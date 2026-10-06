#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
"""Pre-submission check of an ORCA 6 input file (stdlib only).

Usage: check_orca_input.py JOB.inp [--mem-gb FREE_MEMORY_GB]

FAIL (exit 1), do not submit:
  - multiplicity parity does not match the electron count, or multiplicity > electrons + 1
  - a dispersion keyword ORCA does not have (D5, ...), two dispersion keywords, or a
    dispersion keyword on a functional that already contains dispersion (-V, -3c)
  - the same simple-input keyword written twice (ORCA stops on duplicates)
  - a PALn keyword ORCA does not accept (only PAL2-PAL8, PAL16, PAL32, PAL64)
  - a % block without "end", or an "* xyz" block without its closing "*"
  - unknown element symbol in the coordinates
  - with --mem-gb: %maxcore x nprocs above 75 % of that memory
WARN (exit 3 if nothing failed):
  - NoAutoStart missing (an old .gbw with the same base name would be read)
  - no comment saying where charge and multiplicity come from
  - no %maxcore or no core count given

The script does not know every ORCA keyword. A misspelled method or basis is caught by
ORCA itself within a second (INPUT ERROR); read the output right after starting a job.

Exit code: 0 = OK, 1 = FAIL, 3 = warnings only, 2 = usage or read error.
"""
import os
import re
import sys

SYMBOLS = (
    "H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge "
    "As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm "
    "Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U "
    "Np Pu Am Cm Bk Cf Es Fm Md No Lr"
).split()
Z = {s.upper(): i + 1 for i, s in enumerate(SYMBOLS)}

VALID_PAL = {"PAL2", "PAL3", "PAL4", "PAL5", "PAL6", "PAL7", "PAL8", "PAL16", "PAL32", "PAL64"}
DISPERSION = {"D2", "D3", "D3BJ", "D3ZERO", "D30", "D4", "NL", "SCNL"}
# Blocks that are a single "%keyword value" line and need no "end".
ONE_LINE_BLOCKS = {"MAXCORE", "MOINP", "BASE", "COORDS_FILE"}


def die(msg):
    print(f"check_orca_input: {msg}", file=sys.stderr)
    sys.exit(2)


def element_of(label):
    """'C', 'C1', 'Fe(1)', 'H:' (ghost), 'Cl>' -> element symbol upper-case, or None."""
    m = re.match(r"([A-Za-z]{1,2})", label)
    if not m:
        return None
    sym = m.group(1).upper()
    if sym in Z:
        return sym
    if sym[:1] in Z:
        return sym[:1]
    return None


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if args else 2)
    path, mem_gb, i = None, None, 0
    while i < len(args):
        if args[i] == "--mem-gb" and i + 1 < len(args):
            mem_gb = float(args[i + 1])
            i += 2
        elif path is None:
            path = args[i]
            i += 1
        else:
            die(f"unexpected argument {args[i]}")
    if path is None or not os.path.isfile(path):
        die(f"input file not found: {path}")

    raw_lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    fails, warns, notes = [], [], []
    comments = " ".join(l.split("#", 1)[1] for l in raw_lines if "#" in l).lower()
    lines = [l.split("#", 1)[0].rstrip() for l in raw_lines]

    for n, l in enumerate(raw_lines, 1):
        if any(ord(c) > 127 for c in l.split("#", 1)[0]):
            fails.append(f"line {n}: non-ASCII character outside a comment (ORCA rejects it)")

    keywords = []
    for l in lines:
        s = l.strip()
        if s.startswith("!"):
            keywords.extend(s[1:].split())
    upper = [k.upper() for k in keywords]
    seen = set()
    for k in upper:
        if k in seen:
            fails.append(f"keyword {k} appears twice in the simple input (ORCA stops on duplicates)")
        seen.add(k)

    for k in upper:
        if re.fullmatch(r"D\d+[A-Z0-9]*", k) and k not in DISPERSION | {"D3TZ"}:
            fails.append(f"dispersion keyword {k} does not exist in ORCA 6 "
                         "(use D3, D3BJ, D3ZERO or D4)")
    disp = [k for k in upper if k in DISPERSION]
    if len(disp) > 1:
        fails.append(f"more than one dispersion keyword: {' '.join(disp)}")
    has_builtin = [k for k in upper if k.endswith("-V") or k.endswith("-3C")]
    if disp and has_builtin:
        fails.append(f"{has_builtin[0]} already contains dispersion; remove {' '.join(disp)}")
    for k in upper:
        if re.fullmatch(r"PAL\d+", k) and k not in VALID_PAL:
            fails.append(f"{k} is not accepted; use %pal nprocs N end for this core count")
    if "NOAUTOSTART" not in upper:
        warns.append("NoAutoStart not set: an existing .gbw with the same base name would be "
                     "read as the starting guess")

    # % blocks: each needs an "end" before the next !, % or * line
    nprocs, maxcore = None, None
    for kw in upper:
        m = re.fullmatch(r"PAL(\d+)", kw)
        if m:
            nprocs = int(m.group(1))
    n = 0
    while n < len(lines):
        s = lines[n].strip()
        if s.startswith("%"):
            m = re.match(r"%\s*(\w+)(.*)", s)
            if not m:
                fails.append(f"line {n + 1}: cannot read block name")
                n += 1
                continue
            name, rest = m.group(1).upper(), m.group(2)
            if name == "MAXCORE":
                try:
                    maxcore = float(rest.split()[0])
                except (IndexError, ValueError):
                    fails.append(f"line {n + 1}: %maxcore needs a number (MB per core)")
            if name == "PAL":
                mp = re.search(r"nprocs\s+(\d+)", " ".join(lines[n:n + 5]), re.I)
                if mp:
                    nprocs = int(mp.group(1))
            if name in ONE_LINE_BLOCKS:
                n += 1
                continue
            closed = re.search(r"\bend\s*$", rest, re.I) is not None
            j = n + 1
            while not closed and j < len(lines):
                t = lines[j].strip()
                if t[:1] in ("!", "%", "*"):
                    break
                if re.search(r"\bend\s*$", t, re.I):
                    closed = True
                j += 1
            if not closed:
                fails.append(f"line {n + 1}: block %{m.group(1)} has no 'end'")
            n = j if j > n + 1 else n + 1
            continue
        n += 1

    # coordinates
    charge = mult = None
    elements = []
    for n, l in enumerate(lines):
        s = l.strip()
        m = re.match(r"\*\s*(xyzfile|xyz|int|gzmt|pdbfile|gzmtfile)\s+(-?\d+)\s+(\d+)\s*(\S*)", s, re.I)
        if not m:
            continue
        ctype, charge, mult, fname = m.group(1).lower(), int(m.group(2)), int(m.group(3)), m.group(4)
        if ctype == "xyz":
            j = n + 1
            while j < len(lines) and lines[j].strip() != "*":
                parts = lines[j].split()
                if parts:
                    el = element_of(parts[0])
                    if el is None:
                        fails.append(f"line {j + 1}: unknown element '{parts[0]}'")
                    else:
                        elements.append(el)
                j += 1
            if j >= len(lines):
                fails.append("coordinate block '* xyz' has no closing '*'")
        elif ctype == "xyzfile":
            fpath = os.path.join(os.path.dirname(os.path.abspath(path)), fname)
            if not os.path.isfile(fpath):
                notes.append(f"{fname} not found next to the input; electron count not checked")
            else:
                xl = open(fpath, errors="replace").read().splitlines()
                for row in xl[2:]:
                    parts = row.split()
                    if parts:
                        el = element_of(parts[0])
                        if el is None:
                            fails.append(f"{fname}: unknown element '{parts[0]}'")
                        else:
                            elements.append(el)
        else:
            notes.append(f"'* {ctype}' coordinates: electron count not checked")
        break
    if charge is None:
        fails.append("no coordinate line '* xyz <charge> <mult>' (or xyzfile) found")
    elif elements:
        electrons = sum(Z[e] for e in elements) - charge
        counts = {}
        for e in elements:
            counts[e] = counts.get(e, 0) + 1
        formula = " ".join(f"{e.capitalize()}{c}" for e, c in sorted(counts.items()))
        notes.append(f"{len(elements)} atoms ({formula}), charge {charge}, "
                     f"multiplicity {mult}, {electrons} electrons")
        if electrons <= 0:
            fails.append(f"charge {charge} leaves {electrons} electrons")
        elif (electrons % 2 == 0) != (mult % 2 == 1):
            fails.append(f"{electrons} electrons cannot have multiplicity {mult} "
                         f"({'even' if electrons % 2 == 0 else 'odd'} electron count needs an "
                         f"{'odd' if electrons % 2 == 0 else 'even'} multiplicity)")
        elif mult - 1 > electrons:
            fails.append(f"multiplicity {mult} needs more unpaired electrons than the {electrons} present")
    if charge is not None and not re.search(r"charge|multiplicity|mult|电荷|自旋多重度|多重度", comments):
        warns.append("no comment says where charge and multiplicity come from "
                     "(e.g. '# charge 0, doublet: one unpaired electron on N')")

    if maxcore is None:
        warns.append("no %maxcore (MB per core) set; ORCA uses its small default")
    if nprocs is None:
        warns.append("no core count (%pal nprocs N end); the job runs on one core")
    if mem_gb is not None and maxcore is not None:
        total = maxcore * (nprocs or 1)
        limit = 0.75 * mem_gb * 1024
        line = f"%maxcore {maxcore:.0f} MB x {nprocs or 1} cores = {total / 1024:.1f} GB"
        if total > limit:
            fails.append(f"{line} > 75 % of {mem_gb:g} GB ({limit / 1024:.1f} GB)")
        else:
            notes.append(f"{line} (limit {limit / 1024:.1f} GB)")

    print(f"Input: {path}")
    print(f"Keywords: {' '.join(keywords)}")
    for x in notes:
        print(f"  note: {x}")
    for x in fails:
        print(f"  FAIL: {x}")
    for x in warns:
        print(f"  WARN: {x}")
    if fails:
        print("RESULT: FAIL - fix the input before submitting")
        sys.exit(1)
    if warns:
        print("RESULT: OK with warnings")
        sys.exit(3)
    print("RESULT: OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
