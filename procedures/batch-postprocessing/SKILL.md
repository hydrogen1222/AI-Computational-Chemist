---
name: batch-postprocessing
description: Use when a researcher wants to analyze many existing calculation outputs with VASP/Bader, VASPKIT, LOBSTER, Multiwfn, ORCA, CP2K, or other analysis programs without writing scripts or manually repeating commands.
---

# Batch Scientific Post-processing (one agent)

The user specifies a **scientific observable** and a directory/dataset. The
agent selects the relevant per-software skill and performs discovery, preflight,
execution/collection, validation and aggregation. Do not ask the user to write
Python, shell loops, interactive menu sequences or individual run-directory
commands. This is an **optional skill**, not a new agent or scheduler.

## Procedure

1. **Define the observable and convention.** For example distinguish
   Bader/AIM net atomic charges from charge-density difference, Hirshfeld-I,
   QTAIM bond-critical-point properties, and formal oxidation states. Record
   units, electron-count/reference convention and comparisons.
2. **Discover candidate runs** only in the project/data roots supplied by
   the user. Inventory files and software versions. Map the relevant analysis
   skill and exact prerequisites per case. Do not launch new expensive
   first-principles calculations to supply missing files without approval.
3. **Preflight the batch:** distinguish ready, missing-input, incomplete,
   incompatible-method, pre-existing, and failed cases. Keep case-specific
   structure mapping and parameter metadata; do not silently compare
   incomparable calculations. Show a short preview before significant work.
4. **Execute deterministically:** prefer shipped parsers/wrappers. If a needed
   operation lacks a wrapper, the agent writes and runs a small batch helper
   itself (using the software's documented headless/CLI interface), not
   hundreds of manual commands. Keep source files read-only, isolate newly
   generated outputs, capture command/version/logs, and continue other
   independent cases when one fails. Never silently overwrite results.
5. **Validate and aggregate:** check atom counts/species mapping, grids,
   reference consistency, software return status and tool-specific quality
   indicators. Produce machine-readable CSV/JSON including each case's
   source path, per-case errors, units and result convention. Summarize
   distribution/outliers and scientific limitations without overclaiming.
6. **Deliver:** concise overall results with exact paths to per-case outputs
   and aggregate tables, plus the reusable script and how to rerun it.
   For **atomic charges**, CSV alone is not an acceptable handoff: always
   generate an actual Chinese human-readable Markdown report with
   case QC, per-element and site-resolved values and a careful, quantitative
   explanation suitable for a group meeting or PPT. The agent, not the user,
   writes and verifies the report; never dump raw numbers without interpretation.
   Use `tools/vasp/scripts/charge_report.py` to regenerate these reports from
   existing CSVs without further DFT or population calculations. No
   project status database or extra management Markdown.

### Periodic Fukui functions / conceptual DFT

Route to `tools/periodic-cdft/SKILL.md` for independently
installed Multiwfn/Critic2/FukuiGrid methods on fixed-geometry
VASP `N±δN` electronic states. Separate 3D finite differences
from FukuiGrid fractional-electron interpolation and conditional
SCPC/electrode Fukui potentials. Agent validates atom mapping,
valence-electron integration, FFT grid, spin/SCF, method-specific
outputs, all charge sums and pointwise differences, and generates
a readable Chinese analysis. Do not claim fractional charged PBC
TOTEN automatically yields physical global electronegativity or
hardness; do not install or copy external source into AICC.

### VASP Bader / AIM net charges

Load `tools/vasp/references/electronic-analysis.md`. Required density
files are `CHGCAR`, `AECCAR0`, `AECCAR2` from a compatible converged
calculation with `LCHARG=.TRUE.` and `LAECHG=.TRUE.`.
These files cannot be fabricated by post-processing; absent ones require
an explicitly approved VASP computation if scientifically necessary.

The built-in stdlib batch helper is:

```bash
# Agent preflight, read-only and safe by default:
python tools/vasp/scripts/batch_bader.py /project/calculations

# Explicitly authorized batch processing; runs chgsum.pl then bader:
python tools/vasp/scripts/batch_bader.py /project/calculations --execute

# If ACF.dat already exists, aggregate only; no Bader binaries needed:
python tools/vasp/scripts/batch_bader.py /project/calculations --collect-only
```

It finds runs recursively; use `--manifest` for an explicit shortlist.
If POTCAR metadata are absent, supply **verified** valence electron counts
via `--zval "Na:...,P:...,S:..."`; never guess them. Original VASP
files are not overwritten. Execution writes under each run's
`postprocess/bader/`; aggregate tables are under the selected root's
`postprocess_summary/`. Cases, atom charges and per-element
mean/min/max/spread become three CSV files, plus a Chinese
`bader_summary.md` containing full data, signed charge interpretation,
case-specific errors, and QC. Set `--net-charge` only when the cell's
net charge is verified; without it the report explicitly states that
charge conservation is not checked. `--force` deliberately
overwrites **generated Bader outputs only**; inspect them first.

Use the PAW all-electron reference `AECCAR0+AECCAR2` for Bader partitioning,
and report `q = ZVAL - N_Bader` (e), not formal oxidation states. Keep
element/atom mapping intact and compare like-with-like. The original
`scripts/bader_summary.py` remains useful for one run.

### DDEC6 net atomic charge and bond orders

`tools/chargemol/SKILL.md` and `tools/vasp/scripts/batch_ddec6.py`.
Chargemol, not pymatgen, performs the DDEC6 computation. Keep each atom's
net charge, SBO and the pairwise periodic BO information separate. The
batch reports source-traceable CSVs, the existing technical Markdown,
an explicit Chinese `ddec6_report_cn.md`, and optional PPT-ready
SVG/PNG. Preserve density input provenance and charge-balance checks.
Chargemol and Bader executables are auto-discovered in PATH or typical
installation roots; `--binary` flags and environment overrides are
fallbacks. For DDEC6 show **every printed bond type by default**,
paginate dense slides instead of picking scientifically arbitrary bonds,
and never impute unprinted bond orders as zero.

### Ordinary Hirshfeld / CM5 population analysis

If the user has already run Chargemol DDEC6, first check its
`VASP_DDEC_analysis.output`: the initial *noniterative Hirshfeld*
partition and CM5 values may already be present. Use
`tools/vasp/scripts/collect_hirshfeld.py` to batch-extract results
without starting any electronic-structure or Chargemol program.
Also produce `hirshfeld_report_cn.md`; distinguish Chargemol's
ordinary Hirshfeld and CM5 from Multiwfn, and do not assert that
differences are wholly attributable to any one density convention.
Export full atom/site/element tables, keep source provenance, and
optionally plot Hirshfeld vs CM5 vs DDEC6 for the same density.
Do not confuse this with **Hirshfeld-I**, which requires a separate
iterative charged-reference algorithm.

### Periodic Multiwfn Hirshfeld / CM5 / Hirshfeld-I

Use `tools/multiwfn/references/periodic-stockholder.md` and its
`prepare_periodic_chgcar.py` / `collect_periodic_charges.py`.
The agent prepares Nval using the matching POTCAR, independently
runs each validated Multiwfn menu, then exports all atom/element
charges and compares against the existing Chargemol outputs.
Also generate `multiwfn_report_cn.md`: a failed/unconverged method's
values are not usable even if a last-iteration charge was printed.
Report convergence *separately* from basic file/charge parsing success.
Do **not** label Chargemol's initial Hirshfeld iteration as H-I, nor
substitute an unrelated Multiwfn bond-index method for DDEC6 BO.
MBIS is out of scope.

### Finished plots and exploratory previews

Analysis utilities may write fast 16:9 PNG/SVG previews or diagnostic
figures. For figures intended as finished research/PPT/manuscript
deliverables, load **`tools/plotting/SKILL.md`**: copy the relevant
data into a reproducible `figures/NNN_description/` folder, generate
using the versioned Stormy style and complete its visual/automated QA.
Do not merely relabel an existing generic analysis image as a
Stormy-style publication figure. Do not overwrite the original
post-processing charts or mutate calculation data.

### Other tools

- VASPKIT: `tools/vaspkit/`; determine the installed version and exact
  task/menu protocol, automate in isolated working directories.
- LOBSTER: `tools/lobster/`; verify basis/PAW consistency and charge spilling
  before aggregating COHP/ICOHP. Do not assume pre-existing WAVECAR can
  support LOBSTER without compatible settings.
- Multiwfn: `tools/multiwfn/`; batch only validated input wavefunctions,
  check menu numbers against the actual installed version.
- AIMD/MD: engine trajectory skill and analysis references; preserve time
  windows, temperatures, units, drift/trend and statistical uncertainties.
- Other output types: route to `tools/<engine>/` and build a bounded,
  reusable parser as needed; do not assert a universal batch wrapper exists.

**Permission boundary:** reading/parsing files and preparing a dry run are
ordinary post-processing. Confirm before high-cost analysis, GPU/HPC resource
use, a new electronic-structure calculation, or overwriting data. Post-processing
is not permission to submit new VASP jobs.
