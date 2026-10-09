#!/usr/bin/env python3
"""Assemble a Chinese, human-readable periodic Fukui comparison from QC artifacts.

No numerical electronic-structure work. Do NOT label method availability from
a planned input file; only successfully QC'd files count as computed.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
from pathlib import Path
import sys

ENGINES=("multiwfn","critic2","fukuigrid-fd","fukuigrid-interp")
FIELDS=("fplus","fminus","fzero","dual")

def clean(v):
    return str(v if v is not None else "").replace("|",r"\|").replace("\r"," ").replace("\n"," ").strip()

def summarize(preflight,grid,condensed_files):
    if preflight.get("status")!="INPUT_GRID_PASS_SCF_MANUAL_CHECK":
        raise ValueError("VASP density preflight not passed")
    cases=preflight["states"]
    lines=["# 周期性概念 DFT / Fukui 函数三软件对照汇报","",
        "**研究目的：** 使用同一固定晶胞、同一原子核位置与电子结构设置，"
        "对照 Multiwfn、Critic2 和 FukuiGrid 的 Fukui 函数计算结果；"
        "将有限差分与分数电子数插值分开解释。",
        "",
        f"**参考态：** {clean(preflight['reference'])}；原子数 {preflight['n_atoms']}；"
        f"FFT 网格 {clean('×'.join(map(str,preflight['grid'])))}。",
        "",
        "| 状态 | 电子数扰动 ΔN / e | OUTCAR NELECT / e | CHGCAR 网格积分 / e | SCF 终止标志 |",
        "|---|---:|---:|---:|---|"]
    for s in cases:
        lines.append(f"| {clean(s['label'])} | {s['delta_electrons']:+.4f} | "
                     f"{s['NELECT']:.5f} | {s['integrated_electrons']:.5f} | "
                     f"{'有' if s['SCF_EDIFF_marker'] else '缺失，需核实'} |")
    lines+=["","**方法独立性说明：** 三个程序对同一份密度做相同的有限差分，"
            "理论上应接近；FukuiGrid 插值使用不同的电子数扰动与回归估计量，"
            "不属于完全相同的数值方法。Fukui 势的 electrodes 和 SCPC 是"
            "单独的边界条件修正方案，不代表额外的 Fukui 函数定义。","",
            "## 三维 Fukui 函数","",
            "| 方法 | f+ | f− | f0 | Δf |",
            "|---|---|---|---|---|"]
    fields=(grid or {}).get("fields",{})
    for engine in ENGINES:
        cells=[]
        for field in FIELDS:
            key=f"{engine}:{field}"
            if key in fields:
                r=fields[key]
                cells.append(f"已通过网格检查，∫={r['integral']:+.5f}")
            else:cells.append("未提供已验收结果")
        lines.append(f"| {engine} | "+" | ".join(cells)+" |")
    lines+=["","**正、负积分：** 空间上允许出现正负 Fukui 密度瓣；"
            "电子重排可以让某些局域 f 为负。积分值不是对点值做裁剪后的概率。",
            "",
            "## 同一种有限差分近似下的软件对照","",
            "| 比较 | 指标 | RMSE (e/bohr³) | 最大绝对差 (e/bohr³) | 检查状态 |",
            "|---|---|---:|---:|---|"]
    comparison=(grid or {}).get("engine_comparisons",[])
    for r in comparison:
        lines.append(f"| {clean(r['other'])} vs {clean(r['reference'])} | "
                     f"{clean(r['field'])} | {r['rmse']:.6g} | "
                     f"{r['max_abs']:.6g} | {clean(r['status'])} |")
    if not comparison:lines.append("| 无可验证成对结果 | — | — | — | 未运行/未提供 |")
    lines+=["","## 凝聚 Fukui 指数（按原子电荷定义严格区分）",""]
    if condensed_files:
        for file in condensed_files:
            provenance=file.with_suffix(".md")
            if not provenance.is_file() or "**质量检查：** PASS" not in provenance.read_text(encoding="utf-8"):
                raise ValueError(f"{file}: missing validated condensed report QC marker")
            with file.open(encoding="utf-8-sig",newline="") as fh:
                entries=list(csv.DictReader(fh))
            if not entries:continue
            required={"atom_index","element","f_plus","f_minus","f_zero","dual"}
            if not required.issubset(entries[0]):
                raise ValueError(f"{file.name}: condensed CSV missing columns")
            lines.append(f"**来源：** \`{clean(file)}\`（{len(entries)} 个原子）")
            lines+=["",
                "| 原子序号 | 元素 | f_A+ | f_A− | f_A0 | Δf_A |",
                "|---:|---|---:|---:|---:|---:|"]
            for r in entries:
                vals=[float(r[k]) for k in ("f_plus","f_minus","f_zero","dual")]
                if not all(math.isfinite(v) for v in vals):
                    raise ValueError(f"{file}: nonfinite condensed value")
                lines.append(f"| {clean(r['atom_index'])} | {clean(r['element'])} | "
                             +" | ".join(f"{v:+.6f}" for v in vals)+" |")
            lines.append("")
    else:
        lines.append("**未提供已验收的三个电子态原子布居表，凝聚 Fukui 暂不可得。**\n")
    lines+=["## 能量指标、Fukui 势及物理判断的限制","",
            "电负性、全局化学硬度、电子亲和能、局部软度和亲电性指数等若依赖"
            "带电周期晶胞的未经修正 TOTEN，当前标记为 **NOT_VALIDATED_FOR_CHARGED_PBC**，"
            "不生成虚假的定量结果。",
            "",
            "Fukui 势及电极/SCPC 修正只适合输入与表面物理模型相符的情况，"
            "当前报告没有从密度文件自动推断这两类势修正已经完成。",
            "",
            "凝聚 Fukui 的结果依赖 Bader、DDEC6、Hirshfeld/CM5 的划分；"
            "不同电荷模型不应混在一张表解释为同一物理量。"
            "Fukui 函数不能单独预测实际电解质–金属界面分解势垒。",
            ""]
    if grid and grid.get("status")=="PASS_GRID_ARITHMETIC_ONLY_NOT_PBC_PHYSICS" and comparison:
        lines+=["## 可用于组会的初步结论","",
                "在给定的统一电子数扰动与网格规范下，现有三维 Fukui 输出"
                "已经通过电子数归一化及所提供的跨程序空间算术检查。"
                "该结果支持软件后处理的数值一致性，**尚不能证明反应位点或分解机理**。"
                "仍需核查不同电子数状态的 SCF、载流子局域性、补偿背景、"
                "超胞大小与电子数扰动收敛。",""]
    else:
        lines+=["## 可用于组会的初步结论","",
                "尚未取得完整、已验收的三维 Fukui 网格对照；"
                "当前不应据此宣称哪一个原子或反应通道优先。",""]
    if preflight.get("warnings"):
        lines+=["## 源数据预检警告",""]
        lines.extend("- "+clean(x) for x in preflight["warnings"])
    if grid and grid.get("warnings"):
        lines+=["","## 网格对照警告",""]
        lines.extend("- "+clean(x) for x in grid["warnings"])
    return "\n".join(lines)+"\n"

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--preflight",type=Path,required=True)
    p.add_argument("--grid-audit",type=Path,help="Validated grid_audit JSON (optional)")
    p.add_argument("--condensed",action="append",type=Path,default=[],
                   help="Any validated condensed_*.csv (repeat)")
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args(argv)
    try:
        pre=json.loads(a.preflight.read_text(encoding="utf-8"))
        grid=json.loads(a.grid_audit.read_text(encoding="utf-8")) if a.grid_audit else None
        if grid and grid.get("status")!="PASS_GRID_ARITHMETIC_ONLY_NOT_PBC_PHYSICS":
            raise ValueError("grid_audit not passed")
        if a.out.exists() or not a.out.parent.is_dir():
            raise ValueError("report path exists or parent missing; refusing overwrite")
        report=summarize(pre,grid,a.condensed)
        a.out.write_text(report,encoding="utf-8")
        print(f"中文报告：{a.out}")
        return 0
    except (ValueError,OSError,KeyError,TypeError,json.JSONDecodeError) as exc:
        print(f"PERIODIC CDFT REPORT FAILED: {exc}",file=sys.stderr)
        return 1

if __name__=="__main__":
    sys.exit(main())
