#!/usr/bin/env python3
"""Read-only scientific preflight for fixed-geometry periodic Fukui VASP inputs.

Read the first scalar grid only (spin-polarized CHGCAR may have more blocks).
VASP stores rho(r) * cell-volume on that grid: sum(values)/Ngrid = NELECT.
Does not run VASP, create altered CHGCARs, or analyze local orbital binding.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
from pathlib import Path
import sys

NELECT_RE=re.compile(r"\bNELECT\s*=\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][+-]?\d+)?)")
PARAMS=("ENCUT","PREC","ISPIN","ISMEAR","SIGMA","GGA","METAGGA","LHFCALC",
        "LASPH","LDAU","LDAUTYPE","LDAUL","LDAUU","LDAUJ","KSPACING",
        "NGXF","NGYF","NGZF","SYMPREC","ISYM")


def parse_incar(path):
    if not path.is_file():
        raise ValueError("missing INCAR")
    result={}
    for line in path.read_text(errors="replace").splitlines():
        line=line.split("!",1)[0].split("#",1)[0].strip()
        if not line:continue
        for item in line.split(";"):
            if "=" in item:
                k,v=item.split("=",1)
                result[k.strip().upper()]=" ".join(v.split()).upper()
    return result


def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda:fh.read(1048576),b""):
            h.update(chunk)
    return h.hexdigest()


def charge_outcar(path):
    if not path.is_file():
        raise ValueError("OUTCAR missing; need verified VASP electron count")
    values=[]
    converged=False
    for line in path.open(errors="replace"):
        m=NELECT_RE.search(line)
        if m:values.append(float(m.group(1).replace("D","E")))
        if "aborting loop because EDIFF is reached" in line:
            converged=True
    if not values:raise ValueError("OUTCAR missing NELECT")
    if not math.isfinite(values[-1]):raise ValueError("nonfinite NELECT")
    return values[-1],converged


def read_chgcar(path):
    if not path.is_file():raise ValueError(f"missing CHGCAR: {path}")
    with path.open(errors="replace") as fh:
        def next_nonempty():
            for line in fh:
                if line.strip():return line.strip()
            raise ValueError("truncated CHGCAR")
        title=next_nonempty()
        scale=float(next_nonempty().split()[0])
        if not math.isfinite(scale) or scale<=0:
            raise ValueError("only positive VASP POSCAR scale supported; no silent -volume handling")
        lattice=[]
        for _ in range(3):
            row=[float(x) for x in next_nonempty().split()]
            if len(row)!=3 or not all(math.isfinite(x) for x in row):
                raise ValueError("invalid lattice")
            lattice.append([x*scale for x in row])
        symbols=next_nonempty().split()
        if not symbols or not all(re.fullmatch(r"[A-Z][a-z]?",s) for s in symbols):
            raise ValueError("VASP5 chemical symbols required in CHGCAR")
        counts=[int(x) for x in next_nonempty().split()]
        if len(counts)!=len(symbols) or any(x<1 for x in counts):
            raise ValueError("species counts do not match names")
        mode=next_nonempty()
        if mode.lower().startswith("s"):mode=next_nonempty()
        direct=mode.lower().startswith("d")
        cart=mode.lower().startswith(("c","k"))
        if not (direct or cart):raise ValueError("invalid coordinate mode")
        positions=[]
        for _ in range(sum(counts)):
            xyz=[float(x) for x in next_nonempty().split()[:3]]
            if len(xyz)!=3 or not all(math.isfinite(x) for x in xyz):
                raise ValueError("nonfinite or invalid atom coordinate")
            if cart:
                # Convert cartesian to fractional without third-party packages.
                ax,bx,cx=lattice
                det=(ax[0]*(bx[1]*cx[2]-bx[2]*cx[1])-
                     ax[1]*(bx[0]*cx[2]-bx[2]*cx[0])+
                     ax[2]*(bx[0]*cx[1]-bx[1]*cx[0]))
                if abs(det)<1e-12:raise ValueError("degenerate lattice")
                xyz=[x*scale for x in xyz]
                def d3(a,b,c):
                    return a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0])
                frac=[d3(xyz,bx,cx)/det,d3(ax,xyz,cx)/det,d3(ax,bx,xyz)/det]
            else:frac=xyz
            positions.append([x%1 for x in frac])
        grid=[int(x) for x in next_nonempty().split()]
        if len(grid)!=3 or any(x<1 for x in grid):raise ValueError("invalid FFT grid")
        ngrid=math.prod(grid)
        total=0.0
        read=0
        while read<ngrid:
            line=next_nonempty()
            values=[float(x.replace("D","E")) for x in line.split()]
            if read+len(values)>ngrid:raise ValueError("first CHGCAR density block has too many values")
            if not all(math.isfinite(x) for x in values):raise ValueError("nonfinite density")
            total+=math.fsum(values)
            read+=len(values)
        # Do not parse augmentation or optional spin block into charge density.
        return dict(title=title,atoms=sum(counts),species=symbols,counts=counts,
                    positions=positions,lattice=lattice,grid=grid,
                    density_sum_e=total/ngrid)


def allclose(a,b,tol):
    if isinstance(a,(float,int)):
        return abs(a-b)<=tol
    return len(a)==len(b) and all(allclose(x,y,tol) for x,y in zip(a,b))


def periodic_positions_match(a,b,tol):
    return len(a)==len(b) and all(
        all(abs((x-y+0.5)%1-0.5)<=tol for x,y in zip(pos,ref))
        for pos,ref in zip(a,b))


def inspect(root,manifest,epsilon=0.03,geotol=1e-5,deltatol=1e-4):
    if not root.is_dir():raise ValueError("root must be existing directory")
    data=json.loads(manifest.read_text(encoding="utf-8"))
    states=data.get("states")
    if not isinstance(states,list) or len(states)<3:
        raise ValueError("manifest requires N and at least one state on each side")
    seen=set(); results=[]
    for entry in states:
        label=entry["label"]; rel=Path(entry["directory"])
        if not isinstance(label,str) or not label or label in seen:
            raise ValueError("missing or duplicate state label")
        seen.add(label)
        if rel.is_absolute() or any(x==".." for x in rel.parts):
            raise ValueError(f"invalid state relative path {rel}")
        folder=(root/rel).resolve()
        if not folder.is_relative_to(root.resolve()) or not folder.is_dir():
            raise ValueError(f"state escapes root or missing: {rel}")
        claimed=float(entry["delta_electrons"])
        if not math.isfinite(claimed):raise ValueError("nonfinite delta")
        chg=read_chgcar(folder/"CHGCAR")
        nelect,scf=charge_outcar(folder/"OUTCAR")
        inc=parse_incar(folder/"INCAR")
        if not (folder/"POTCAR").is_file() or not (folder/"KPOINTS").is_file():
            raise ValueError("POTCAR/KPOINTS missing: cannot confirm comparable VASP settings")
        if abs(chg["density_sum_e"]-nelect)>epsilon:
            raise ValueError(f"{label}: first CHGCAR block integrates to {chg['density_sum_e']:.7f} e, OUTCAR NELECT {nelect:.7f} e")
        results.append(dict(label=label,directory=str(rel),delta_electrons=claimed,
                            NELECT=nelect,integrated_electrons=chg["density_sum_e"],
                            SCF_EDIFF_marker=scf,potcar_sha256=sha256(folder/"POTCAR"),
                            kpoints_sha256=sha256(folder/"KPOINTS"),incar=inc,geometry=chg))
    neutral=[x for x in results if abs(x["delta_electrons"])<1e-9]
    if len(neutral)!=1:raise ValueError("need exactly one delta_electrons=0 neutral/reference state")
    ref=neutral[0]; plus=minus=0
    for x in results:
        delta=x["NELECT"]-ref["NELECT"]
        if abs(delta-x["delta_electrons"])>deltatol:
            raise ValueError(f"{x['label']}: claimed delta {x['delta_electrons']} vs OUTCAR delta {delta}")
        if delta>deltatol:plus+=1
        if delta< -deltatol:minus+=1
        a,b=x["geometry"],ref["geometry"]
        if a["species"]!=b["species"] or a["counts"]!=b["counts"]:
            raise ValueError(f"{x['label']}: atom species/order mismatch")
        if a["grid"]!=b["grid"]:raise ValueError(f"{x['label']}: FFT grid mismatch")
        if not allclose(a["lattice"],b["lattice"],geotol):
            raise ValueError(f"{x['label']}: lattice mismatch")
        if not periodic_positions_match(a["positions"],b["positions"],geotol):
            raise ValueError(f"{x['label']}: nuclear positions/order mismatch")
        if x["potcar_sha256"]!=ref["potcar_sha256"] or x["kpoints_sha256"]!=ref["kpoints_sha256"]:
            raise ValueError(f"{x['label']}: POTCAR or KPOINTS fingerprint mismatch")
        for key in PARAMS:
            if x["incar"].get(key)!=ref["incar"].get(key):
                raise ValueError(f"{x['label']}: INCAR {key} differs across electronic states")
    if not plus or not minus:raise ValueError("two-sided f+ / f- requires states both above and below N")
    issues=[]
    if not all(x["SCF_EDIFF_marker"] for x in results):
        issues.append("EDIFF termination marker absent in at least one OUTCAR; independently verify SCF before using results")
    for x in results:
        if x["incar"].get("NSW","0") not in {"0","0.0"}:
            issues.append(f"{x['label']}: NSW nonzero; verify ions did NOT move")
    return dict(status="INPUT_GRID_PASS_SCF_MANUAL_CHECK",reference=ref["label"],
                n_atoms=ref["geometry"]["atoms"],grid=ref["geometry"]["grid"],
                plus_states=plus,minus_states=minus,states=[
                    {k:v for k,v in x.items() if k not in {"geometry","incar"}}
                    for x in results], warnings=issues,
                limitations=["CHGCAR first valence scalar block checked; not PAW one-center augmentation.",
                             "Fixed geometry alone does not validate periodic charged-cell physical response.",
                             "Bader/Chargemol charged-state populations and SCF occupancy need separate QC."])


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--electron-tol",type=float,default=0.03)
    p.add_argument("--write",type=Path,help="Output JSON; absent => read-only; will not overwrite")
    args=p.parse_args(argv)
    if args.electron_tol<=0 or not math.isfinite(args.electron_tol):
        p.error("invalid electron tolerance")
    try:
        result=inspect(args.root.expanduser().resolve(),args.manifest.expanduser().resolve(),
                       epsilon=args.electron_tol)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        if args.write:
            dst=args.write.expanduser().resolve()
            if dst.exists():raise ValueError("output exists; refusing to overwrite")
            if not dst.parent.is_dir():raise ValueError("output parent does not exist")
            dst.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    except (ValueError,OSError,KeyError,TypeError,json.JSONDecodeError) as exc:
        print(f"PRECHECK FAILED: {exc}",file=sys.stderr)
        return 1
    return 0


if __name__=="__main__":
    sys.exit(main())
