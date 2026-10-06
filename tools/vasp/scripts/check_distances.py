#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
"""Shortest distance for every element pair in a POSCAR/CONTCAR, with red and yellow lines.

Usage: check_distances.py STRUCTURE [--reference BULK_CONTCAR] [--red-scale 0.7]
                          [--yellow-shrink 0.15] [--lattice-ref "a b c"] [--lattice-tol 3]

Stdlib only. Periodic images are included, so small cells are handled correctly.
STRUCTURE must be VASP 5 format (element names on line 6).

Red line (stop): a pair closer than red-scale x the sum of the two covalent radii
  (Cordero et al., Dalton Trans. 2008, 2832; the table ASE uses). Default 0.7.
  Example: Li-S, 0.7 x (1.28 + 1.05) = 1.63 Angstrom.
Yellow line (explain before going on): with --reference, an element pair whose
  shortest distance is more than yellow-shrink (default 15 %) below the shortest
  distance of the same pair in the reference structure, normally the project's
  relaxed bulk. This catches changed chemistry, such as two S atoms moving to
  bonding distance, which the red line lets through. Pairs absent from the
  reference get the red check only, and the output says so.
Lattice (yellow): with --lattice-ref, each cell length that differs from the given
  value by more than lattice-tol percent (default 3). Give the expected lengths of
  this cell (for a supercell, the supercell lengths).

Run it on the starting POSCAR before submitting and on the CONTCAR after a relaxation.

Exit code: 0 = clean, 1 = red line crossed (stop), 3 = yellow only (explain in the
ledger before using the result), 2 = usage or read error.
"""
import itertools
import math
import sys

# Cordero et al. 2008 covalent radii in Angstrom (low-spin values for Mn, Fe, Co).
COVALENT_RADII = {
    "H": 0.31, "He": 0.28, "Li": 1.28, "Be": 0.96, "B": 0.84, "C": 0.76, "N": 0.71,
    "O": 0.66, "F": 0.57, "Ne": 0.58, "Na": 1.66, "Mg": 1.41, "Al": 1.21, "Si": 1.11,
    "P": 1.07, "S": 1.05, "Cl": 1.02, "Ar": 1.06, "K": 2.03, "Ca": 1.76, "Sc": 1.70,
    "Ti": 1.60, "V": 1.53, "Cr": 1.39, "Mn": 1.39, "Fe": 1.32, "Co": 1.26, "Ni": 1.24,
    "Cu": 1.32, "Zn": 1.22, "Ga": 1.22, "Ge": 1.20, "As": 1.19, "Se": 1.20, "Br": 1.20,
    "Kr": 1.16, "Rb": 2.20, "Sr": 1.95, "Y": 1.90, "Zr": 1.75, "Nb": 1.64, "Mo": 1.54,
    "Tc": 1.47, "Ru": 1.46, "Rh": 1.42, "Pd": 1.39, "Ag": 1.45, "Cd": 1.44, "In": 1.42,
    "Sn": 1.39, "Sb": 1.39, "Te": 1.38, "I": 1.39, "Xe": 1.40, "Cs": 2.44, "Ba": 2.15,
    "La": 2.07, "Ce": 2.04, "Pr": 2.03, "Nd": 2.01, "Pm": 1.99, "Sm": 1.98, "Eu": 1.98,
    "Gd": 1.96, "Tb": 1.94, "Dy": 1.92, "Ho": 1.92, "Er": 1.89, "Tm": 1.90, "Yb": 1.87,
    "Lu": 1.87, "Hf": 1.75, "Ta": 1.70, "W": 1.62, "Re": 1.51, "Os": 1.44, "Ir": 1.41,
    "Pt": 1.36, "Au": 1.36, "Hg": 1.32, "Tl": 1.45, "Pb": 1.46, "Bi": 1.48, "Po": 1.40,
    "At": 1.50, "Rn": 1.50, "Fr": 2.60, "Ra": 2.21, "Ac": 2.15, "Th": 2.06, "Pa": 2.00,
    "U": 1.96, "Np": 1.90, "Pu": 1.87, "Am": 1.80, "Cm": 1.69,
}
SEARCH_RADIUS = 6.0  # Angstrom; pairs with no contact inside this are reported as "> 6"


def die(msg):
    print(f"check_distances: {msg}", file=sys.stderr)
    sys.exit(2)


def det(m):
    return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def norm(v):
    return math.sqrt(sum(x * x for x in v))


def read_poscar(path):
    try:
        lines = [l.split() for l in open(path, errors="ignore")]
    except OSError as exc:
        die(f"cannot read {path}: {exc}")
    try:
        scale = float(lines[1][0])
        raw = [[float(x) for x in lines[i][:3]] for i in (2, 3, 4)]
        if scale < 0:
            scale = (abs(scale) / abs(det(raw))) ** (1 / 3)
        lat = [[x * scale for x in row] for row in raw]
        species = lines[5]
        if not species or species[0][0].isdigit():
            die(f"{path}: no element line (line 6); use VASP 5 format")
        counts = [int(x) for x in lines[6]]
        k = 7
        if lines[k][0][0] in "sS":
            k += 1
        direct = lines[k][0][0] in "dD"
        n = sum(counts)
        coords = [[float(x) for x in lines[k + 1 + i][:3]] for i in range(n)]
    except (IndexError, ValueError):
        die(f"{path}: not a readable VASP 5 POSCAR/CONTCAR")
    labels = [s.split("_")[0].split("/")[0] for s, c in zip(species, counts) for _ in range(c)]
    if not direct:  # Cartesian -> fractional
        inv = invert(lat)
        coords = [[sum(c[j] * scale * inv[j][i] for j in range(3)) for i in range(3)]
                  for c in coords]
    return lat, labels, coords


def invert(m):
    d = det(m)
    return [[(m[(j + 1) % 3][(i + 1) % 3] * m[(j + 2) % 3][(i + 2) % 3]
              - m[(j + 1) % 3][(i + 2) % 3] * m[(j + 2) % 3][(i + 1) % 3]) / d
             for j in range(3)] for i in range(3)]


def pair_minima(lat, labels, frac):
    vol = abs(det(lat))
    # number of images needed along each axis so that SEARCH_RADIUS is covered
    reps = []
    for i in range(3):
        height = vol / norm(cross(lat[(i + 1) % 3], lat[(i + 2) % 3]))
        reps.append(int(math.ceil(SEARCH_RADIUS / height)))
    images = [img for img in itertools.product(*(range(-r, r + 1) for r in reps))]
    best = {}
    n = len(labels)
    for a in range(n):
        for b in range(a, n):
            d0 = [frac[b][k] - frac[a][k] for k in range(3)]
            d0 = [x - round(x) for x in d0]
            for img in images:
                if a == b and img == (0, 0, 0):
                    continue
                f = [d0[k] + img[k] for k in range(3)]
                cart = [sum(f[k] * lat[k][j] for k in range(3)) for j in range(3)]
                d = norm(cart)
                if d > SEARCH_RADIUS:
                    continue
                key = tuple(sorted((labels[a], labels[b])))
                if d < best.get(key, (math.inf,))[0]:
                    best[key] = (d, a + 1, b + 1)
    return best


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if args else 2)
    opts = {"--reference": None, "--red-scale": "0.7", "--yellow-shrink": "0.15",
            "--lattice-ref": None, "--lattice-tol": "3"}
    path, i = None, 0
    while i < len(args):
        if args[i] in opts and i + 1 < len(args):
            opts[args[i]] = args[i + 1]
            i += 2
        elif path is None:
            path = args[i]
            i += 1
        else:
            die(f"unexpected argument {args[i]}")
    if path is None:
        die("no structure given")
    red_scale = float(opts["--red-scale"])
    shrink = float(opts["--yellow-shrink"])

    lat, labels, frac = read_poscar(path)
    mins = pair_minima(lat, labels, frac)
    ref = None
    if opts["--reference"]:
        rlat, rlabels, rfrac = read_poscar(opts["--reference"])
        ref = pair_minima(rlat, rlabels, rfrac)

    reds, yellows = [], []
    print(f"Structure: {path}  ({len(labels)} atoms)")
    if ref is not None:
        print(f"Reference: {opts['--reference']}")
    print(f"{'pair':<8} {'shortest (A)':>12} {'atoms':>10} {'red line':>9} {'reference':>10}  verdict")
    elements = sorted(set(labels))
    for key in sorted(itertools.combinations_with_replacement(elements, 2)):
        name = f"{key[0]}-{key[1]}"
        if key[0] not in COVALENT_RADII or key[1] not in COVALENT_RADII:
            die(f"no covalent radius for {name}")
        red = red_scale * (COVALENT_RADII[key[0]] + COVALENT_RADII[key[1]])
        if key not in mins:
            ref_txt = f"{ref[key][0]:.3f}" if ref and key in ref else "-"
            print(f"{name:<8} {'> 6':>12} {'':>10} {red:9.3f} {ref_txt:>10}  ok")
            continue
        d, a, b = mins[key]
        verdict = "ok"
        ref_txt = "-"
        if d < red:
            verdict = "RED: too close, stop"
            reds.append(f"{name} {d:.3f} A (atoms {a}, {b}) < red line {red:.3f} A")
        if ref is not None:
            if key in ref:
                ref_txt = f"{ref[key][0]:.3f}"
                if d < (1 - shrink) * ref[key][0] and verdict == "ok":
                    verdict = f"YELLOW: {100 * (1 - d / ref[key][0]):.0f}% shorter than reference"
                    yellows.append(f"{name} {d:.3f} A (atoms {a}, {b}) vs {ref[key][0]:.3f} A in the reference")
            else:
                ref_txt = "none"
                if verdict == "ok":
                    verdict = "ok (no reference pair; red check only)"
        print(f"{name:<8} {d:12.3f} {f'{a},{b}':>10} {red:9.3f} {ref_txt:>10}  {verdict}")

    if opts["--lattice-ref"]:
        want = [float(x) for x in opts["--lattice-ref"].replace(",", " ").split()]
        if len(want) != 3:
            die("--lattice-ref needs three lengths: \"a b c\"")
        tol = float(opts["--lattice-tol"])
        have = [norm(v) for v in lat]
        for axis, h, w in zip("abc", have, want):
            dev = 100 * (h - w) / w
            flag = abs(dev) > tol
            print(f"lattice {axis}: {h:.4f} A vs {w:.4f} A ({dev:+.2f}%)" + ("  YELLOW" if flag else ""))
            if flag:
                yellows.append(f"lattice {axis} {h:.4f} A differs from {w:.4f} A by {dev:+.2f}% (limit {tol}%)")

    if reds:
        print("RESULT: RED - atoms too close; stop and wait for the user")
        for r in reds:
            print(f"  RED: {r}")
        sys.exit(1)
    if yellows:
        print("RESULT: YELLOW - explain these in the ledger before using the structure")
        for y in yellows:
            print(f"  YELLOW: {y}")
        sys.exit(3)
    print("RESULT: OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
