#!/usr/bin/env python3
"""Condensed periodic Fukui finite differences from EXISTING atomic charge CSV.

No external programs, no atoms guessed, no reuse of unconverged H-I.
Per-method source CSVs MUST be generated for N, N+delta, N-delta on the
same VASP structure; a documented preflight is prerequisite.
"""
from __future__ import annotations
import argparse
import csv
import math
from pathlib import Path
import sys

COLUMNS={
    "bader":("atom_index","net_charge_e"),
    "ddec6":("atom_index_1based","ddec6_net_charge_e"),
    "chargemol-h":("atom_index_1based","hirshfeld_net_charge_e"),
    "chargemol-cm5":("atom_index_1based","cm5_net_charge_e"),
    "multiwfn-h":("atom_1based","multiwfn_hirshfeld_e"),
    "multiwfn-cm5":("atom_1based","multiwfn_cm5_e"),
}


def read_atoms(file,method,case):
    idx_col,q_col=COLUMNS[method]
    if not file.is_file():raise ValueError(f"missing source {file}")
    records={}
    with file.open(encoding="utf-8-sig",newline="") as fh:
        reader=csv.DictReader(fh)
        if not {idx_col,q_col,"element","case"}.issubset(reader.fieldnames or []):
            raise ValueError(f"{file}: required columns absent: {idx_col}/{q_col}/element/case")
        for row in reader:
            if row["case"]!=case:continue
            try:
                idx=int(row[idx_col]); q=float(row[q_col])
            except (ValueError,TypeError) as ex:
                raise ValueError(f"{file}: invalid charge for atom {row.get(idx_col)}; cannot infer missing values") from ex
            if idx<1 or idx in records or not math.isfinite(q):
                raise ValueError(f"{file}: duplicate/invalid charge or atom index")
            records[idx]=(row["element"],q)
    if not records:raise ValueError(f"{file}: case '{case}' not found")
    if sorted(records)!=list(range(1,len(records)+1)):
        raise ValueError(f"{file}: missing/non-contiguous atom indices")
    return records


def compute(neutral,plus,minus,dplus,dminus,tol):
    if dplus<=0 or dminus<=0 or not all(math.isfinite(v) for v in [dplus,dminus,tol]):
        raise ValueError("delta-plus/minus must be finite positive numbers")
    if neutral.keys()!=plus.keys() or neutral.keys()!=minus.keys():
        raise ValueError("atomic index sets differ; cannot compare")
    result=[]
    for idx in neutral:
        elem,q0=neutral[idx]
        ep,qp=plus[idx]
        em,qm=minus[idx]
        if elem!=ep or elem!=em:
            raise ValueError(f"atom {idx}: element/order mismatch")
        fp=(q0-qp)/dplus
        fm=(qm-q0)/dminus
        result.append(dict(atom_index=idx,element=elem,
                           f_plus=fp,f_minus=fm,
                           f_zero=(fp+fm)/2,dual=fp-fm))
    sums={k:math.fsum(r[k] for r in result) for k in
          ("f_plus","f_minus","f_zero","dual")}
    status="PASS" if (abs(sums["f_plus"]-1)<=tol and
                      abs(sums["f_minus"]-1)<=tol and
                      abs(sums["f_zero"]-1)<=tol and
                      abs(sums["dual"])<=2*tol) else "FAIL_CHARGE_RESPONSE_SUM"
    return result,sums,status


def write_csv(path,rows):
    with path.open("w",encoding="utf-8",newline="") as fh:
        writer=csv.DictWriter(fh,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--method",required=True,choices=list(COLUMNS))
    for state in ("neutral","plus","minus"):
        p.add_argument("--"+state,type=Path,required=True)
        p.add_argument("--case-"+state,default=".")
    p.add_argument("--delta-plus",type=float,required=True,help="Actual NELECT(N+)−NELECT(N)")
    p.add_argument("--delta-minus",type=float,required=True,help="Actual NELECT(N)−NELECT(N−)")
    p.add_argument("--preflight",type=Path,required=True,
                   help="A vetted JSON from preflight.py, with same delta+- and atom count")
    p.add_argument("--charge-tol",type=float,default=0.05)
    p.add_argument("--output",type=Path,required=True,help="Output CSV path; no overwrite")
    args=p.parse_args(argv)
    try:
        if args.charge_tol<=0 or not math.isfinite(args.charge_tol):
            raise ValueError("invalid charge tolerance")
        import json
        meta=json.loads(args.preflight.read_text(encoding="utf-8"))
        if meta.get("status")!="INPUT_GRID_PASS_SCF_MANUAL_CHECK":
            raise ValueError("VASP input grid preflight has not passed")
        states={r["label"]:r for r in meta["states"]}
        # State labels in the metadata are independent of the CSV case labels.
        deltas=[r["delta_electrons"] for r in meta["states"]]
        if not any(abs(x-args.delta_plus)<1e-4 for x in deltas):
            raise ValueError("requested electron-addition delta absent in preflight")
        if not any(abs(x+args.delta_minus)<1e-4 for x in deltas):
            raise ValueError("requested electron-removal delta absent in preflight")
        datasets=[read_atoms(getattr(args,state),args.method,
                             getattr(args,"case_"+state))
                  for state in ("neutral","plus","minus")]
        if len(datasets[0])!=meta["n_atoms"]:
            raise ValueError("charge-table atom count differs from VASP density")
        rows,sums,status=compute(*datasets,args.delta_plus,args.delta_minus,args.charge_tol)
        print("Atomic condensed sums:",sums,"status:",status)
        if status!="PASS":
            raise ValueError("condensed Fukui charge-response sums failed; no valid report exported")
        out=args.output.expanduser().resolve()
        if out.exists() or out.with_suffix(".md").exists():
            raise ValueError("refusing to overwrite existing report or CSV")
        if not out.parent.is_dir():raise ValueError("output directory does not exist")
        write_csv(out,rows)
        grouped={}
        for row in rows:grouped.setdefault(row["element"],[]).append(row)
        lines=[
            "# 周期性凝聚 Fukui 指数｜中文汇报",
            "",
            f"**方法：** {args.method}；三个固定结构电子态，每原子同一分区约定。",
            f"**电子数变化：** +{args.delta_plus:g} e / −{args.delta_minus:g} e。",
            "**符号约定：** f_A+ = (q_N−q_{N+δ})/δ；"
            "f_A− = (q_{N−δ}−q_N)/δ；f_A0=(f_A+ + f_A−)/2；Δf_A=f_A+−f_A−。",
            "**注意：** 局部或凝聚 Fukui 指数允许为负，不能强行截断；"
            "它反映电荷分区下的布居响应，不是实测电荷转移量或势垒。",
            "",
            f"**质量检查：** {status}；Σf+={sums['f_plus']:+.5f}，"
            f"Σf−={sums['f_minus']:+.5f}，Σf0={sums['f_zero']:+.5f}，"
            f"ΣΔf={sums['dual']:+.5f}。",
            "",
            "**元素平均值（不替代逐原子位点）：**",
            "",
            "| 元素 | 原子数 | 平均 f+ | 平均 f− | 平均 f0 | 平均 Δf |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for el,rs in grouped.items():
            mean=lambda key:sum(r[key] for r in rs)/len(rs)
            lines.append(f"| {el} | {len(rs)} | {mean('f_plus'):+.5f} | "
                         f"{mean('f_minus'):+.5f} | {mean('f_zero'):+.5f} | "
                         f"{mean('dual'):+.5f} |")
        lines+=["","**逐原子 Fukui 指数（全部）：**","",
                "| 编号 | 元素 | f+ | f− | f0 | Δf |",
                "|---:|---|---:|---:|---:|---:|"]
        lines.extend(f"| {r['atom_index']} | {r['element']} | {r['f_plus']:+.6f} | "
                     f"{r['f_minus']:+.6f} | {r['f_zero']:+.6f} | {r['dual']:+.6f} |"
                     for r in rows)
        lines+=["","**来源：** "+", ".join(str(getattr(args,s)) for s in ("neutral","plus","minus")),
                "",
                "比较不同电荷模型时必须分别报告方法。不同电子数状态下原子盆地或参考原子密度也可能改变。"
                "凝聚 f_A 不一定等于体 Fukui 在任意固定原子区间上的积分。",
                "该前处理只检查静态结构/电荷守恒；加入电子的态局域性、SCF、PBC 背景及尺寸依赖需另行验证。",
                ""]
        out.with_suffix(".md").write_text("\n".join(lines),encoding="utf-8")
        print(f"CSV: {out}\n中文报告: {out.with_suffix('.md')}")
        return 0
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print(f"CONDENSED FUKUI FAILED: {exc}",file=sys.stderr)
        return 1


if __name__=="__main__":
    sys.exit(main())
