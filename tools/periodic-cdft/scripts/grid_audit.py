#!/usr/bin/env python3
"""Audit already-produced Gaussian .cube Fukui fields from local external codes.

Independent QA only: requires SAME grid/units, checks integral, identities
and pointwise cross-engine agreement. Does not calculate electronic density,
convert VASP files, run external software, or silently renormalize fields.
All cube axes must be positive-count BOHR grids (fail-closed otherwise).
"""
from __future__ import annotations
import argparse
from array import array
import json
import math
from pathlib import Path
import sys

FIELDS={"fplus","fminus","fzero","dual"}
ENGINES={"multiwfn","critic2","fukuigrid-fd","fukuigrid-interp"}
FD={"multiwfn","critic2","fukuigrid-fd"}


def vec(line,n):
    parts=line.split()
    if len(parts)<n:raise ValueError("truncated cube header")
    result=[float(x.replace("D","E")) for x in parts[:n]]
    if not all(math.isfinite(x) for x in result):
        raise ValueError("nonfinite cube header")
    return result


def determinant(a,b,c):
    return (a[0]*(b[1]*c[2]-b[2]*c[1])
            -a[1]*(b[0]*c[2]-b[2]*c[0])
            +a[2]*(b[0]*c[1]-b[1]*c[0]))


def load_cube(path):
    if not path.is_file():raise ValueError(f"cube not found: {path}")
    with path.open(errors="replace") as fh:
        fh.readline();fh.readline()
        head=vec(fh.readline(),4)
        natoms=int(head[0])
        if natoms<0 or natoms>100000 or natoms!=head[0]:
            raise ValueError("unsupported multi-field/orbital cube or invalid atom count")
        origin=head[1:4]; grids=[];axes=[]
        for _ in range(3):
            row=vec(fh.readline(),4)
            n=int(row[0])
            if n<1 or n!=row[0]:
                raise ValueError("need positive cube grid counts (bohr), no mixed Å/bohr")
            grids.append(n);axes.append(row[1:4])
        atoms=[]
        for _ in range(natoms):
            atom=vec(fh.readline(),5)
            atoms.append(atom[:5])
        ngrid=math.prod(grids)
        vol=abs(determinant(*axes))
        if vol<=1e-15:raise ValueError("degenerate cube voxel geometry")
        values=array("d")
        for line in fh:
            if not line.strip():continue
            for tok in line.split():
                try:n=float(tok.replace("D","E"))
                except ValueError as exc:raise ValueError("non-grid text after cube samples") from exc
                if not math.isfinite(n):raise ValueError("nonfinite grid sample")
                if len(values)>=ngrid:raise ValueError("more grid points than declared")
                values.append(n)
        if len(values)!=ngrid:
            raise ValueError(f"cube missing data: {len(values)} vs {ngrid} grid points")
    return dict(path=str(path),axes=axes,origin=origin,grid=grids,atoms=atoms,voxel=vol,values=values)


def same_grid(a,b,tol=1e-7):
    if a["grid"]!=b["grid"] or len(a["atoms"])!=len(b["atoms"]):return False
    def near(x,y):return abs(x-y)<=tol
    for key in ("axes","origin","atoms"):
        x,y=a[key],b[key]
        if key=="origin":
            if any(not near(u,v) for u,v in zip(x,y)):return False
        elif any(any(not near(u,v) for u,v in zip(r,s)) for r,s in zip(x,y)):
            return False
    return True


def integrated(field):
    arr=field["values"];v=field["voxel"]
    positive=math.fsum(x for x in arr if x>0)*v
    negative=math.fsum(x for x in arr if x<0)*v
    return dict(integral=positive+negative,positive_integral=positive,
                negative_integral=negative,min=min(arr),max=max(arr),
                grid=field["grid"],units="e/bohr^3 per electron")


def compare(a,b,mode="difference"):
    if not same_grid(a,b):raise ValueError("cube grids/origin/atoms mismatch")
    n=len(a["values"])
    squared=0.;maxabs=0.;absolute=0.
    for x,y in zip(a["values"],b["values"]):
        d=x-y;squared+=d*d;maxabs=max(maxabs,abs(d));absolute+=abs(d)
    return dict(rmse=math.sqrt(squared/n),max_abs=maxabs,
                mae=absolute/n,l1_integral=absolute*a["voxel"])


def combine_check(fp,fm,observed,kind):
    if not same_grid(fp,fm) or not same_grid(fp,observed):
        raise ValueError("f± and derived f0/dual grids disagree")
    maxerr=0.
    for p,m,actual in zip(fp["values"],fm["values"],observed["values"]):
        exp=(p+m)/2 if kind=="fzero" else p-m
        maxerr=max(maxerr,abs(exp-actual))
    return maxerr


def audit(selections,integral_tol=0.05,identity_tol=1e-5,agreement_abs=1e-4,agreement_rel=.02):
    fields={};report={"fields":{},"identity_checks":{},"engine_comparisons":[],"warnings":[]}
    base=None
    for spec in selections:
        p=spec.split(":",2)
        if len(p)!=3:raise ValueError(f"use engine:field:/path/to/file.cube, not '{spec}'")
        engine,field,path=p
        if engine not in ENGINES or field not in FIELDS or (engine,field) in fields:
            raise ValueError(f"invalid or duplicate engine/field: {engine}/{field}")
        item=load_cube(Path(path))
        if base is not None and not same_grid(base,item):
            raise ValueError(f"reference vs {engine}:{field}: cube origins, axes, grids or atoms differ")
        base=base or item
        fields[engine,field]=item
        stats=integrated(item)
        report["fields"][f"{engine}:{field}"]=dict(path=path,**stats)
        expected=0 if field=="dual" else 1
        if abs(stats["integral"]-expected)>integral_tol:
            raise ValueError(f"{engine}:{field} integral {stats['integral']:.7f}, expected {expected}")
    engines={e for e,_ in fields}
    if not engines:raise ValueError("need at least one engine")
    for engine in sorted(engines):
        if (engine,"fplus") not in fields or (engine,"fminus") not in fields:
            raise ValueError(f"{engine}: both fplus and fminus are required")
        for kind in ("fzero","dual"):
            if (engine,kind) not in fields:
                report["warnings"].append(f"{engine}: {kind} not supplied, cannot check identity")
                continue
            err=combine_check(fields[engine,"fplus"],fields[engine,"fminus"],
                              fields[engine,kind],kind)
            report["identity_checks"][f"{engine}:{kind}"]=err
            if err>identity_tol:
                raise ValueError(f"{engine}:{kind} identity inconsistent by {err:g}")
    reference="critic2" if "critic2" in engines else next(iter(sorted(engines&FD)),None)
    for engine in sorted(engines&FD):
        if engine==reference:continue
        for kind in ("fplus","fminus"):
            metrics=compare(fields[reference,kind],fields[engine,kind])
            scale=max(max(abs(x) for x in fields[reference,kind]["values"]),1e-12)
            allowed=agreement_abs+agreement_rel*scale
            metrics.update(reference=reference,other=engine,field=kind,allowed_max=allowed,
                           status="PASS" if metrics["max_abs"]<=allowed else "DISAGREE")
            report["engine_comparisons"].append(metrics)
            if metrics["status"]=="DISAGREE":
                raise ValueError(f"{engine} vs {reference} {kind}: max diff {metrics['max_abs']:.4g} > {allowed:.4g}; check grid/sign/units/writer")
    if "fukuigrid-interp" in engines:
        report["warnings"].append(
            "FukuiGrid interpolation uses a different electron-number estimator; differences vs finite differences are not automatically software bugs")
    report["status"]="PASS_GRID_ARITHMETIC_ONLY_NOT_PBC_PHYSICS"
    return report


def markdown(result):
    lines=["# 周期性 Fukui 三软件网格 QC｜中文报告","",
           "**状态：** "+result["status"]+"。"
           "仅证明所提供网格的归一化、配对与算术一致性；"
           "不能自动证明带电周期性模型、表面反应性和物理收敛可靠。","",
           "| 软件:指标 | 积分 | 正值积分 | 负值积分 | min | max |",
           "|---|---:|---:|---:|---:|---:|"]
    for key,r in result["fields"].items():
        lines.append(f"| {key} | {r['integral']:+.6f} | {r['positive_integral']:+.6f} | "
                     f"{r['negative_integral']:+.6f} | {r['min']:+.6g} | {r['max']:+.6g} |")
    lines+=["","**同一有限差分、不同软件的逐网格对照（仅同一晶胞和相同电子扰动）：**","",
            "| 比较 | 指标 | RMSE (e/bohr³) | 最大绝对偏差 | 结果 |",
            "|---|---|---:|---:|---|"]
    for r in result["engine_comparisons"]:
        lines.append(f"| {r['other']} − {r['reference']} | {r['field']} | "
                     f"{r['rmse']:.6g} | {r['max_abs']:.6g} | {r['status']} |")
    lines+=["","**提醒：** 插值与有限差分不是同一种电子数近似；"
            "在相同状态、相同归一化下，三套软件仅做网格加减应接近，"
            "显著偏差首先排查实现与输入，不当成三个相互独立的化学预测。",
            "缺失 f0/dual 时必须标注尚未计算，不可用描述性文字补齐。",""]
    for warning in result["warnings"]:lines.append("- "+warning)
    return "\n".join(lines)+"\n"


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cube",action="append",required=True,
                   help="Repeated engine:fplus|fminus|fzero|dual:/abs/file.cube")
    p.add_argument("--out",type=Path,required=True,help="New JSON output; matching Markdown created")
    p.add_argument("--integral-tol",type=float,default=.05)
    p.add_argument("--identity-tol",type=float,default=1e-5)
    p.add_argument("--agreement-abs",type=float,default=1e-4)
    p.add_argument("--agreement-rel",type=float,default=.02)
    args=p.parse_args(argv)
    try:
        if any(not math.isfinite(x) or x<0 for x in
               [args.integral_tol,args.identity_tol,args.agreement_abs,args.agreement_rel]):
            raise ValueError("invalid tolerance")
        dst=args.out.expanduser().resolve()
        if dst.exists() or dst.with_suffix(".md").exists() or not dst.parent.is_dir():
            raise ValueError("output path exists or parent missing; no overwrite permitted")
        report=audit(args.cube,args.integral_tol,args.identity_tol,
                     args.agreement_abs,args.agreement_rel)
        dst.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        dst.with_suffix(".md").write_text(markdown(report),encoding="utf-8")
        print(f"QC: {dst}\n中文报告: {dst.with_suffix('.md')}")
        return 0
    except (ValueError,OSError,KeyError) as exc:
        print(f"GRID QC FAILED: {exc}",file=sys.stderr)
        return 1


if __name__=="__main__":
    sys.exit(main())
