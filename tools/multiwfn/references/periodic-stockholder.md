# Periodic stockholder charges from VASP — Multiwfn

**Scope:** ordinary Hirshfeld (H), CM5 and **iterative Hirshfeld-I
(H-I)** for 3D-periodic systems. **MBIS is explicitly out of scope.**
See Tian Lu's original tutorial, June 8, 2024:
http://sobereva.com/712 ("使用Multiwfn对周期性体系计算Hirshfeld(-I)、CM5和MBIS原子电荷").
The tutorial specifies Multiwfn builds updated May 25, 2024 or later.
For VASP, use the **valence CHGCAR directly**, but edit the *first line
of a separate work copy* to identify true PAW valence nuclear charges.

## What each program actually does

| Observable | Engine |
|---|---|
| Standard Hirshfeld / CM5 | Multiwfn; also in Chargemol's first noniterative DDEC6 log |
| True iterative Hirshfeld-I | **Multiwfn** with the installed `atomrad/` ionic reference database |
| DDEC6 q, DDEC6 SBO and periodic DDEC6 pair BO | **Chargemol** only |
| Other bond indices in Multiwfn | Different definitions — do not relabel them DDEC6 BO |

H-I is **not** the initial Hirshfeld step in Chargemol, and DDEC6 is
not equivalent to H-I. No MBIS computation is requested or scheduled.
Bader remains handled by the existing Bader Skill.

## Source checks before touching files

1. Require the **same converged VASP static calculation's**
   `CHGCAR`, `POTCAR`, and (recommended) `OUTCAR`. Do not mix files
   from different relax/static steps or different PAW datasets.
   VASP `CHGCAR` contains valence density, and the PAW one-center
   occupancy records are not a substitute for AECCAR all-electron
   reconstruction. Multiwfn's charges from a valence grid and
   Chargemol's reconstructed/reference-density analysis may differ
   for justified method-dependent reasons.
2. Inspect the VASP5 CHGCAR **species order and per-species atom counts**.
   Parse `TITEL` and actual `ZVAL` for *each* POTCAR dataset in the
   **same order**. Don't assume Li always has ZVAL=1; `Li_sv` normally
   has ZVAL=3. If the local cell contains `S` then `Li_sv`,
   the three-atom Li2S CHGCAR work copy's first line should be
   `Nval S 6 Li 3` (valence sum 12, consistent with NELECT=12).
3. Never edit the source CHGCAR or POTCAR. AICC's
   `scripts/prepare_periodic_chgcar.py` streams a byte-for-byte density
   body into `<case>/postprocess/multiwfn/CHGCAR_Nval`, replacing
   **only its first title line**. It prints the derived Nval,
   valence-electron sum, OUTCAR NELECT and inferred net charge.
   Default invocation is read-only; `--prepare` is explicit.
   Existing work copies are not overwritten. No CHGCAR or POTCAR
   is uploaded or committed.
4. If the PAW species is ambiguous or POTCAR missing, stop and ask
   the researcher to locate the matching local POTCAR. Do **not**
   fabricate `Nval` from atomic numbers.

## Multiwfn execution (the local agent does this)

Discover installed Multiwfn in PATH or standard local application roots.
Record its actual version, location, and the matching manual.
`Multiwfnpath` points to the directory containing `settings.ini`,
not necessarily to the executable. Work in the per-case isolated folder.

**First validate the installed menu with one small real example.**
The reference tutorial's main function 7 ("Population analysis")
uses **1** = ordinary Hirshfeld, **16** = CM5, and **15 → 1** =
Hirshfeld-I with default settings; run H-I only after locating the
installed Multiwfn `examples/atomrad/` charge-state radial-density
reference folder in the current analysis working directory (may
symlink the unmodified installed folder). Treat these menu numbers as
**documented reference values**, not a guarantee across installations.

For each method the agent:
- Tests prompts interactively on a single Li2S case; notes the actual
  `y` prompt for reading Nval from the file's first line, the menu
  path, the return/exit prompts, and how to decline optional CHG export.
- Saves the actual validated **stdin menu transcript** and executes
  `Multiwfn CHGCAR_Nval < METHOD.commands > METHOD.log 2>&1` in
  the isolated working directory. Filename aliases in that directory
  should be exactly `hirshfeld.log`, `cm5.log`,
  `hirshfeld_i.log`. Retain `*.commands` and Multiwfn version.
  Do not assume a fixed command transcript is compatible with all
  Multiwfn versions, or accept an exit code of 0 without checking
  the result table.
- Checks all atom indices, species, net charge, finite numbers,
  and the **Hirshfeld-I iteration convergence** from the unabridged
  console log. Do not treat a plausible H-I value or convergence of the
  VASP SCF as proof of H-I iteration convergence.
- Never launches VASP/HPC scheduler jobs. Only bounded post-processing
  in the user's interactive session is permitted.

These menu transcripts are created by the **agent**, not homework for
the user. Do not place absolute local executables, private POTCARs or
densities in Git.

## Batch operation and comparisons

The user can simply say: "用Multiwfn重新计算所有 VASP CHGCAR 的
Hirshfeld、CM5 和 Hirshfeld-I 电荷，与 Chargemol 做交叉验证，输出
CSV 和 PPT 图。" The agent implements the batch with:

```bash
# Read-only scan: verify species order and true ZVAL from local POTCAR
python tools/multiwfn/scripts/prepare_periodic_chgcar.py CALC_ROOT

# Stage isolated first-line-only density copies for each valid case
python tools/multiwfn/scripts/prepare_periodic_chgcar.py CALC_ROOT --prepare

# AFTER the agent has run version-validated menus and archived logs:
python tools/multiwfn/scripts/collect_periodic_charges.py CALC_ROOT --net-charge 0
```

Use a newline-separated `--manifest cases.txt` for selected cases
and separate batches for cells with different total charges.
Do not force a neutral-charge check on a charged system.
The postprocessor accepts **no guessed/surrogate method**: unavailable
logs produce clear per-method ERROR/blank data.
It also reads existing Chargemol first-step Hirshfeld/CM5 from
`VASP_DDEC_analysis.output` plus final DDEC6 charges, when available,
without rerunning Chargemol.

**Output:** under `CALC_ROOT/postprocess_summary`:
The human-facing Chinese report is required even when the user only
requests numerical results. Do not hand off CSVs alone. Any failed
H-I iteration is invalid as a reported charge and must remain
an explicit method failure rather than a speculative numerical result.
- `multiwfn_report_cn.md` — actual Chinese, presentation-ready
  case descriptions, full element/atom comparisons, QC and status
  interpretation; never quote a nonconverged H-I number.
- `multiwfn_atoms.csv` — every atom with H, CM5, H-I from
  Multiwfn beside existing Chargemol H, CM5 and DDEC6 values;
- `multiwfn_elements.csv` — per-element means/min/max;
- `multiwfn_qc.csv` — method-by-method status, charge closure and logs;
- `multiwfn_charge_comparison.md` — all-atom readable comparison;
- `ppt_figures/*_pageNN.{svg,png}` — 16:9 vector/300-dpi figures
  when matplotlib is installed.

## Interpretation, not overvalidation

- Compare ordinary H vs H and CM5 vs CM5 first, **not H-I vs DDEC6
  as if they were the same definition**. Report signed differences
  and explanations of reference-grid/atomic-density conventions.
  Chargemol's initial H/CM5 and Multiwfn H/CM5 can legitimately differ.
- H-I uses charge-dependent reference atoms and updates iteratively.
  H-I is usually larger in magnitude than H in strongly ionic systems,
  but neither the relative ordering nor a chemically intuitive sign
  certifies numerical accuracy. Check Hirshfeld-I stability with grid
  refinement, especially for solids and low-symmetry interfacial sites.
- For primitive Li2S, independently compare the two symmetry-related
  Li charges and check S/Li values add to the expected charge.
- When Multiwfn and Chargemol disagree, inspect **actual input density**
  (valence CHGCAR vs reference-density conventions), pseudo-atom
  valence counts, ionic reference densities, software versions,
  integration grid and convergence. **Do not tune values to match.**
- Charges in any method are **not oxidation states**. CM5 was fitted
  primarily to molecular electrostatic/dipole information; do not
  claim it is automatically the best choice for periodic solids.

## References

- Tian Lu, "使用Multiwfn对周期性体系计算Hirshfeld(-I)、CM5和MBIS原子电荷",
  http://sobereva.com/712 (June 8, 2024).
- Multiwfn user manual §3.9.1 (H), §3.9.13 (H-I), §3.9.14 (CM5);
  use the manual bundled with the actual installed version.
- VASP CHGCAR format: https://www.vasp.at/wiki/CHGCAR
