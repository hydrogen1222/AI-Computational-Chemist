#!/usr/bin/env python3
"""Collect *ordinary, noniterative* Hirshfeld and CM5 charges from Chargemol DDEC6 logs.

No VASP or Chargemol execution. Default is read-only discovery; use
--collect-only to write per-atom/per-element CSV, a human report and optional
PNG/SVG charts. This does NOT compute iterative Hirshfeld-I.
"""
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
import re
import sys

from batch_ddec6 import source_structure, xyz_properties

LOG = "VASP_DDEC_analysis.output"
DDEC = "DDEC6_even_tempered_net_atomic_charges.xyz"
PERIODIC = ("H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe "
            "Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn "
            "Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta "
            "W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm "
            "Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og").split()
ATOMS = ["case", "atom_index_1based", "element", "hirshfeld_net_charge_e",
         "cm5_net_charge_e", "ddec6_net_charge_e", "source_log"]
ELEMENTS = ["case", "element", "count", "hirshfeld_mean_e", "hirshfeld_min_e",
            "hirshfeld_max_e", "cm5_mean_e", "ddec6_mean_e"]
CASES = ["case", "status", "detail", "n_atoms", "hirshfeld_charge_sum_e",
         "cm5_charge_sum_e", "ddec6_charge_sum_e", "expected_net_charge_e",
         "source_log"]


def args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path, help="VASP directory or parent of several runs")
    p.add_argument("--collect-only", action="store_true",
                   help="Parse logs and write summaries; never starts executables")
    p.add_argument("--manifest", type=Path, help="One run directory per line, relative to root")
    p.add_argument("--net-charge", type=float, help="Expected cell net charge in e, optional QC")
    p.add_argument("--charge-tol", type=float, default=0.05,
                   help="Charge-balance tolerance e (default 0.05)")
    return p.parse_args(argv)


def find_cases(root: Path, manifest: Path | None):
    if manifest:
        if not manifest.is_file():
            raise ValueError(f"missing manifest: {manifest}")
        result = []
        for line in manifest.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            p = Path(line)
            run = (p if p.is_absolute() else root / p).resolve()
            if not run.is_relative_to(root) or not run.is_dir():
                raise ValueError(f"case not inside root: {line}")
            result.append(run)
        return sorted(set(result))
    cases = set()
    for file in root.rglob(LOG):
        if "postprocess" in file.parts and file.parent.name == "chargemol" \
                and file.parent.parent.name == "postprocess":
            run = file.parent.parent.parent
        else:
            run = file.parent
        if run.resolve().is_relative_to(root) and (run / "CHGCAR").is_file():
            cases.add(run.resolve())
    return sorted(cases)


def find_log(run: Path) -> Path:
    # The standard AICC output location takes precedence.
    for path in (run / "postprocess" / "chargemol" / LOG, run / LOG):
        if path.is_file():
            return path
    raise ValueError("missing Chargemol log VASP_DDEC_analysis.output")


def _float(token: str) -> float:
    value = float(token.replace("D", "E").replace("d", "e"))
    if not math.isfinite(value):
        raise ValueError("nonfinite atomic charge")
    return value


def read_first_partition(log: Path, symbols: list[str]):
    """Parse the labeled *first* Hirshfeld partition; never use later DDEC steps."""
    raw = log.read_text(encoding="utf-8", errors="replace")
    head = "Information for noniterative Hirshfeld method will be printed now."
    end = "Information for noniterative CM5 method will be printed now."
    first = raw.find(head)
    after = raw.find(end, first + len(head)) if first >= 0 else -1
    if first < 0 or after < 0:
        raise ValueError("noniterative Hirshfeld block absent/incomplete; not substituting DDEC6")
    section = raw[first:after]
    lines = section.splitlines()
    charge_header = next((i for i, line in enumerate(lines)
                          if "center number, atomic number, x, y, z, net_charge" in line), None)
    if charge_header is None:
        raise ValueError("Hirshfeld multipole table header absent")
    q = []
    for line in lines[charge_header+1:]:
        tokens = line.split()
        if len(tokens) < 6 or not tokens[0].isdigit() or not tokens[1].isdigit():
            if q:
                break
            continue
        idx, atomic_num = int(tokens[0]), int(tokens[1])
        if idx != len(q) + 1:
            raise ValueError(f"Hirshfeld atom order mismatch at index {idx}")
        if atomic_num != PERIODIC.index(symbols[idx-1]) + 1:
            raise ValueError(f"Hirshfeld element mismatch at atom {idx}")
        q.append(_float(tokens[5]))
        if len(q) == len(symbols):
            break
    if len(q) != len(symbols):
        raise ValueError(f"Hirshfeld table truncated: {len(q)}/{len(symbols)} atoms")

    cm5_label = "The computed CM5 net atomic charges are:"
    cm5_at = raw.find(cm5_label, after)
    cm5 = None
    if cm5_at >= 0:
        values = []
        for line in raw[cm5_at + len(cm5_label):].splitlines():
            parts = line.split()
            if not parts:
                continue
            try:
                floats = [_float(x) for x in parts]
            except ValueError:
                break
            values.extend(floats)
            if len(values) >= len(symbols):
                break
        if len(values) != len(symbols):
            raise ValueError(f"CM5 charge table incomplete: {len(values)}/{len(symbols)} atoms")
        cm5 = values
    return q, cm5


def load_case(run: Path, case: str, expected: float | None, tol: float):
    symbols = source_structure(run)
    log = find_log(run)
    hirsh, cm5 = read_first_partition(log, symbols)
    charge_xyz = log.parent / DDEC
    if not charge_xyz.is_file():
        charge_xyz = run / DDEC
    ddec = xyz_properties(charge_xyz, symbols) if charge_xyz.is_file() else None
    for name, vals in (("Hirshfeld", hirsh), ("CM5", cm5), ("DDEC6", ddec)):
        if vals is not None and expected is not None and abs(sum(vals)-expected) > tol:
            raise ValueError(f"{name} charge sum {sum(vals):+.7f} e differs from expected {expected:+.7f} e")
    atoms = []
    for i, element in enumerate(symbols):
        atoms.append({
            "case": case, "atom_index_1based": i+1, "element": element,
            "hirshfeld_net_charge_e": round(hirsh[i], 6),
            "cm5_net_charge_e": round(cm5[i], 6) if cm5 else "",
            "ddec6_net_charge_e": round(ddec[i], 6) if ddec else "",
            "source_log": str(log)
        })
    per_el = []
    for el in sorted(set(symbols)):
        ix = [i for i,x in enumerate(symbols) if x == el]
        h = [hirsh[i] for i in ix]
        per_el.append({
            "case": case, "element": el, "count": len(ix),
            "hirshfeld_mean_e": round(sum(h)/len(h), 6),
            "hirshfeld_min_e": round(min(h), 6),
            "hirshfeld_max_e": round(max(h), 6),
            "cm5_mean_e": round(sum(cm5[i] for i in ix)/len(ix),6) if cm5 else "",
            "ddec6_mean_e": round(sum(ddec[i] for i in ix)/len(ix),6) if ddec else "",
        })
    result = {"case": case, "status": "OK", "detail": "log parsed; ordinary Hirshfeld (not Hirshfeld-I)",
              "n_atoms": len(symbols), "hirshfeld_charge_sum_e": round(sum(hirsh), 6),
              "cm5_charge_sum_e": round(sum(cm5), 6) if cm5 else "",
              "ddec6_charge_sum_e": round(sum(ddec), 6) if ddec else "",
              "expected_net_charge_e": expected if expected is not None else "NOT_CHECKED",
              "source_log": str(log)}
    return result, atoms, per_el


def csv_out(path: Path, fields, records):
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def report(path: Path, statuses, elements, expected):
    with path.open("w", encoding="utf-8") as doc:
        doc.write("# Hirshfeld / CM5 / DDEC6 charge comparison\n\n"
                  "These **noniterative ordinary Hirshfeld** charges are read from "
                  "Chargemol's first DDEC6 partition; **not Hirshfeld-I**. "
                  "No VASP or Chargemol calculations were performed.\n\n"
                  "Positive net charge denotes electron depletion. CM5 and DDEC6 "
                  "are distinct charge-assignment methods.\n\n"
                  f"Expected net charge (e): {expected if expected is not None else 'NOT CHECKED'}.\n\n"
                  "## Analysis status\n\n"
                  "| Case | Status | Atoms | Σq Hirshfeld (e) | Details |\n"
                  "|---|---|---:|---:|---|\n")
        for item in statuses:
            doc.write(f"| {item['case']} | {item['status']} | {item['n_atoms']} | "
                      f"{item['hirshfeld_charge_sum_e']} | "
                      f"{item['detail'].replace('|','/')} |\n")
        doc.write("\n## All element-resolved charges (e)\n\n"
                  "| Case | Element | N | Hirshfeld mean [min,max] | CM5 mean | DDEC6 mean |\n"
                  "|---|---|---:|---|---:|---:|\n")
        for entry in elements:
            doc.write(f"| {entry['case']} | {entry['element']} | {entry['count']} | "
                      f"{entry['hirshfeld_mean_e']:+.4f} "
                      f"[{entry['hirshfeld_min_e']:+.4f}, {entry['hirshfeld_max_e']:+.4f}] | "
                      f"{entry['cm5_mean_e']} | {entry['ddec6_mean_e']} |\n")
        doc.write("\n## Figure caption template\n\n"
                  "Net atomic charges for [model] from noniterative Hirshfeld, CM5 "
                  "and DDEC6 population analyses of the same VASP density using "
                  "Chargemol. Bars show per-element arithmetic means, not oxidation "
                  "states; distinguish atom-to-atom ranges from statistical errors.\n"
                  "\n## Interpretation limits\n\n"
                  "Conservation of net charge and agreement between parsers cannot "
                  "alone validate electron-density convergence or scientific model "
                  "adequacy. For strongly ionic solids, noniterative Hirshfeld often "
                  "underestimates charge transfer; report the method name precisely. "
                  "Hirshfeld-I uses charge-updated reference atoms and is **not** "
                  "computed by this parser.\n")


def make_plots(folder: Path, elements):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("NOTE: matplotlib unavailable; CSV and Markdown were generated")
        return
    import hashlib
    dest = folder / "ppt_figures"
    dest.mkdir(exist_ok=True)
    plt.rcParams["svg.fonttype"] = "none"
    cases = sorted({r["case"] for r in elements})
    methods = [("hirshfeld_mean_e","Hirshfeld"), ("cm5_mean_e","CM5"),
               ("ddec6_mean_e","DDEC6")]
    total = 0
    for case in cases:
        values = sorted((x for x in elements if x["case"] == case),
                        key=lambda x:x["element"])
        for page, offset in enumerate(range(0, len(values), 10), 1):
            batch = values[offset:offset+10]
            fig, ax = plt.subplots(figsize=(12.8,7.2), constrained_layout=True)
            xs = list(range(len(batch)))
            for mi, (key, name) in enumerate(methods):
                ids = [i for i,x in enumerate(batch) if x[key] != ""]
                if ids:
                    ax.bar([xs[i]+(mi-1)*0.24 for i in ids],
                           [float(batch[i][key]) for i in ids],
                           width=0.22, label=name)
            ax.axhline(0, color="black", alpha=.5, lw=.8)
            ax.set_xticks(xs, [f"{x['element']} (n={x['count']})" for x in batch])
            ax.set_ylabel("Mean net atomic charge (e)")
            ax.set_title(f"Population analysis — {case} [{page}]\n"
                         "Same density; distinct partition definitions", loc="left")
            ax.legend()
            ax.grid(axis="y",alpha=.15)
            ax.set_axisbelow(True)
            suffix = hashlib.sha256(case.encode()).hexdigest()[:8]
            stem = re.sub(r"[^a-zA-Z0-9_.-]","_",case)[:65] + "_" + suffix
            if page > 1:
                stem += f"_part{page:02d}"
            for ext, kw in ((".svg",{}),(".png",{"dpi":300})):
                fig.savefig(dest / (stem+"_charge_methods"+ext),bbox_inches="tight",**kw)
            plt.close(fig)
            total += 1
    print(f"Created {total} SVG/PNG comparison figure pairs, all cases and all elements")


def main(argv=None):
    opts = args(argv)
    root = opts.root.expanduser().resolve()
    if not root.is_dir() or opts.charge_tol <= 0:
        print("Invalid root or charge tolerance", file=sys.stderr)
        return 2
    try:
        cases = find_cases(root, opts.manifest)
    except (OSError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    if not cases:
        print("No Chargemol logs / source VASP densities found", file=sys.stderr)
        return 2
    print(f"Hirshfeld / CM5 log discovery: {len(cases)} cases")
    if not opts.collect_only:
        for run in cases:
            print(f"READY {run}")
        print("Read-only discovery completed. Use --collect-only to export charges.")
        return 0
    statuses, atoms, elements = [], [], []
    failures = 0
    for run in cases:
        name = "." if run == root else run.relative_to(root).as_posix()
        try:
            st, at, el = load_case(run, name, opts.net_charge, opts.charge_tol)
            statuses.append(st); atoms.extend(at); elements.extend(el)
            print(f"OK {name}: ordinary Hirshfeld extracted")
        except (ValueError, OSError) as e:
            failures += 1
            statuses.append({"case": name, "status":"ERROR", "detail":str(e),
                             "n_atoms":"", "hirshfeld_charge_sum_e":"",
                             "cm5_charge_sum_e":"", "ddec6_charge_sum_e":"",
                             "expected_net_charge_e":opts.net_charge if opts.net_charge is not None else "",
                             "source_log":str(run)})
            print(f"ERROR {name}: {e}")
    output = root / "postprocess_summary"
    output.mkdir(exist_ok=True)
    csv_out(output / "hirshfeld_cases.csv", CASES, statuses)
    csv_out(output / "hirshfeld_atoms.csv", ATOMS, atoms)
    csv_out(output / "hirshfeld_elements.csv", ELEMENTS, elements)
    report(output / "hirshfeld_summary.md", statuses, elements, opts.net_charge)
    make_plots(output, elements)
    print(f"Wrote {len(atoms)} atoms and {len(elements)} element groups to {output}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
