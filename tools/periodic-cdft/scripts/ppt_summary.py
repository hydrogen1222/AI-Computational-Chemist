#!/usr/bin/env python3
"""Produce ONE concise Chinese, PPT-ready summary from existing QC evidence.

No electronic-structure work, guessed numbers or proprietary data required.
The long report.py remains the detailed audit record.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import sys

from report import summarize as validate_full_report

LABELS = {
    "condensed_bader": "Bader",
    "condensed_ddec6": "DDEC6",
    "condensed_chargemol_h": "Hirshfeld",
    "condensed_multiwfn_h": "Hirshfeld (Multiwfn)",
}
ENGINES = ("multiwfn", "critic2", "fukuigrid-fd")
FIELDS = ("fplus", "fminus", "fzero", "dual")


def evidence_summary(pre, grid, condensed_paths, system, warnings=()):
    # Reuse the full reporter's PASS and evidence checks first.
    validate_full_report(pre, grid, condensed_paths)

    states = pre["states"]
    neutral = next((s for s in states if abs(s["delta_electrons"]) < 1e-10), None)
    if neutral is None:
        raise ValueError("neutral/reference state missing")
    sampled = ", ".join(f"{s['delta_electrons']:+g}" for s in states)
    lines = [
        f"# {system}｜周期性 Fukui 分析（PPT 摘要）",
        "",
        f"**数据：** 同结构电子态 ΔN = {sampled} e；{pre['n_atoms']} 个原子。",
        "**计算量：** 空间 f⁺、f⁻、f⁰=(f⁺+f⁻)/2、双描述符 Δf=f⁺−f⁻；"
        "以及各电荷分区下的原子凝聚 f_A⁺、f_A⁻、f_A⁰、Δf_A。",
        "",
    ]
    valid = []
    comparisons = []
    if grid is not None and grid.get("status") == "PASS_GRID_ARITHMETIC_ONLY_NOT_PBC_PHYSICS":
        fields = grid.get("fields", {})
        valid = [engine for engine in ENGINES
                 if all(f"{engine}:{field}" in fields for field in FIELDS)]
        comparisons = [r for r in grid.get("engine_comparisons", [])
                       if r.get("status") == "PASS"
                       and r.get("reference") in valid and r.get("other") in valid
                       and r.get("field") in ("fplus", "fminus")]
    if valid:
        lines.append("**空间 Fukui：** 已验收软件：" + "、".join(valid) + "；"
                     "各软件的 f⁺、f⁻、f⁰ 积分约为 1，Δf 积分约为 0。")
        if len(valid) > 1 and comparisons:
            maximum = max(float(r["max_abs"]) for r in comparisons)
            if not math.isfinite(maximum):
                raise ValueError("nonfinite grid comparison")
            lines.append(f"**跨软件最大逐点差：** {maximum:.3g} e/bohr³"
                         "（相同有限差分、网格和单位；仅证明数值一致）。")
        elif len(valid) > 1:
            lines.append("**跨软件一致性：** 缺少已验收的成对逐点比较，不能声称一致。")
    else:
        lines.append("**空间 Fukui：** 未提供四场均通过验收的数值证据，不声明软件一致。")

    collected = {}
    for path in condensed_paths:
        stem = path.stem
        if stem not in LABELS:
            continue
        with path.open(encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        if not rows:
            raise ValueError(f"empty atomic table: {path}")
        grouped = {}
        for row in rows:
            for key in ("f_plus", "f_minus", "f_zero", "dual"):
                if not math.isfinite(float(row[key])):
                    raise ValueError("nonfinite atomic descriptor")
            grouped.setdefault(row["element"], []).append(row)
        collected[stem] = grouped

    # Limit a one-page table to distinct charge partitions; CM5/H duplicate
    # data belong in the full audit, not repeated here.
    selected = [key for key in ("condensed_chargemol_h",
                               "condensed_multiwfn_h",
                               "condensed_ddec6", "condensed_bader")
                if key in collected]
    if "condensed_chargemol_h" in selected and "condensed_multiwfn_h" in selected:
        selected.remove("condensed_multiwfn_h")
    lines += ["", "**原子凝聚 Fukui（按元素平均，分区方法不能混用）：**", ""]
    if selected:
        lines += ["| 电荷分区 | 元素 | f_A⁺ | f_A⁻ | f_A⁰ | Δf_A |",
                  "|---|---|---:|---:|---:|---:|"]
        for key in selected:
            for element, atoms in collected[key].items():
                means = [math.fsum(float(atom[k]) for atom in atoms) / len(atoms)
                         for k in ("f_plus", "f_minus", "f_zero", "dual")]
                lines.append(f"| {LABELS[key]} | {element} | "
                             + " | ".join(f"{v:+.3f}" for v in means) + " |")
        lines += ["",
                  "**凝聚指数结论：** 数值随原子电荷划分方法变化；"
                  "不能据此判定哪种分区更准确。"]
        if "condensed_bader" in selected:
            lines.append("**Bader 注意：** 电荷守恒不等于对称位点通过检查，"
                         "需另外核对等价原子。")
    else:
        lines.append("没有已验收的可列示原子凝聚结果。")

    for item in warnings:
        lines.append(f"**特别说明：** {str(item).replace(chr(10), ' ')}")
    lines += ["", "**尚未证明：** 反应势垒、实际反应位点，以及未经修正的周期性"
              "I/A、绝对电负性、硬度和局部软度。"]
    return "\n".join(lines) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--preflight", required=True, type=Path)
    p.add_argument("--grid-audit", type=Path)
    p.add_argument("--condensed", action="append", default=[], type=Path)
    p.add_argument("--system", default="周期性体系")
    p.add_argument("--warning", action="append", default=[])
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args(argv)
    try:
        if a.out.exists() or not a.out.parent.is_dir():
            raise ValueError("output exists or parent missing; no overwrites")
        pre = json.loads(a.preflight.read_text(encoding="utf-8"))
        grid = json.loads(a.grid_audit.read_text(encoding="utf-8")) if a.grid_audit else None
        report = evidence_summary(pre, grid, a.condensed, a.system, a.warning)
        a.out.write_text(report, encoding="utf-8")
        print(f"PPT 一页摘要：{a.out}")
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"PPT SUMMARY FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
