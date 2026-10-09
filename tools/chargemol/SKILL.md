---
name: chargemol
description: Use Chargemol for DDEC6 atomic net charges, sum of bond orders, and pairwise periodic bond orders; batch-process finished VASP datasets and make PPT-ready charts.
---

# Chargemol / DDEC6

This is a single-agent **software Skill**. The external compiled **Chargemol**
program performs the DDEC6 charge and bond-order computations; pymatgen has
a useful ChargemolAnalysis wrapper/parser but **does not replace the executable
or its atomic reference-density library**. Never distribute a Chargemol binary,
atomic reference densities, licensed POTCAR, or secret machine configurations
in this repository.

## Scientific meaning

- **DDEC6 net atomic charge q (e):** positive means electron-deficient,
  negative electron-rich. This is not a formal oxidation state.
- **DDEC6 sum of bond orders (SBO):** one sum per atom; includes contributions
  from pairs below Chargemol's bond-print cutoff.
- **DDEC6 pair bond order (BO):** one bond per atom pair and periodic image
  vector. It is dimensionless and not synonymous with ICOHP or a Lewis bond.
- Comparing values across structures requires consistent DFT settings,
  electronic convergence, comparable chemical environments and a justified
  hypothesis. Geometry/source provenance is essential.

## Inputs

For VASP, require a compatible single completed electron-density calculation
with CHGCAR, AECCAR0, AECCAR2, POTCAR. Generate with LCHARG=.TRUE. and
LAECHG=.TRUE. in the VASP input. Density files cannot be recreated by a
parser. Confirm 3D VASP periodicity, original lattice/atom indices,
spin/charge conditions and convergence. Charge sum alone does not prove
SCF convergence or validity. Chargemol may need POTCAR compatibility
adaptations across versions; record the precise error, do not alter the
original pseudopotentials without understanding the implications.

## Agent workflow

1. Preflight user-provided VASP directories and check files, expected total
   cell charge and installed Chargemol executable / atomic_densities directory.
2. Default batch action is read-only and does not start Chargemol.
3. With explicit approval for this bounded post-processing operation, run
   Chargemol with DDEC6 and compute BOs enabled, one case at a time.
   The user alone submits and monitors **DFT/HPC production calculations**.
4. Collect existing output without an installed binary using collect-only.
5. Check atom counts and element mapping against the original CHGCAR;
   reject invalid numeric data and mismatch in charge balance (if expected
   charge is provided). Preserve periodic image translations and avoid
   double counting reversed pair listings.
6. Provide actual CSVs and an immediately readable Markdown summary.
   When Matplotlib is present, automatically make 16:9 PNG (300 dpi)
   and editable SVG charts suitable for a presentation.

## Commands for the Agent (not homework for the user)

Preflight: python tools/vasp/scripts/batch_ddec6.py CALC_ROOT

Collect output: python tools/vasp/scripts/batch_ddec6.py CALC_ROOT --collect-only --net-charge 0

Execute approved Chargemol postprocessing:
python tools/vasp/scripts/batch_ddec6.py CALC_ROOT --execute --net-charge 0 --binary /path/to/chargemol --atomic-densities /path/to/atomic_densities

Select specific folders: --manifest case_list.txt, one relative folder per line.
Use different batches for distinct charge states; do not assume all cells neutral.

Regenerate figures: python tools/vasp/scripts/plot_ddec6.py CALC_ROOT/postprocess_summary
Optionally supply --case NAME for one selected case or --max-cases 0 for all.

## Output contract

- Original density and POTCAR files are never modified. Chargemol work goes
  under each run's postprocess/chargemol/ and is never silently overwritten.
- Under CALC_ROOT/postprocess_summary/: ddec6_cases.csv (case QC),
  ddec6_atoms.csv (q and SBO per atom), ddec6_bonds.csv (pairs with image
  vectors), ddec6_elements.csv (element means and min-max),
  ddec6_bond_types.csv (bond type means and min-max), ddec6_summary.md,
  and ppt_figures/*.svg + *.png if Matplotlib is installed.
- PPT charts depict **range**, not measurement or statistical uncertainty.
  These figures do not by themselves validate the model or cross-case
  comparability. Keep source paths and all per-case errors in exported CSVs.
- The initial parser follows the Chargemol 2017 format documented by
  pymatgen 2026.9.23. Mock-binary integration tests are NOT sufficient
  for publication use: at least one genuine Chargemol + pymatgen
  numerical cross-check remains required.

## References

- Chargemol official distribution: https://sourceforge.net/projects/ddec/
- pymatgen ChargemolAnalysis: https://pymatgen.org/pymatgen.command_line.html
- DDEC6 charges part 1, DOI 10.1039/C6RA04656H
- DDEC6 charges part 2, DOI 10.1039/C6RA05507A
- DDEC6 bond orders part 3, DOI 10.1039/C7RA07400J
- DDEC6 implementation part 4, DOI 10.1039/C7RA11829E
