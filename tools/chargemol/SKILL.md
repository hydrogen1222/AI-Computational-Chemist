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

## Ordinary Hirshfeld charges and CM5 — included in DDEC6 logs

Chargemol v3.5 performs **noniterative neutral-reference Hirshfeld**
partitioning in the first iteration of a DDEC6 analysis. The labeled block
in `VASP_DDEC_analysis.output` contains atomic charges; the same log
normally prints CM5 charges, too. **No repeat DFT or Chargemol execution**
is needed if the source log is retained.

The agent uses `python tools/vasp/scripts/collect_hirshfeld.py CALC_ROOT`
for read-only discovery and adds `--collect-only` to write full per-atom,
per-element, and charge-method-comparison tables. Add `--net-charge 0`
when the original system is confirmed neutral, to verify charge closure.

- Output: `hirshfeld_atoms.csv`, `hirshfeld_elements.csv`,
  `hirshfeld_cases.csv`, `hirshfeld_summary.md`, and 16:9
  `ppt_figures/*_charge_methods.{svg,png}` if Matplotlib is available.
- Compare **ordinary Hirshfeld**, CM5 and DDEC6 calculated from the
  same density, with distinct column labels and no inferred oxidation states.
- This does **not** produce iterative Hirshfeld-I. Do not relabel the
  first DDEC6 partition, DDEC6 itself or CM5 as Hirshfeld-I.
- If the Chargemol log lacks a uniquely labeled first-iteration block,
  report missing evidence; never guess charges from the final DDEC6 XYZ.

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

1. Preflight VASP results and find Chargemol plus its **separate reference
   density library automatically** using PATH, environment variables, and a
   bounded search of `~/apps`, `/opt/apps`, `~/.local/bin`, and related
   common locations. A user-supplied path is a *fallback*, not a requirement.
   If several installations are found, report the choices instead of
   silently selecting one. Verify actual `c2_*.txt` reference files.
   This software discovery can be reused by Bader and chgsum.pl.
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
python tools/vasp/scripts/batch_ddec6.py CALC_ROOT --execute --net-charge 0

The script finds the executable and `atomic_densities/` automatically when
possible. If the executable/library is installed elsewhere, set one-time
`AICC_CHARGEMOL_BIN` / `DDEC6_ATOMIC_DENSITIES_DIR` or provide
`--binary` / `--atomic-densities`. Optional `AICC_SOFTWARE_ROOTS`
(colon-separated on Linux) adds other search roots without editing code.
The agent can diagnose discovery with
`python tools/vasp/scripts/software_locator.py chargemol`.

Select specific folders: --manifest case_list.txt, one relative folder per line.
Use different batches for distinct charge states; do not assume all cells neutral.

Regenerate figures: python tools/vasp/scripts/plot_ddec6.py CALC_ROOT/postprocess_summary
All cases and all Chargemol-reported bond types are included by default.
If the slide has too many categories, the plotter adds `_part02`, `_part03`
pages instead of dropping categories; use `--items-per-figure 10` to
control pagination. `--max-cases N` is an opt-in limit only. Molecular
pairs absent from the Chargemol printed bond list are **not** silently
classified as zero: the output has a print threshold, and only reported
bond classes appear. Use the full raw BO table for detailed analysis.

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

## Chemical validity flags learned from Li2S testing

For antifluorite Li2S with one S and two Li atoms per primitive cell,
an ideal structure has 8 distinct nearest-neighbor Li–S *periodic*
connections overall, but only 4 around each Li. A printed list of 8
connections cannot all be called "Li1–S1" without inspecting atom indices.
Verify the pair table, cell translations and bond lengths.

A periodic self-image bond (e.g. S–S between reference S and a translated S)
can contribute **twice** per distinct undirected connection to the local
SBO. Therefore do not compare SBO with the simple unweighted sum of
element-pair means, and do not call a small S–S BO a conventional sulfur
covalent bond merely because the method printed it. Compare symmetry
equivalent bonds of equal distances and flag conspicuously different BOs
for follow-up; validate geometry and output parsing before interpreting.

Retain all Chargemol-printed bond types without hiding weak entries.
Every slide summary must identify whether the displayed error range is
min–max across bonds/atoms, not statistical uncertainty.

## References

- Chargemol official distribution: https://sourceforge.net/projects/ddec/
- pymatgen ChargemolAnalysis: https://pymatgen.org/pymatgen.command_line.html
- DDEC6 charges part 1, DOI 10.1039/C6RA04656H
- DDEC6 charges part 2, DOI 10.1039/C6RA05507A
- DDEC6 bond orders part 3, DOI 10.1039/C7RA07400J
- DDEC6 implementation part 4, DOI 10.1039/C7RA11829E
