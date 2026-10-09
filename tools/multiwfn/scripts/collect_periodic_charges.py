#!/usr/bin/env python3
"""Batch parse verified Multiwfn Hirshfeld / CM5 / Hirshfeld-I logs for VASP.

Requires separate, version-validated Multiwfn runs in each case's
postprocess/multiwfn/{hirshfeld,cm5,hirshfeld_i}.log.
Does not run Multiwfn or DFT. Do not parse unrelated menu text as charges.
"""
from __future__ import annotations
import argparse
import csv
import math
from pathlib import Path
import re
import sys
from prepare_periodic_chgcar import valence_metadata,manifest_cases
# Existing validated Chargemol parsers live in the VASP software-tool folder.
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"vasp"/"scripts"))
from batch_ddec6 import xyz_properties,CHARGE_FILE
from collect_hirshfeld import read_first_partition,find_log

NUM=r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][+-]?\d+)?"
ATOM=re.compile(r"Atom\s+(\d+)\(\s*([A-Z][a-z]?)\s*\)\s*:\s*("+NUM+r")")
CM5=re.compile(r"Atom:\s*(\d+)\s*([A-Z][a-z]?)\s+CM5 charge:\s*("+NUM+r")",re.I)
METHODS=("hirshfeld","cm5","hirshfeld_i")
FIELDS=["case","atom_1based","element","multiwfn_hirshfeld_e",
        "multiwfn_cm5_e","multiwfn_hirshfeld_i_e",
        "chargemol_hirshfeld_e","chargemol_cm5_e","chargemol_ddec6_e",
        "delta_hirshfeld_e","delta_cm5_e"]
QC=["case","method","status","detail","charge_sum_e","expected_charge_e","log"]
ELEMS=["case","element","method","n_atoms","mean_q_e","min_q_e","max_q_e"]


def symbols_of(names,counts):
    return [x for x,n in zip(names,counts) for _ in range(n)]


def parse_file(file,method,symbols):
    if not file.is_file():raise ValueError("log missing")
    text=file.read_text(encoding="utf-8",errors="replace")
    if "forrtl: severe" in text.lower() or "segmentation fault" in text.lower():
        raise ValueError("Multiwfn runtime failure")
    if method=="cm5":
        found=CM5.findall(text)
    else:
        markers=list(re.finditer(r"Final atomic charges\s*:",text,re.I))
        if not markers:
            raise ValueError("Final atomic charges marker not found")
        # Use the last section (Multiwfn may show intermediate iteration data).
        found=ATOM.findall(text[markers[-1].end():])
    if len(found)!=len(symbols):
        raise ValueError(f"found {len(found)} charge rows, need {len(symbols)}")
    values=[]
    for i,(index,element,number) in enumerate(found):
        if int(index)!=i+1 or element!=symbols[i]:
            raise ValueError(f"atom mapping mismatch at {i+1}")
        q=float(number.replace("D","E").replace("d","e"))
        if not math.isfinite(q):raise ValueError("nonfinite charge")
        values.append(q)
    return values


def existing_chargemol(case,symbols):
    output={}
    try:
        log=find_log(case)
        h,c=read_first_partition(log,symbols)
        output["hirshfeld"]=h
        if c is not None:output["cm5"]=c
    except (ValueError,OSError):
        pass
    for x in (case/"postprocess"/"chargemol"/CHARGE_FILE,case/CHARGE_FILE):
        if x.is_file():
            output["ddec6"]=xyz_properties(x,symbols)
            break
    return output


def write_csv(path,fields,rows):
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def plot(folder,rows):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("Matplotlib unavailable; CSV and Markdown remain complete")
        return
    import hashlib
    folder.mkdir(exist_ok=True)
    plt.rcParams["svg.fonttype"]="none"
    cols=[("multiwfn_hirshfeld_e","Multiwfn H"),
          ("multiwfn_cm5_e","Multiwfn CM5"),
          ("multiwfn_hirshfeld_i_e","Multiwfn H-I"),
          ("chargemol_ddec6_e","Chargemol DDEC6")]
    for case in sorted({r["case"] for r in rows}):
        data=[r for r in rows if r["case"]==case]
        kinds=sorted({r["element"] for r in data})
        for page,start in enumerate(range(0,len(kinds),8),1):
            selected=kinds[start:start+8]
            fig,ax=plt.subplots(figsize=(12.8,7.2),constrained_layout=True)
            for i,(key,label) in enumerate(cols):
                xx,yy=[],[]
                for j,el in enumerate(selected):
                    values=[float(r[key]) for r in data if r["element"]==el and r[key]!=""]
                    if values:
                        xx.append(j+(i-1.5)*0.18);yy.append(sum(values)/len(values))
                if yy:ax.bar(xx,yy,width=.17,label=label)
            ax.set_xticks(list(range(len(selected))),selected)
            ax.axhline(0,color="black",alpha=.4,lw=.8)
            ax.set_ylabel("Mean net atomic charge (e)")
            ax.set_title(f"Population methods — {case} [{page}]\n"
                         "Distinct density-partition/reference conventions",loc="left")
            ax.legend();ax.grid(axis="y",alpha=.15)
            stem=re.sub(r"[^a-zA-Z0-9_.-]","_",case)[:55] + "_" + hashlib.sha256(case.encode()).hexdigest()[:7]+f"_page{page:02d}"
            for ext,kw in ((".svg",{}),(".png",{"dpi":300})):
                fig.savefig(folder/(stem+ext),bbox_inches="tight",**kw)
            plt.close(fig)


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root",type=Path)
    ap.add_argument("--manifest",type=Path)
    ap.add_argument("--net-charge",type=float,help="Expected cell net charge; otherwise use OUTCAR if present")
    ap.add_argument("--charge-tol",type=float,default=0.05)
    opt=ap.parse_args(argv)
    root=opt.root.expanduser().resolve()
    if not root.is_dir() or opt.charge_tol<=0:ap.error("invalid root or charge tolerance")
    try:
        cases=manifest_cases(root,opt.manifest)
    except ValueError as e:ap.error(str(e))
    if not cases:ap.error("no source cases")
    rows,quality,elements=[],[],[]
    failures=0
    for case in cases:
        name="." if case==root else case.relative_to(root).as_posix()
        try:
            names,counts,zvals,_,nval,nelect=valence_metadata(case)
            symbols=symbols_of(names,counts)
            expected=opt.net_charge if opt.net_charge is not None else (
                nval-nelect if nelect is not None else None)
            if nelect is not None and opt.net_charge is not None and abs(nval-nelect-opt.net_charge)>1e-3:
                raise ValueError("OUTCAR NELECT and --net-charge disagree")
            results={}
            for method in METHODS:
                path=case/"postprocess"/"multiwfn"/(method+".log")
                try:
                    charges=parse_file(path,method,symbols)
                    if expected is not None and abs(sum(charges)-expected)>opt.charge_tol:
                        raise ValueError(f"charge sum {sum(charges):+.6f} vs expected {expected:+.6f}")
                    results[method]=charges
                    quality.append(dict(case=name,method=method,status="OK",
                                        detail="parsed; manually confirm Hirshfeld-I convergence",
                                        charge_sum_e=round(sum(charges),7),
                                        expected_charge_e=expected if expected is not None else "NOT_VERIFIED",
                                        log=str(path)))
                except (ValueError,OSError) as e:
                    failures+=1
                    quality.append(dict(case=name,method=method,status="ERROR",detail=str(e),
                                        charge_sum_e="",expected_charge_e=expected if expected is not None else "NOT_VERIFIED",
                                        log=str(path)))
            compare=existing_chargemol(case,symbols)
            for i,el in enumerate(symbols):
                def val(d,key):return round(d[key][i],7) if key in d else ""
                h=val(results,"hirshfeld");c=val(results,"cm5")
                hc=val(compare,"hirshfeld");cc=val(compare,"cm5")
                rows.append(dict(case=name,atom_1based=i+1,element=el,
                                 multiwfn_hirshfeld_e=h,multiwfn_cm5_e=c,
                                 multiwfn_hirshfeld_i_e=val(results,"hirshfeld_i"),
                                 chargemol_hirshfeld_e=hc,chargemol_cm5_e=cc,
                                 chargemol_ddec6_e=val(compare,"ddec6"),
                                 delta_hirshfeld_e=round(h-hc,7) if h!="" and hc!="" else "",
                                 delta_cm5_e=round(c-cc,7) if c!="" and cc!="" else ""))
            for method,charges in results.items():
                for el in sorted(set(symbols)):
                    q=[charges[i] for i,sym in enumerate(symbols) if sym==el]
                    elements.append(dict(case=name,element=el,method=method,n_atoms=len(q),
                                         mean_q_e=round(sum(q)/len(q),7),
                                         min_q_e=round(min(q),7),max_q_e=round(max(q),7)))
            print(f"{name}: {len(results)}/3 Multiwfn methods read")
        except (OSError,ValueError) as e:
            failures+=1
            print(f"ERROR {name}: {e}")
            quality.append(dict(case=name,method="preflight",status="ERROR",detail=str(e),
                                charge_sum_e="",expected_charge_e="",log=""))
    folder=root/"postprocess_summary"
    folder.mkdir(exist_ok=True)
    write_csv(folder/"multiwfn_atoms.csv",FIELDS,rows)
    write_csv(folder/"multiwfn_elements.csv",ELEMS,elements)
    write_csv(folder/"multiwfn_qc.csv",QC,quality)
    with (folder/"multiwfn_charge_comparison.md").open("w",encoding="utf-8") as f:
        f.write("# Multiwfn periodic atomic charges\n\n"
                "Multiwfn H, CM5 and H-I use the original VASP valence CHGCAR "
                "with POTCAR-derived Nval. Chargemol comparisons use separate "
                "reference densities/algorithms; do not expect numeric identity.\n\n"
                "## QC\n\n| Case | Method | Status | Σq (e) | Expected | Detail |\n"
                "|---|---|---|---:|---:|---|\n")
        for row in quality:
            f.write(f"| {row['case']} | {row['method']} | {row['status']} | "
                    f"{row['charge_sum_e']} | {row['expected_charge_e']} | "
                    f"{row['detail']} |\n")
        f.write("\n## Per-atom comparison (e)\n\n"
                "| Case | Atom | Element | Multiwfn H | Multiwfn CM5 | "
                "Multiwfn H-I | Chargemol H | Chargemol CM5 | DDEC6 |\n"
                "|---|---:|---|---:|---:|---:|---:|---:|---:|\n")
        for r in rows:
            f.write(f"| {r['case']} | {r['atom_1based']} | {r['element']} | "
                    f"{r['multiwfn_hirshfeld_e']} | {r['multiwfn_cm5_e']} | "
                    f"{r['multiwfn_hirshfeld_i_e']} | {r['chargemol_hirshfeld_e']} | "
                    f"{r['chargemol_cm5_e']} | {r['chargemol_ddec6_e']} |\n")
        f.write("\nMethod-dependent charges are not oxidation states. "
                "For Hirshfeld-I, confirm genuine iterative convergence from "
                "its complete Multiwfn log. No MBIS is computed.\n")
    plot(folder/"ppt_figures",rows)
    print(f"Output: {folder}; failed or missing methods: {failures}")
    return 1 if failures else 0


if __name__=="__main__":
    sys.exit(main())
