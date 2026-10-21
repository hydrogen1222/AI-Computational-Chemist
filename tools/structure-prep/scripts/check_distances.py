#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
"""Shortest distance for every element pair in a POSCAR/CONTCAR, with red and yellow lines.

Usage: check_distances.py STRUCTURE [--reference BULK_CONTCAR] [--red-scale 0.7]
                          [--yellow-shrink 0.15] [--lattice-ref "a b c"] [--lattice-tol 3]

Stdlib only. Periodic images are included, so small cells are handled correctly.
STRUCTURE must be VASP 5 format (element names on line 6).

Red line (stop): a pair closer than red-scale x the sum of the two Pyykko single-bond
  covalent radii (the same table audit_structure.py uses). Default 0.7.
  Example: Li-S, 0.7 x (1.33 + 1.03) = 1.65 Angstrom.
Yellow line (explain before going on): with --reference, an element pair whose
  shortest distance is more than yellow-shrink (default 15 %) below the shortest
  distance of the same pair in the reference structure, normally the project's
  relaxed bulk. This catches changed chemistry, such as two S atoms moving to
  bonding distance, which the red line lets through. Pairs absent from the
  reference get the red check only, and the output says so.
Lattice (yellow): with --lattice-ref, each cell length that differs from the given
  value by more than lattice-tol percent (default 3). Give the expected lengths of
  this cell (for a supercell, the supercell lengths).

Run it on any POSCAR before submitting and on the CONTCAR after a relaxation. It needs
no pymatgen, so it also works on a cluster login node. For a freshly built model use
audit_structure.py (stricter 0.95 build-time threshold plus vacuum/slab checks); see
tools/structure-prep/references/validation.md for why the two thresholds differ.

Exit code: 0 = clean, 1 = red line crossed (stop), 3 = yellow only (explain in the
model notes before using the result), 2 = usage or read error.
"""
import itertools
import math
import sys

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from covalent_radii import PYYKKO_SINGLE_COVALENT_RADII_A as COVALENT_RADII  # noqa: E402

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
        print("RESULT: YELLOW - explain these in the model notes before using the structure")
        for y in yellows:
            print(f"  YELLOW: {y}")
        sys.exit(3)
    print("RESULT: OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
