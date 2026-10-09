#!/usr/bin/env python3
"""Batch Bader/AIM charge analysis of existing VASP outputs (stdlib-only).

SAFE DEFAULT: inspect candidates without writing or running anything.
Use --execute to run chgsum.pl + bader in separate postprocess/bader dirs.
Use --collect-only to summarize already existing ACF.dat files.
No VASP jobs are submitted; source VASP files are never modified.

Net atomic charge q = ZVAL - N_Bader (positive means electron depletion).
"""
from __future__ import annotations

import argparse
import csv
import re
import shutil
import subprocess
import sys
from pathlib import Path


INPUTS = ("CHGCAR", "AECCAR0", "AECCAR2")
BADER_FILES = ("CHGCAR_sum", "ACF.dat", "BCF.dat", "AVF.dat")


def arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="One VASP run or the parent directory")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--execute", action="store_true", help="Run the Bader tools and write CSV")
    mode.add_argument("--collect-only", action="store_true", help="Parse existing ACF.dat; no external binaries")
    parser.add_argument("--manifest", type=Path, help="Optional newline-separated run directories, relative to root")
    parser.add_argument("--zval", default="", help="Explicit valence electrons, e.g. Na:9,P:5,S:6; no guessed defaults")
    parser.add_argument("--bader-bin", default="bader")
    parser.add_argument("--chgsum-bin", default="chgsum.pl")
    parser.add_argument("--force", action="store_true", help="Explicitly replace generated Bader outputs only")
    parser.add_argument("--timeout", type=int, default=0, help="Seconds per external tool (0 = no timeout)")
    return parser.parse_args(argv)


def discover(root: Path, manifest: Path | None, collect_only: bool) -> list[Path]:
    if manifest is not None:
        if not manifest.is_file():
            raise ValueError(f"manifest missing: {manifest}")
        runs = []
        for line in manifest.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            p = Path(line)
            p = (p if p.is_absolute() else root / p).resolve()
            if not p.is_dir() or not p.is_relative_to(root):
                raise ValueError(f"manifest path is not a directory inside root: {line}")
            runs.append(p)
        return sorted(set(runs))
    found = set()
    for name in (("CHGCAR", "ACF.dat") if collect_only else ("CHGCAR",)):
        candidates = [root / name, *root.rglob(name)]
        for p in candidates:
            if p.is_file() and not {"postprocess", ".git"}.intersection(p.relative_to(root).parts):
                found.add(p.parent.resolve())
    # Existing Bader output lives in run/postprocess/bader/ACF.dat.
    if collect_only:
        for p in root.rglob("postprocess/bader/ACF.dat"):
            if p.is_file() and p.parent.parent.parent.resolve().is_relative_to(root):
                found.add(p.parent.parent.parent.resolve())
    return sorted(found)


def parse_structure(folder: Path):
    for name in ("CONTCAR", "POSCAR"):
        p = folder / name
        if not p.is_file() or p.stat().st_size == 0:
            continue
        lines = p.read_text(errors="replace").splitlines()
        if len(lines) < 7:
            continue
        species = lines[5].split()
        if not species or all(s.isdigit() for s in species):
            raise ValueError("VASP4 POSCAR has no element symbols; provide a VASP5 structure")
        try:
            counts = [int(x) for x in lines[6].split()]
        except ValueError as exc:
            raise ValueError(f"invalid POSCAR species counts in {p}") from exc
        if len(species) != len(counts) or any(n <= 0 for n in counts):
            raise ValueError(f"species and counts mismatch in {p}")
        return species, counts
    raise ValueError("missing usable CONTCAR/POSCAR")


def parse_zval(folder: Path, species: list[str], supplied: str):
    override = {}
    for segment in supplied.split(","):
        if not segment.strip():
            continue
        if ":" not in segment:
            raise ValueError("bad --zval mapping; use e.g. Na:9,P:5,S:6")
        name, number = segment.split(":", 1)
        override[name.strip()] = float(number)
    p = folder / "POTCAR"
    values = []
    if p.is_file():
        # Read only ZVAL metadata; do not print or export copyrighted POTCAR contents.
        values = [float(s) for s in re.findall(r"ZVAL\s*=\s*([0-9]+(?:\.[0-9]+)?)", p.read_text(errors="ignore"))]
    valence = []
    for i, elem in enumerate(species):
        if elem in override:
            valence.append(override[elem])
        elif i < len(values):
            valence.append(values[i])
        else:
            raise ValueError(f"missing ZVAL for {elem}; provide POTCAR or --zval")
    return valence


def parse_acf(path: Path, expected: int) -> list[float]:
    if not path.is_file():
        raise ValueError(f"no ACF.dat: {path}")
    charge = []
    for line in path.read_text(errors="replace").splitlines():
        tokens = line.split()
        if len(tokens) < 7 or not tokens[0].isdigit():
            continue
        try:
            value = float(tokens[4])
        except ValueError as exc:
            raise ValueError(f"invalid ACF.dat charge row in {path}") from exc
        charge.append(value)
    if len(charge) != expected:
        raise ValueError(f"ACF.dat has {len(charge)} atoms; structure has {expected}")
    return charge


def run_tool(cmd: list[str], cwd: Path, logfile: Path, timeout: int):
    try:
        with logfile.open("w", encoding="utf-8") as log:
            log.write("# Command: " + " ".join(cmd) + "\\n")
            log.write("# Executable: " + str(shutil.which(cmd[0])) + "\\n")
            log.flush()
            result = subprocess.run(cmd, cwd=cwd, stdout=log, stderr=subprocess.STDOUT,
                                    timeout=timeout if timeout > 0 else None, check=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"tool timed out after {timeout}s: {cmd[0]}") from exc
    if result.returncode:
        raise RuntimeError(f"{cmd[0]} returned {result.returncode}; see {logfile}")


def prepare_and_run(folder: Path, opts):
    missing = [name for name in INPUTS if not (folder / name).is_file()]
    if missing:
        raise ValueError("missing " + ", ".join(missing) + "; VASP rerun may be needed")
    output = folder / "postprocess" / "bader"
    output.mkdir(parents=True, exist_ok=True)
    for name in (*INPUTS, "CONTCAR", "POSCAR", "POTCAR"):
        source = folder / name
        if not source.is_file():
            continue
        target = output / name
        if target.exists() or target.is_symlink():
            if not target.is_symlink() or target.resolve() != source.resolve():
                raise ValueError(f"conflicting output input link: {target}")
        else:
            target.symlink_to(source.resolve())

    acf = output / "ACF.dat"
    if acf.is_file() and not opts.force:
        latest_input = max((folder / n).stat().st_mtime for n in INPUTS)
        if acf.stat().st_mtime < latest_input:
            raise ValueError("existing ACF.dat is older than density files; use --force after review")
        return acf, "reused"

    if not shutil.which(opts.chgsum_bin) or not shutil.which(opts.bader_bin):
        raise ValueError("missing chgsum.pl or bader executable on PATH; no VASP files changed")
    if not opts.force and any((output / n).exists() for n in BADER_FILES):
        raise ValueError("incomplete existing Bader output; inspect it or use --force")
    run_tool([opts.chgsum_bin, "AECCAR0", "AECCAR2"],
             output, output / "chgsum.log", opts.timeout)
    if not (output / "CHGCAR_sum").is_file():
        raise RuntimeError("chgsum.pl did not produce CHGCAR_sum")
    run_tool([opts.bader_bin, "CHGCAR", "-ref", "CHGCAR_sum"],
             output, output / "bader.log", opts.timeout)
    if not acf.is_file():
        raise RuntimeError("bader did not produce ACF.dat")
    return acf, "calculated"


def atomic_rows(folder: Path, case: str, acf: Path, zval: str):
    species, counts = parse_structure(folder)
    valence = parse_zval(folder, species, zval)
    electrons = parse_acf(acf, sum(counts))
    expanded = [(name, v) for name, n, v in zip(species, counts, valence) for _ in range(n)]
    atoms = []
    by_elem: dict[str, list[float]] = {}
    for idx, ((elem, v), n) in enumerate(zip(expanded, electrons), 1):
        q = v - n
        atoms.append({"case": case, "atom_index": idx, "element": elem,
                      "bader_electrons": round(n, 7), "zval": v, "net_charge_e": round(q, 7),
                      "acf_path": str(acf)})
        by_elem.setdefault(elem, []).append(q)
    elems = []
    for elem, charges in by_elem.items():
        elems.append({"case": case, "element": elem, "count": len(charges),
                      "mean_q_e": round(sum(charges) / len(charges), 7),
                      "min_q_e": round(min(charges), 7), "max_q_e": round(max(charges), 7),
                      "spread_e": round(max(charges) - min(charges), 7),
                      "acf_path": str(acf)})
    return atoms, elems


def write_csv(path: Path, fields: list[str], rows: list[dict]):
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None):
    opts = arguments(argv)
    root = opts.root.expanduser().resolve()
    if not root.is_dir():
        print(f"ERROR: root does not exist: {root}", file=sys.stderr)
        return 2
    if opts.force and not opts.execute:
        print("ERROR: --force requires --execute", file=sys.stderr)
        return 2
    try:
        cases = discover(root, opts.manifest, opts.collect_only)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if not cases:
        print("No VASP candidate runs found.")
        return 2

    summary, all_atoms, all_elems = [], [], []
    failures = 0
    mode = "execute" if opts.execute else ("collect" if opts.collect_only else "dry-run")
    print(f"Bader batch: {len(cases)} cases, mode={mode}, root={root}")
    for folder in cases:
        case = "." if folder == root else folder.relative_to(root).as_posix()
        status, source, detail = "READY", "", ""
        try:
            if not (folder / "CHGCAR").is_file() and not opts.collect_only:
                raise ValueError("missing CHGCAR")
            # Validate the intended geometry before importing any charges.
            species, counts = parse_structure(folder)
            parse_zval(folder, species, opts.zval)
            if opts.execute:
                acf, action = prepare_and_run(folder, opts)
                atoms, elems = atomic_rows(folder, case, acf, opts.zval)
                all_atoms.extend(atoms)
                all_elems.extend(elems)
                status, source, detail = "OK", str(acf), action
            elif opts.collect_only:
                acf_options = [folder / "postprocess/bader/ACF.dat", folder / "ACF.dat"]
                acf = next((x for x in acf_options if x.is_file()), None)
                if acf is None:
                    raise ValueError("ACF.dat not found in run or postprocess/bader")
                atoms, elems = atomic_rows(folder, case, acf, opts.zval)
                all_atoms.extend(atoms)
                all_elems.extend(elems)
                status, source, detail = "OK", str(acf), "collected"
            else:
                missing = [p for p in INPUTS if not (folder / p).is_file()]
                if missing:
                    raise ValueError("missing " + ", ".join(missing))
                status, detail = "READY", "has inputs (no execution performed)"
        except (OSError, ValueError, RuntimeError) as exc:
            failures += 1
            status, detail = "ERROR", str(exc)
        print(f"{status:<6} {case}: {detail}")
        summary.append({"case": case, "status": status, "detail": detail,
                        "acf_path": source})

    if opts.execute or opts.collect_only:
        dest = root / "postprocess_summary"
        dest.mkdir(parents=True, exist_ok=True)
        write_csv(dest / "bader_cases.csv",
                  ["case", "status", "detail", "acf_path"], summary)
        write_csv(dest / "bader_atoms.csv",
                  ["case", "atom_index", "element", "bader_electrons", "zval",
                   "net_charge_e", "acf_path"], all_atoms)
        write_csv(dest / "bader_elements.csv",
                  ["case", "element", "count", "mean_q_e", "min_q_e",
                   "max_q_e", "spread_e", "acf_path"], all_elems)
        print(f"CSV: {dest} (cases, atoms, elements)")
    print(f"Completed {len(cases) - failures}/{len(cases)}; failed {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
