---
name: periodic-cdft
description: Use for periodic VASP charge-density Fukui functions f+/f-/f0, dual descriptor, condensed atomic Fukui indices and optional Fukui potentials, using independently installed Multiwfn, Critic2, and FukuiGrid. Scientific preflight and method-by-method comparison; no external code bundled.
---

# Periodic conceptual DFT / Fukui functions (three external engines)

This skill is for **conceptual** density-functional theory, *not constrained DFT*.
All executables and data stay on the researcher's machine. **Never vendor,
pip-install implicitly, patch the user's FukuiGrid clone, or redistribute
VASP POTCAR/CHGCAR, Multiwfn, Critic2 or FukuiGrid code.** No VASP jobs,
scheduler jobs or expensive analyses without permission. Do not invent
output values, convergence or software-supported menu numbers.

Start with `references/three-engine-protocol.md`. The agent should drive the
local programs on the user's behalf, not ask the user to program an algorithm.
If an installed version has not been smoke-tested, mark the particular branch
**UNVERIFIED**, not "success." The protocol is reproducible even if a binary
is temporarily absent.

## Scientific model before any calculations

Choose a single **fixed lattice and fixed ionic positions** for a sequence
of self-consistent VASP single points with electron counts N + δN. Specify:
functional/PAW ZVAL/k-mesh/ENCUT/FFT grid/smearing/spin/convergence, reference
charge and expected delocalized versus localized state. For fractional
occupation near N, use **distinct self-consistent densities**; do not divide
an unverified grid by a guessed δN. N±1 and small-fraction slopes estimate
different observables in general (piecewise linearity, state changes,
finite-size/PBC effects); **do not call their discrepancy a code bug**.

Definitions, always with **positive electronic density** and fixed external
potential:
- `f+ = [rho(N+δ+) - rho(N)]/δ+` (δ+ > 0; electron **addition**);
- `f- = [rho(N) - rho(N−δ-)]/δ-` (δ- > 0; electron **removal**);
- `f0 = (f+ + f-)/2` (declared averaged-response convention);
- `dual = f+ − f-` (sign convention mandatory);
- `f_A+ = [q_A(N)−q_A(N+δ+)]/δ+`,
  `f_A- = [q_A(N−δ-)−q_A(N)]/δ-`, q = ZVAL − population,
  and condensed f_A0 / dual analogous.

Each `f` is in inverse volume (e.g. Å^-3 per added electron).
For electron-conserving neutral-to-charged comparisons, integrals:
`∫f+≈1, ∫f-≈1, ∫f0≈1, ∫dual≈0`.
Local Fukui can contain *negative lobes* due to density relaxation:
never clip negatives or reinterpret any local lobe as a strictly positive
electron probability. A condensed f_A is **method-dependent**, not an
observable and not automatically equal to an integration of a volumetric
Fukui over a fixed Bader basin (basins shift with density).

## Operational sequence

1. Use `scripts/preflight.py --root ... --manifest ...` (read-only by
   default): validate VASP5 species/site positions, lattice, first scalar
   FFT grids, electron sums, NELECT metadata, all δN, and required
   two-sided sampling. Fail closed on incompatible geometry, atom order,
   grid or electron count. For *real* runs, verify source SCF convergence,
   wavefunction/occupation and spin manually as well; parser-only checks
   cannot establish physical validity.
2. Create isolated result directories **under the research project**:
   `postprocess/periodic_cdft/{multiwfn,critic2,fukuigrid,comparison}/`.
   Keep originals read-only, stage symlinks or copies only after conflict
   checks, record executable paths, versions, local command/script and logs.
3. Using the SAME validated N±δ VASP densities, run:
   (A) Multiwfn grid module **13**, density-grid arithmetic, for f±;
   (B) Critic2 VASP LOAD/LOAD AS/CUBE GRID, for f±;
   (C) FukuiGrid finite-difference grid arithmetic for f± **only if its
   installed writer has passed zero-valued-grid regression**.
   FukuiGrid's separate **fractional-occupation interpolation** uses
   independently chosen 4-or-more matching density points on each side.
   The two FukuiGrid *potential* corrections (electrodes / SCPC) are
   conditional, **not** two extra density-Fukui definitions.
   For Critic2, `scripts/make_critic2.py` writes a reproducible
   four-field input from the vetted preflight manifest (default: no
   external execution; explicit `--execute` runs local Critic2).
4. From validated f±, use the **same engine** to produce f0 and dual:
   no additional VASP run. Never substitute f0 for a spin-specific
   radical-attack barrier. For each exported grid verify cell integral,
   origin/axes/shape, units, atom alignment, and f0/dual identities.
   `∫dual≈0` alone is NOT proof of spatial correctness.
5. Optional condensed indices from the existing **three-state charge
   tables**: use `scripts/condensed.py`. Supported matched population
   methods include Bader, Chargemol DDEC6, Chargemol ordinary H/CM5 and
   Multiwfn ordinary H/CM5, provided each is available and valid in
   **all three** electronic states. Keep methods separate. Multiwfn
   Hirshfeld-I only with independently verified iterative convergence,
   not merely a parsed terminal number. If the input lacks three
   independently valid charge tables, mark condensed indices
   `NOT_AVAILABLE`, never infer them from the one neutral state.
6. Compare as a **controlled two-axis matrix**: at one δN,
   Multiwfn vs Critic2 vs (validated) FukuiGrid finite differences
   isolates implementation; within FukuiGrid, finite difference vs
   fractional interpolation diagnoses perturbation/approximation effects.
   Compare same-grid pointwise fields, integrated norms, peak coordinates
   **and** signed negative lobes. The absolute max alone is insufficient.
   Compare condensed indices **within the same population model across
   three states**, not across arbitrary charge conventions. Include
   volume/unit normalization and grid conservation in the Chinese report.
7. Deliver concise Chinese `periodic_cdft_report.md` under the project's
   single `postprocess/periodic_cdft/comparison/` folder: purpose, exact
   case and filenames, method names/δN, all requested available results,
   QC/integrals/side-by-side figures, scientifically qualified findings,
   `NOT_AVAILABLE`/failed statuses, and reproducible commands.
   Use `scripts/report.py` with validated preflight/grid-audit JSON and
   checked condensed CSVs to generate one evidence-grounded Chinese
   summary. Agent then adds physical interpretation and installed-version
   information; never claim missing methods ran.
   Quantitative statements must be generated from actual measured files;
   do **not** publish placeholder output as a result. Plotting final
   figures follows `tools/plotting/SKILL.md`.

## Things deliberately out of scope for a first cross-check

- Electron affinity/ionization energy, electronegativity, hardness,
  softness and electrophilicity from uncorrected *periodically charged*
  VASP total energies. Such numbers need PBC charge corrections, vacuum/
  electrode alignment or a defensible solid-state thermodynamic model.
- Fukui potentials when no legitimate electrode geometry or SCPC
  correction exists; point-charge perturbation energies when no physically
  defined external probe exists. `NOT_APPLICABLE` is an acceptable outcome.
- Equating f+ to a reduction reaction pathway or f- to an oxidation
  barrier. It probes density response, not kinetics or actual metal insertion.

Read scientific implementation caveats in
`references/three-engine-protocol.md` **before running anything**.
