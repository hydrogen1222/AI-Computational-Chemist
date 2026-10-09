#!/usr/bin/env python3
"""Batch VASP Chargemol DDEC6 charges and periodic bond orders.

Dry-run by default; --execute runs Chargemol (never VASP); --collect-only parses
existing outputs. No external Python dependencies. No overwrite or job submission.
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import importlib.util
from pathlib import Path
import re
from software_locator import DiscoveryError, find_executable, find_chargemol_densities
import subprocess
import sys

INPUTS = ("CHGCAR", "AECCAR0", "AECCAR2", "POTCAR")
CHARGE_FILE = "DDEC6_even_tempered_net_atomic_charges.xyz"
BONDS_FILE = "DDEC6_even_tempered_bond_orders.xyz"
HEADER = ["case", "status", "detail", "n_atoms", "net_charge_e",
          "sum_ddec6_q_e", "charge_balance_error_e", "source", "chargemol_dir"]
ATOMS = ["case", "atom_index_1based", "element", "ddec6_net_charge_e",
         "sum_bond_orders", "source_xyz"]
BONDS = ["case", "atom_i_1based", "element_i", "atom_j_1based", "element_j",
         "translation_a", "translation_b", "translation_c", "ddec6_bond_order",
         "source_xyz"]
ELEMENTS = ["case", "element", "n_atoms", "mean_charge_e", "min_charge_e",
            "max_charge_e", "mean_sbo", "min_sbo", "max_sbo"]
BOND_TYPES = ["case", "element_pair", "n_periodic_bonds", "mean_bond_order",
              "min_bond_order", "max_bond_order"]


def cli(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--execute", action="store_true", help="Run installed Chargemol; request user approval first")
    mode.add_argument("--collect-only", action="store_true", help="Read existing Chargemol output files")
    p.add_argument("--manifest", type=Path, help="Optional case directories (newline-separated)")
    p.add_argument("--binary", help="Optional executable path/name; auto-discover if omitted")
    p.add_argument("--atomic-densities", type=Path, help="Installed Chargemol atomic_densities directory")
    p.add_argument("--net-charge", type=float, help="Expected cell net charge in e, required with --execute")
    p.add_argument("--charge-tol", type=float, default=0.05, help="Maximum abs(sum q - expected q), in e")
    p.add_argument("--timeout", type=int, default=0, help="Chargemol seconds per case; 0 = unlimited")
    return p.parse_args(argv)


def discover(root: Path, manifest: Path | None, collect_only: bool):
    if manifest:
        if not manifest.is_file():
            raise ValueError(f"manifest missing: {manifest}")
        roots = []
        for line in manifest.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            p = Path(line)
            d = (p if p.is_absolute() else root / p).resolve()
            if not d.is_relative_to(root) or not d.is_dir():
                raise ValueError(f"manifest case outside root or absent: {line}")
            roots.append(d)
        return sorted(set(roots))
    found = set()
    for p in [root / "CHGCAR", *root.rglob("CHGCAR")]:
        if p.is_file() and "postprocess" not in p.relative_to(root).parts:
            found.add(p.parent.resolve())
    if collect_only:
        for p in root.rglob(CHARGE_FILE):
            if p.parent.name == "chargemol" and p.parent.parent.name == "postprocess":
                found.add(p.parent.parent.parent.resolve())
    return sorted(found)


def source_structure(folder: Path):
    """CHGCAR embeds exact VASP species order; only inspect its small text header."""
    source = folder / "CHGCAR"
    if not source.is_file():
        raise ValueError("missing CHGCAR (needed to confirm source atom ordering)")
    with source.open(errors="replace") as fh:
        lines = [next(fh, "") for _ in range(8)]
    species = lines[5].split()
    try:
        counts = [int(x) for x in lines[6].split()]
    except ValueError as e:
        raise ValueError("bad CHGCAR VASP5 element/count header") from e
    if not species or len(species) != len(counts) or any(n <= 0 for n in counts):
        raise ValueError("CHGCAR species/atom count ambiguous; VASP5 format required")
    names = [el for el, n in zip(species, counts) for _ in range(n)]
    return names


def xyz_properties(path: Path, expected_symbols: list[str]):
    if not path.is_file():
        raise ValueError(f"missing result: {path}")
    with path.open(errors="replace") as fh:
        try:
            n = int(next(fh).strip())
        except (ValueError, StopIteration) as e:
            raise ValueError(f"bad Chargemol XYZ atom-count header in {path}") from e
        next(fh, None)  # comment
        if n != len(expected_symbols):
            raise ValueError(f"{path.name}: {n} atoms vs source {len(expected_symbols)}")
        values = []
        for i, elem in enumerate(expected_symbols):
            line = next(fh, "").split()
            if len(line) < 5 or line[0] != elem:
                raise ValueError(f"{path.name}: atom {i+1} element/order mismatch ({line[:1]} vs {elem})")
            try:
                value = float(line[-1])
            except ValueError as e:
                raise ValueError(f"{path.name}: bad numeric property at atom {i+1}") from e
            if not math.isfinite(value):
                raise ValueError(f"{path.name}: non-finite property at atom {i+1}")
            values.append(value)
    return values


def read_bonds(path: Path, symbols: list[str], sums: list[float]):
    """Chargemol's 'Printing BOs' sections, as parsed by pymatgen 2026.9.23.

    Preserve atom pair and periodic image; de-duplicate reverse listings.
    """
    raw = {}
    anchor = None
    reported = {}
    for raw_line in path.read_text(errors="replace").splitlines():
        tok = raw_line.split()
        if "Printing BOs" in raw_line:
            try:
                anchor = int(tok[5])
                element = tok[7]
            except (ValueError, IndexError) as e:
                raise ValueError("unrecognized 'Printing BOs' format") from e
            if not 1 <= anchor <= len(symbols) or symbols[anchor-1] != element:
                raise ValueError(f"BO source atom mapping differs: {anchor} {element}")
        elif "Bonded to the" in raw_line:
            if anchor is None:
                raise ValueError("BO neighbor without anchor")
            try:
                shift = tuple(int(part.split(")")[0].split(",")[0]) for part in tok[4:7])
                partner, element, bo = int(tok[12]), tok[14], float(tok[20])
            except (ValueError, IndexError) as e:
                raise ValueError("unrecognized 'Bonded to the' BO format") from e
            if len(shift) != 3 or not 1 <= partner <= len(symbols) or symbols[partner-1] != element:
                raise ValueError(f"BO partner mapping differs: {anchor}->{partner} {element}")
            if not math.isfinite(bo) or bo < 0:
                raise ValueError("nonfinite/negative DDEC6 bond order")
            if anchor == partner and shift == (0, 0, 0):
                raise ValueError("self bond with zero lattice shift")
            key = (anchor, partner, *shift)
            if key in raw and abs(raw[key] - bo) > 0.0001:
                raise ValueError(f"duplicate BO entry differs: {key}")
            raw[key] = bo
        elif "The sum of bond orders for this atom" in raw_line and anchor is not None:
            try:
                reported[anchor] = float(tok[-1])
            except ValueError as e:
                raise ValueError("bad BO sum reported value") from e
    if not reported and not raw:
        # 'xyz' may contain SBO only but no printed pairs. This is
        # inappropriate for user-requested pairwise bond-order export.
        raise ValueError("no atom-resolved BO sections found (cannot report pairwise bonds)")
    for idx, val in reported.items():
        if abs(val - sums[idx-1]) > 0.03:
            raise ValueError(f"SBO mismatch in two Chargemol output sections for atom {idx}")
    result = {}
    for a, b, dx, dy, dz in raw:
        reverse = (b, a, -dx, -dy, -dz)
        canonical = min((a, b, dx, dy, dz), reverse)
        if canonical in result and abs(result[canonical] - raw[(a,b,dx,dy,dz)]) > 0.001:
            raise ValueError(f"nonreciprocal BO for {canonical}")
        result[canonical] = raw[(a,b,dx,dy,dz)]
    return [{"atom_i_1based": a, "element_i": symbols[a-1],
             "atom_j_1based": b, "element_j": symbols[b-1],
             "translation_a": dx, "translation_b": dy, "translation_c": dz,
             "ddec6_bond_order": round(bo, 8)}
            for (a,b,dx,dy,dz), bo in sorted(result.items())]


def read_analysis(case: str, run: Path, expected_charge: float | None, tol: float):
    symbols = source_structure(run)
    output = run / "postprocess" / "chargemol"
    if not (output / CHARGE_FILE).is_file() and (run / CHARGE_FILE).is_file():
        output = run  # support manually run Chargemol in the VASP directory
    charge_path, bo_path = output / CHARGE_FILE, output / BONDS_FILE
    q = xyz_properties(charge_path, symbols)
    sbo = xyz_properties(bo_path, symbols)
    pair = read_bonds(bo_path, symbols, sbo)
    total = sum(q)
    if expected_charge is not None and abs(total - expected_charge) > tol:
        raise ValueError(f"charge sum {total:.6f} e differs from expected {expected_charge:.6f} e")
    atoms = [{"case": case, "atom_index_1based": i+1, "element": el,
              "ddec6_net_charge_e": round(q[i], 8), "sum_bond_orders": round(sbo[i], 8),
              "source_xyz": str(charge_path)}
             for i, el in enumerate(symbols)]
    bonds = [{"case": case, **b, "source_xyz": str(bo_path)} for b in pair]
    els, types = [], []
    for el in sorted(set(symbols)):
        ix = [i for i, x in enumerate(symbols) if x == el]
        charges, sbos = [q[i] for i in ix], [sbo[i] for i in ix]
        els.append({"case": case, "element": el, "n_atoms": len(ix),
                    "mean_charge_e": round(sum(charges)/len(ix), 8),
                    "min_charge_e": round(min(charges), 8), "max_charge_e": round(max(charges), 8),
                    "mean_sbo": round(sum(sbos)/len(ix), 8),
                    "min_sbo": round(min(sbos), 8), "max_sbo": round(max(sbos), 8)})
    pair_types = {}
    for b in bonds:
        label = "-".join(sorted((b["element_i"], b["element_j"])))
        pair_types.setdefault(label, []).append(b["ddec6_bond_order"])
    for label, vals in sorted(pair_types.items()):
        types.append({"case": case, "element_pair": label, "n_periodic_bonds": len(vals),
                      "mean_bond_order": round(sum(vals)/len(vals), 8),
                      "min_bond_order": round(min(vals), 8), "max_bond_order": round(max(vals), 8)})
    return atoms, bonds, els, types, total, str(output)


def exec_chargemol(run: Path, opts):
    work = run / "postprocess" / "chargemol"
    if work.exists():
        if (work / CHARGE_FILE).is_file() and (work / BONDS_FILE).is_file():
            return "reused pre-existing outputs"
        raise ValueError(f"nonempty or partial Chargemol workdir: {work}; inspect manually")
    if not hasattr(opts, "_resolved_chargemol"):
        exe = find_executable("chargemol", opts.binary)
        density = find_chargemol_densities(opts.atomic_densities, exe)
        opts._resolved_chargemol = (exe, density)
        print(f"Chargemol discovered: {exe}; atomic densities: {density}")
    binary, densities = opts._resolved_chargemol
    missing = [n for n in INPUTS if not (run/n).is_file()]
    if missing:
        raise ValueError("missing " + ", ".join(missing))
    if opts.net_charge is None:
        raise ValueError("explicit --net-charge required; never assume neutral cells")
    work.mkdir(parents=True, exist_ok=False)
    for name in INPUTS:
        (work/name).symlink_to((run/name).resolve())
    (work/"job_control.txt").write_text(
        f"<net charge>\n{opts.net_charge:.9f}\n</net charge>\n"
        "<periodicity along A, B, and C vectors>\n.true.\n.true.\n.true.\n"
        "</periodicity along A, B, and C vectors>\n"
        f"<atomic densities directory complete path>\n{densities.as_posix()}/\n"
        "</atomic densities directory complete path>\n"
        "<charge type>\nDDEC6\n</charge type>\n"
        "<compute BOs>\n.true.\n</compute BOs>\n",
        encoding="utf-8")
    with (work/"chargemol_stdout.log").open("w") as log:
        try:
            proc = subprocess.run([binary], cwd=work, stdout=log,
                                  stderr=subprocess.STDOUT, check=False,
                                  timeout=opts.timeout if opts.timeout>0 else None)
        except subprocess.TimeoutExpired as e:
            raise ValueError("Chargemol timeout; inspect workdir and log") from e
    if proc.returncode:
        raise ValueError(f"Chargemol exit code {proc.returncode}; see {work/'chargemol_stdout.log'}")
    if not (work/CHARGE_FILE).is_file() or not (work/BONDS_FILE).is_file():
        raise ValueError("Chargemol did not produce both charges and bond orders")
    return "computed"


def write_csv(path: Path, keys, records):
    with path.open("w", newline="", encoding="utf-8") as fh:
        out = csv.DictWriter(fh, fieldnames=keys)
        out.writeheader()
        out.writerows(records)


def main(argv=None):
    opt = cli(argv)
    root = opt.root.expanduser().resolve()
    if not root.is_dir() or opt.charge_tol <= 0 or opt.timeout < 0:
        print("invalid root, tolerance, or timeout", file=sys.stderr)
        return 2
    if opt.execute and opt.net_charge is None:
        print("ERROR: --execute requires explicit --net-charge", file=sys.stderr)
        return 2
    try:
        dirs = discover(root, opt.manifest, opt.collect_only)
    except ValueError as e:
        print("ERROR:", e, file=sys.stderr)
        return 2
    if not dirs:
        print("No VASP/Chargemol cases found", file=sys.stderr)
        return 2
    mode = "execute" if opt.execute else "collect-only" if opt.collect_only else "dry-run"
    print(f"DDEC6 batch: {len(dirs)} cases; mode={mode}")
    status, atoms, bonds, els, types = [], [], [], [], []
    errors = 0
    for run in dirs:
        case = "." if run == root else run.relative_to(root).as_posix()
        msg, state, total, outdir, n = "", "READY", None, "", 0
        try:
            symbols = source_structure(run)
            n = len(symbols)
            if opt.execute:
                msg = exec_chargemol(run, opt)
            if opt.execute or opt.collect_only:
                aa, bb, ee, tt, total, outdir = read_analysis(case, run, opt.net_charge, opt.charge_tol)
                atoms.extend(aa); bonds.extend(bb); els.extend(ee); types.extend(tt)
                state, msg = "OK", msg or "collected"
            else:
                missing = [x for x in INPUTS if not (run/x).is_file()]
                if missing:
                    raise ValueError("missing " + ", ".join(missing))
                state, msg = "READY", "complete input set; no program executed"
        except (ValueError, OSError, RuntimeError) as exc:
            state, msg = "ERROR", str(exc)
            errors += 1
        print(f"{state:6} {case}: {msg}")
        status.append({"case": case, "status": state, "detail": msg,
                       "n_atoms": n, "net_charge_e": opt.net_charge if opt.net_charge is not None else "",
                       "sum_ddec6_q_e": round(total, 8) if total is not None else "",
                       "charge_balance_error_e": round(total-opt.net_charge,8)
                       if total is not None and opt.net_charge is not None else "NOT_CHECKED",
                       "source": str(run), "chargemol_dir": outdir})
    if opt.execute or opt.collect_only:
        out = root / "postprocess_summary"
        out.mkdir(exist_ok=True)
        for name, keys, rows in [
            ("ddec6_cases.csv", HEADER, status),
            ("ddec6_atoms.csv", ATOMS, atoms),
            ("ddec6_bonds.csv", BONDS, bonds),
            ("ddec6_elements.csv", ELEMENTS, els),
            ("ddec6_bond_types.csv", BOND_TYPES, types),
        ]:
            write_csv(out/name, keys, rows)
        (out/"ddec6_summary.md").write_text(
            "# DDEC6 analysis — slide-ready summary\n\n"
            f"Cases: {len(dirs)}; passed: {len(dirs)-errors}; failed: {errors}.\n\n"
            "Reported q is **DDEC6 net atomic charge (e)**, positive = electron-deficient.\n"
            "SBO is the sum of bond orders per atom; pair BO is dimensionless.\n"
            "The pair table retains periodic cell translations. A given pair is counted\n"
            "once even if both reciprocal listings are present. The SBO includes\n"
            "small bonds below Chargemol's bond-print cutoff and therefore need not\n"
            "equal the sum of printed pair BOs.\n\n"
            f"Charge sum check: {'enabled against '+str(opt.net_charge)+' e' if opt.net_charge is not None else 'NOT CHECKED: --net-charge unspecified'}.\n\n"
            "## Files\n\n"
            "- ddec6_cases.csv — case status/errors and charge-sum check\n"
            "- ddec6_atoms.csv — full per-atom q and SBO\n"
            "- ddec6_bonds.csv — pairwise BO including periodic translations\n"
            "- ddec6_elements.csv — element-resolved means and ranges\n"
            "- ddec6_bond_types.csv — bond-type means and ranges\n\n"
            "## Scientific limits\n\n"
            "Do **not** interpret DDEC6 q as formal oxidation state or BO as\n"
            "integer Lewis bond order. Confirm DFT-method consistency, density\n"
            "quality, convergence, and the structure/site mapping before\n"
            "making comparative claims; numerical aggregation alone does not\n"
            "certify such comparability. Generated figures are descriptive,\n"
            "not evidence that trends are statistically independent.\n",
            encoding="utf-8")
        # Add genuinely human-readable numbers to the overview without replacing
        # full precision atom/pair CSVs. This is for screening/slide drafting only.
        with (out / "ddec6_summary.md").open("a", encoding="utf-8") as md:
            md.write("\n## Case QC (all cases)\n\n"
                     "| Case | Status | N atoms | Σq (e) | Charge-balance Δ (e) |\n"
                     "|---|---|---:|---:|---:|\n")
            for row in status:
                md.write(f"| {row['case']} | {row['status']} | {row['n_atoms']} | "
                         f"{row['sum_ddec6_q_e']} | {row['charge_balance_error_e']} |\n")
            md.write("\n## Element-resolved means / range\n\n"
                     "| Case | Element | N | Mean q (e) | q range (e) | Mean SBO | SBO range |\n"
                     "|---|---|---:|---:|---|---:|---|\n")
            for e in els:
                md.write(f"| {e['case']} | {e['element']} | {e['n_atoms']} | "
                         f"{e['mean_charge_e']:+.3f} | "
                         f"[{e['min_charge_e']:+.3f}, {e['max_charge_e']:+.3f}] | "
                         f"{e['mean_sbo']:.3f} | "
                         f"[{e['min_sbo']:.3f}, {e['max_sbo']:.3f}] |\n")
            md.write("\n## Periodic bond-type means / range\n\n"
                     "| Case | Bond type | Printed pairs | Mean BO | BO range |\n"
                     "|---|---|---:|---:|---|\n")
            for b in types:
                md.write(f"| {b['case']} | {b['element_pair']} | "
                         f"{b['n_periodic_bonds']} | {b['mean_bond_order']:.3f} | "
                         f"[{b['min_bond_order']:.3f}, {b['max_bond_order']:.3f}] |\n")
            md.write("\n## Suggested figure caption template\n\n"
                     "DDEC6 net atomic charge q or pairwise bond order for [model] "
                     "from Chargemol analysis of a [DFT functional, potential and "
                     "density settings] calculation. Bars denote arithmetic means "
                     "across atoms/printed bonds of the given type; error bars show "
                     "the minimum and maximum, **not** confidence intervals. "
                     "Specify the model composition, sample sizes, and any "
                     "comparison controls before presenting trends.\n")
        print(f"Outputs: {out}")
        if importlib.util.find_spec("matplotlib") is not None:
            plotter = Path(__file__).with_name("plot_ddec6.py")
            if plotter.is_file():
                env = os.environ.copy()
                env.setdefault("MPLBACKEND", "Agg")
                fig = subprocess.run([sys.executable, str(plotter), str(out)],
                                     text=True, capture_output=True, check=False, env=env)
                if fig.returncode:
                    print("WARNING: slide chart generation failed; CSVs retained:",
                          (fig.stderr or fig.stdout)[-600:])
                else:
                    print(fig.stdout.strip())
        else:
            print("NOTE: CSV and Markdown ready; install matplotlib to add PPT PNG/SVG charts.")

    print(f"Passed {len(dirs)-errors}/{len(dirs)}; failed {errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
