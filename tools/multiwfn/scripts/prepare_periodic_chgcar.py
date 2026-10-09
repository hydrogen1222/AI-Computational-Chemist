#!/usr/bin/env python3
"""Prepare Multiwfn periodic CHGCAR inputs using exact VASP POTCAR ZVAL.

Read-only by default. --prepare copies density into an isolated working
directory, replacing ONLY the first title line with 'Nval ...'. No external
programs are run; source CHGCAR and licensed POTCAR are never modified.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import re
import shutil
import sys

FLOAT = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][+-]?\d+)?"
ZVAL = re.compile(r"\bZVAL\s*=\s*(" + FLOAT + r")", re.I)
TITLE = re.compile(r"^\s*TITEL\s*=\s*(.*)", re.I)
NELECT = re.compile(r"\bNELECT\s*=\s*("+FLOAT+r")")


def valence_metadata(case: Path):
    density, paw = case/"CHGCAR", case/"POTCAR"
    if not density.is_file() or not paw.is_file():
        raise ValueError("both CHGCAR and POTCAR required for VASP valence charges")
    with density.open("rb") as f:
        header=[f.readline().decode("utf-8",errors="replace").strip() for _ in range(8)]
    species=header[5].split()
    try:
        counts=[int(v) for v in header[6].split()]
    except ValueError as exc:
        raise ValueError("invalid VASP5 CHGCAR atom counts") from exc
    if not species or len(species)!=len(counts) or min(counts)<=0:
        raise ValueError("ambiguous CHGCAR species/counts")
    entries=[]
    current=None
    for line in paw.open(encoding="utf-8",errors="replace"):
        m=TITLE.match(line)
        if m:
            if current is not None: entries.append(current)
            tokens=m.group(1).split()
            name=next((x for x in tokens if re.fullmatch(r"[A-Z][a-z]?(?:_[a-zA-Z0-9]+)?",x)),None)
            if name is None:
                raise ValueError("unrecognized POTCAR TITEL")
            current=[name,None]
        m=ZVAL.search(line)
        if m and current is not None and current[1] is None:
            current[1]=float(m.group(1).replace("D","E").replace("d","e"))
    if current is not None:entries.append(current)
    if len(entries)!=len(species):
        raise ValueError(f"POTCAR {len(entries)} datasets vs {len(species)} CHGCAR species")
    vals=[]
    for el,(name,zval) in zip(species,entries):
        if not re.fullmatch(re.escape(el)+r"(?:_[a-zA-Z0-9]+)?",name):
            raise ValueError(f"CHGCAR/POTCAR species mismatch: {el} vs {name}")
        if zval is None or not 0<zval<120:
            raise ValueError(f"missing/out-of-range ZVAL for {name}")
        vals.append(zval)
    electrons=sum(n*z for n,z in zip(counts,vals))
    nelect=None
    outcar=case/"OUTCAR"
    if outcar.is_file():
        for line in outcar.open(encoding="utf-8",errors="replace"):
            m=NELECT.search(line)
            if m:nelect=float(m.group(1).replace("D","E").replace("d","e"))
    return species,counts,vals,entries,electrons,nelect


def manifest_cases(root,manifest):
    if manifest:
        if not manifest.is_file():raise ValueError("missing manifest")
        found=set()
        for line in manifest.read_text().splitlines():
            line=line.strip()
            if not line or line.startswith("#"):continue
            path=Path(line)
            run=(path if path.is_absolute() else root/path).resolve()
            if not run.is_relative_to(root) or not run.is_dir():
                raise ValueError(f"invalid/outside case: {line}")
            found.add(run)
        return sorted(found)
    return sorted({p.parent for p in root.rglob("CHGCAR")
                   if "postprocess" not in p.relative_to(root).parts})


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root",type=Path)
    ap.add_argument("--prepare",action="store_true",help="Make isolated Nval CHGCAR working copy")
    ap.add_argument("--manifest",type=Path)
    ap.add_argument("--net-charge",type=float,help="Explicit expected cell charge for QC")
    opt=ap.parse_args(argv)
    root=opt.root.expanduser().resolve()
    if not root.is_dir():ap.error("root directory missing")
    try:
        cases=manifest_cases(root,opt.manifest)
    except ValueError as exc:
        ap.error(str(exc))
    if not cases:ap.error("no input CHGCAR found")
    failures=0
    for case in cases:
        label=case.relative_to(root)
        try:
            names,counts,zvals,entries,electrons,nelect=valence_metadata(case)
            charge=electrons-nelect if nelect is not None else None
            if opt.net_charge is not None and charge is not None and abs(charge-opt.net_charge)>1e-3:
                raise ValueError(f"charge from OUTCAR is {charge:.6f}, expected {opt.net_charge:.6f}")
            first="Nval "+" ".join(f"{e} {v:g}" for e,v in zip(names,zvals))
            result=f"{first}; valence sum {electrons:g}; OUTCAR NELECT {nelect}; expected q {charge}"
            if not opt.prepare:
                print(f"READY {label}: {result}")
                continue
            folder=case/"postprocess"/"multiwfn"
            target=folder/"CHGCAR_Nval"
            folder.mkdir(parents=True,exist_ok=True)
            if target.exists():
                raise ValueError(f"staged input already exists (no overwrite): {target}")
            with (case/"CHGCAR").open("rb") as src, target.open("xb") as dst:
                src.readline()
                dst.write((first+"\n").encode("ascii"))
                shutil.copyfileobj(src,dst,1024*1024)
            print(f"PREPARED {label}: {target} | {result}")
        except (OSError,ValueError) as exc:
            failures+=1
            print(f"ERROR {label}: {exc}")
    return 1 if failures else 0


if __name__=="__main__":
    sys.exit(main())
