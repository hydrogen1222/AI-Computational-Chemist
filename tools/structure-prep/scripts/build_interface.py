#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pymatgen"]
# ///
"""Build coherent film|substrate interface candidates by ZSL lattice matching.

Usage:
    uv run build_interface.py SUBSTRATE FILM --sub-miller 0 0 1 --film-miller 1 1 0
        [--max-area 300] [--max-length-tol 0.03] [--max-angle-tol 0.01]
        [--max-area-ratio-tol 0.09] [--show 15]
    # after reading the listing:
    uv run build_interface.py SUBSTRATE FILM --sub-miller 0 0 1 --film-miller 1 1 0
        --termination 0 --match 2 [--match 5] [--sub-layers 4] [--film-layers 4]
        [--gap 2.0] [--vacuum 15] [--max-atoms 400] --out iface/

Without --termination/--match it only LISTS the terminations and lattice matches
(area, strain, supercell multiplicities) and writes nothing: which termination pair
and which match to use are scientific choices, not list positions.

The FILM is strained onto the SUBSTRATE (pymatgen CoherentInterfaceBuilder); the
substrate keeps its lattice. Put the softer phase (e.g. Li or Na metal) as the film
and report its strain. Layers are counted in unit planes of each Miller index.
--vacuum 0 gives a periodic sandwich with two interfaces; > 0 gives one interface with
vacuum over the film.

Each written candidate gets iface/<label>/POSCAR (species grouped) and one
iface/interface_summary.json with sources, Miller indices, termination labels, match
vectors, strain, area, atom counts per side, gap, vacuum and ZSL tolerances. Run
audit_structure.py on every POSCAR before engine handoff.

Exit: 0 ok, 1 nothing matched / too large, 2 usage or read error.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys


def load(path: str):
    from pymatgen.core import Structure
    try:
        return Structure.from_file(path)
    except Exception as exc:  # noqa: BLE001 - report the reader's message
        raise SystemExit(f"cannot read {path}: {exc}") from exc


def det2(m) -> int:
    return int(round(abs(m[0][0] * m[1][1] - m[0][1] * m[1][0])))


def match_rows(builder):
    import numpy as np
    from pymatgen.analysis.elasticity.strain import Deformation
    rows = []
    for idx, m in enumerate(builder.zsl_matches):
        a, b = np.asarray(m.substrate_sl_vectors[0]), np.asarray(m.substrate_sl_vectors[1])
        area = float(np.linalg.norm(np.cross(a, b)))
        strain = Deformation(m.match_transformation).green_lagrange_strain
        rows.append({
            "match": idx,
            "area_A2": round(area, 2),
            "von_mises_strain": round(float(strain.von_mises_strain), 5),
            "max_abs_inplane_strain": round(float(np.max(np.abs(np.asarray(strain)[:2, :2]))), 5),
            "substrate_multiplicity": det2(m.substrate_transformation),
            "film_multiplicity": det2(m.film_transformation),
            "substrate_sl_vectors": [list(map(float, v)) for v in m.substrate_sl_vectors],
            "film_sl_vectors": [list(map(float, v)) for v in m.film_sl_vectors],
        })
    return sorted(rows, key=lambda r: (r["area_A2"], r["von_mises_strain"]))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("substrate")
    p.add_argument("film")
    p.add_argument("--sub-miller", nargs=3, type=int, required=True, metavar=("H", "K", "L"))
    p.add_argument("--film-miller", nargs=3, type=int, required=True, metavar=("H", "K", "L"))
    p.add_argument("--max-area", type=float, default=300.0, help="largest interface area searched, A^2")
    p.add_argument("--max-length-tol", type=float, default=0.03)
    p.add_argument("--max-angle-tol", type=float, default=0.01)
    p.add_argument("--max-area-ratio-tol", type=float, default=0.09)
    p.add_argument("--termination-ftol", type=float, default=0.25)
    p.add_argument("--show", type=int, default=15, help="matches to list")
    p.add_argument("--termination", type=int, help="index from the listing")
    p.add_argument("--match", type=int, action="append", help="match index from the listing (repeat)")
    p.add_argument("--sub-layers", type=int, default=4)
    p.add_argument("--film-layers", type=int, default=4)
    p.add_argument("--gap", type=float, default=2.0, help="initial film-substrate gap, A")
    p.add_argument("--vacuum", type=float, default=15.0, help="vacuum over the film, A (0 = periodic sandwich)")
    p.add_argument("--max-atoms", type=int, default=400)
    p.add_argument("--out", default="interfaces")
    a = p.parse_args(argv)

    try:
        import pymatgen
        from pymatgen.analysis.interfaces.coherent_interfaces import CoherentInterfaceBuilder
        from pymatgen.analysis.interfaces.zsl import ZSLGenerator
        from pymatgen.io.vasp import Poscar
    except ImportError as exc:
        raise SystemExit(f"pymatgen is required (run via `uv run`): {exc}") from exc

    sub, film = load(a.substrate), load(a.film)
    zsl = ZSLGenerator(max_area_ratio_tol=a.max_area_ratio_tol, max_area=a.max_area,
                       max_length_tol=a.max_length_tol, max_angle_tol=a.max_angle_tol,
                       bidirectional=True)
    builder = CoherentInterfaceBuilder(substrate_structure=sub, film_structure=film,
                                       film_miller=tuple(a.film_miller),
                                       substrate_miller=tuple(a.sub_miller),
                                       zslgen=zsl, termination_ftol=a.termination_ftol,
                                       label_index=True)
    terms = list(builder.terminations)
    rows = match_rows(builder)

    print(f"substrate {sub.composition.reduced_formula} {tuple(a.sub_miller)} | "
          f"film {film.composition.reduced_formula} {tuple(a.film_miller)}  "
          f"(film is strained onto the substrate)")
    print("terminations (film, substrate):")
    for i, t in enumerate(terms):
        print(f"  [{i}] {t[0]}  |  {t[1]}")
    if not rows:
        print("no lattice matches: raise --max-area or the tolerances, or reconsider the Miller indices")
        return 1
    print(f"lattice matches ({len(rows)} found, smallest area first):")
    print(f"  {'match':>5} {'area A^2':>9} {'vonMises':>9} {'max|e|':>7} {'n_sub':>5} {'n_film':>6}")
    for r in rows[:a.show]:
        print(f"  {r['match']:>5} {r['area_A2']:>9.1f} {r['von_mises_strain']:>9.4f} "
              f"{r['max_abs_inplane_strain']:>7.4f} {r['substrate_multiplicity']:>5} {r['film_multiplicity']:>6}")

    if a.termination is None or not a.match:
        print("listing only - choose a termination pair and match(es), then rerun with "
              "--termination I --match J [--match K]")
        return 0
    if not 0 <= a.termination < len(terms):
        raise SystemExit(f"--termination must be 0..{len(terms) - 1}")
    known = {r["match"]: r for r in rows}
    bad = [m for m in a.match if m not in known]
    if bad:
        raise SystemExit(f"unknown match index {bad}")

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    term = terms[a.termination]
    wanted = set(a.match)
    summary = {
        "substrate": str(Path(a.substrate).resolve()), "film": str(Path(a.film).resolve()),
        "substrate_miller": a.sub_miller, "film_miller": a.film_miller,
        "termination": {"index": a.termination, "film": term[0], "substrate": term[1]},
        "strained_side": "film", "sub_layers": a.sub_layers, "film_layers": a.film_layers,
        "gap_A": a.gap, "vacuum_over_film_A": a.vacuum,
        "zsl": {"max_area": a.max_area, "max_length_tol": a.max_length_tol,
                "max_angle_tol": a.max_angle_tol, "max_area_ratio_tol": a.max_area_ratio_tol},
        "pymatgen_version": getattr(pymatgen, "__version__", "unknown"),
        "candidates": [],
    }
    too_big = 0
    gen = builder.get_interfaces(termination=term, gap=a.gap, vacuum_over_film=a.vacuum,
                                 film_thickness=a.film_layers, substrate_thickness=a.sub_layers,
                                 in_layers=True)
    for idx, iface in enumerate(gen):
        if idx not in wanted:
            continue
        labels = iface.site_properties.get("interface_label", [None] * len(iface))
        per_side = {side: dict(Counter(s.specie.symbol for s, lab in zip(iface, labels) if lab == side))
                    for side in ("substrate", "film")}
        label = f"t{a.termination}_m{idx}"
        folder = out / label
        folder.mkdir(exist_ok=True)
        Poscar(iface.get_sorted_structure(), comment=f"{label} {term[1]} | {term[0]}").write_file(folder / "POSCAR")
        n = len(iface)
        too_big += n > a.max_atoms
        lat = iface.lattice
        summary["candidates"].append({**known[idx], "label": label, "poscar": f"{label}/POSCAR",
                                      "n_atoms": n, "atoms_per_side": per_side,
                                      "lattice_abc_A": [round(x, 4) for x in lat.abc],
                                      "lattice_angles_deg": [round(x, 3) for x in lat.angles]})
        flag = f"  > --max-atoms {a.max_atoms}" if n > a.max_atoms else ""
        print(f"wrote {folder}/POSCAR  {n} atoms  strain(vM)={known[idx]['von_mises_strain']:.4f}{flag}")
    (out / "interface_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"summary: {out / 'interface_summary.json'}  - next: audit_structure.py on each POSCAR")
    return 1 if too_big else 0


if __name__ == "__main__":
    sys.exit(main())
