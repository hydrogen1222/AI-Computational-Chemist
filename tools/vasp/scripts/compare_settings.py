#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
"""Check that VASP runs were done under the same settings before their energies are combined.

Usage: compare_settings.py RUNDIR1 RUNDIR2 [RUNDIR3 ...] [--k-tol 0.05]

Stdlib only. Run it before subtracting or comparing total energies from different run
directories (formation energies, migration barriers, adsorption or substitution
energies, mixing energies). It reads the INCAR, POTCAR, KPOINTS and POSCAR actually
in each directory.

FAIL (exit 1), the energies must not be combined:
  - any tag in COMPARED_TAGS differs, including set in one run and absent in another;
  - the same element uses a different POTCAR (label or family) in two runs.
YELLOW (exit 3), allowed but must be stated in the ledger:
  - the coarsest k-point spacing differs by more than --k-tol (1/Angstrom, VASP
    KSPACING convention, default 0.05). Cells of different size often cannot have
    identical spacing; each run must still pass the project's KSPACING_MAX.
NELECT (charge state) is printed but not compared, since charged and neutral cells are
compared on purpose.

Exit code: 0 = same settings, 1 = different settings, 3 = yellow only, 2 = usage or read error.
"""
import math
import os
import sys

COMPARED_TAGS = [
    "ENCUT", "PREC", "GGA", "METAGGA", "XC", "LHFCALC", "HFSCREEN", "AEXX", "AGGAX",
    "AGGAC", "ALDAC", "IVDW", "LUSE_VDW", "LDAU", "LDAUTYPE", "LDAUL", "LDAUU", "LDAUJ",
    "LSORBIT", "ISMEAR", "SIGMA", "ISPIN", "LASPH", "LREAL", "ADDGRID",
]


def die(msg):
    print(f"compare_settings: {msg}", file=sys.stderr)
    sys.exit(2)


def parse_incar(path):
    tags = {}
    for line in open(path, errors="ignore"):
        line = line.split("#")[0].split("!")[0]
        for part in line.split(";"):
            if "=" in part:
                k, v = part.split("=", 1)
                tags[k.strip().upper()] = v.strip()
    return tags


def canon(v):
    if v is None:
        return "(not set)"
    t = v.strip().strip(".").upper()
    if t in ("TRUE", "T"):
        return "TRUE"
    if t in ("FALSE", "F"):
        return "FALSE"
    parts = v.split()
    try:
        return " ".join(repr(float(p)) for p in parts)
    except ValueError:
        return " ".join(parts).upper()


def det(m):
    return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def lattice(path):
    lines = [l.split() for l in open(path, errors="ignore")]
    scale = float(lines[1][0])
    raw = [[float(x) for x in lines[i][:3]] for i in (2, 3, 4)]
    if scale < 0:
        scale = (abs(scale) / abs(det(raw))) ** (1 / 3)
    return [[x * scale for x in row] for row in raw]


def coarsest_spacing(rundir, incar):
    kp = os.path.join(rundir, "KPOINTS")
    if not os.path.isfile(kp):
        if "KSPACING" in incar:
            return float(incar["KSPACING"].split()[0]), f"KSPACING {incar['KSPACING']}"
        return None, "no KPOINTS"
    lines = [l.strip() for l in open(kp, errors="ignore") if l.strip()]
    try:
        if int(float(lines[1].split()[0])) != 0 or lines[2][:1].lower() not in "gm":
            return None, "not an automatic mesh"
        mesh = [int(float(x)) for x in lines[3].split()[:3]]
    except (IndexError, ValueError):
        return None, "unreadable KPOINTS"
    pos = os.path.join(rundir, "POSCAR")
    if not os.path.isfile(pos):
        return None, "no POSCAR"
    lat = lattice(pos)
    v = abs(det(lat))
    sp = []
    for i in range(3):
        c = cross(lat[(i + 1) % 3], lat[(i + 2) % 3])
        sp.append(2 * math.pi * math.sqrt(sum(x * x for x in c)) / v / mesh[i])
    return max(sp), "mesh " + "x".join(map(str, mesh))


def potcars(rundir):
    out = {}
    path = os.path.join(rundir, "POTCAR")
    if not os.path.isfile(path):
        return None
    for line in open(path, errors="ignore"):
        if "TITEL" in line:
            parts = line.split("=", 1)[1].split()
            if len(parts) >= 2:
                out[parts[1].split("_")[0]] = f"{parts[0]} {parts[1]}"
    return out


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if args else 2)
    ktol, dirs, i = 0.05, [], 0
    while i < len(args):
        if args[i] == "--k-tol" and i + 1 < len(args):
            ktol = float(args[i + 1])
            i += 2
        else:
            dirs.append(args[i])
            i += 1
    if len(dirs) < 2:
        die("give at least two run directories")

    runs = []
    for d in dirs:
        inc = os.path.join(d, "INCAR")
        if not os.path.isfile(inc):
            die(f"no INCAR in {d}")
        incar = parse_incar(inc)
        runs.append({"dir": d, "incar": incar, "potcar": potcars(d),
                     "k": coarsest_spacing(d, incar)})

    fails, yellows = [], []
    width = max(len(d) for d in dirs)
    print("Runs compared:")
    for n, r in enumerate(runs, 1):
        k, ktxt = r["k"]
        ktxt = f"{k:.3f} 1/A ({ktxt})" if k is not None else ktxt
        nel = r["incar"].get("NELECT", "default")
        print(f"  [{n}] {r['dir']:<{width}}  coarsest k spacing {ktxt}; NELECT {nel}")

    for tag in COMPARED_TAGS:
        vals = [canon(r["incar"].get(tag)) for r in runs]
        if len(set(vals)) > 1:
            shown = ", ".join(f"[{n}] {r['incar'].get(tag, '(not set)')}" for n, r in enumerate(runs, 1))
            fails.append(f"{tag} differs: {shown}")

    if any(r["potcar"] is None for r in runs):
        missing = [r["dir"] for r in runs if r["potcar"] is None]
        fails.append(f"no POTCAR in {', '.join(missing)}; cannot confirm the same POTCARs")
    else:
        elements = sorted(set().union(*(r["potcar"] for r in runs)))
        for el in elements:
            labels = {r["potcar"][el] for r in runs if el in r["potcar"]}
            if len(labels) > 1:
                fails.append(f"POTCAR for {el} differs: {', '.join(sorted(labels))}")

    ks = [r["k"][0] for r in runs if r["k"][0] is not None]
    if ks and max(ks) - min(ks) > ktol:
        yellows.append(f"coarsest k spacing ranges {min(ks):.3f} to {max(ks):.3f} 1/A "
                       f"(tolerance {ktol}); state it in the ledger")
    if len(ks) < len(runs):
        yellows.append("k spacing could not be read for every run (band path or missing file)")

    if fails:
        print("RESULT: DIFFERENT SETTINGS - do not combine these energies")
        for f in fails:
            print(f"  FAIL: {f}")
        for y in yellows:
            print(f"  YELLOW: {y}")
        sys.exit(1)
    if yellows:
        print("RESULT: YELLOW - same physics settings; note the following in the ledger")
        for y in yellows:
            print(f"  YELLOW: {y}")
        sys.exit(3)
    print("RESULT: OK - same settings")
    sys.exit(0)


if __name__ == "__main__":
    main()
