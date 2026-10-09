# Three-engine periodic VASP Fukui protocol (Multiwfn / Critic2 / FukuiGrid)

**Purpose:** compare **the same electronic-density observable** on **exactly the same
fixed supercell** without confusing code differences with different δN
approximations, charge models, or periodic electrostatic corrections.

Authoritative upstream references:
- VASP CHGCAR normalization: https://www.vasp.at/wiki/CHGCAR
- Critic2 LOAD/LOAD AS: https://aoterodelaroza.github.io/critic2/manual/fields/
- Critic2 CUBE GRID: https://aoterodelaroza.github.io/critic2/manual/graphics/
- Critic2 grid SUM: https://aoterodelaroza.github.io/critic2/manual/misc/
- FukuiGrid: https://github.com/cacarden/FukuiGrid ; 2026 CPC article
  https://doi.org/10.1016/j.cpc.2025.109957
- Multiwfn installed manual, GUI/noGUI grid-data menu 13; version-dependent.
- AICC molecular/cluster CDFT (NOT VASP reciprocal-space calculation):
  \`tools/multiwfn/references/conceptual-dft.md\`.
Do not interchange molecule-only main-menu 22 wavefunction features with
VASP CHGCAR grids. Never claim VASP WAVECAR is a Multiwfn molecular
wavefunction file.

## 0. Input contract: a single VASP *family*

Given root \`/project/fukui_vasp\`, organize verified source calculations as:

\`\`\`text
/project/fukui_vasp/
  00_N/          INCAR KPOINTS POSCAR POTCAR CHGCAR OUTCAR
  plus_005/      INCAR KPOINTS POSCAR POTCAR CHGCAR OUTCAR
  plus_010/      ...
  plus_015/      ...
  minus_005/     ...
  minus_010/     ...
  minus_015/     ...
  cdft_states.json
\`\`\`

The **manifest is the only new input file**, not an additional project-root
README. Electron counts in OUTCAR must differ by the *declared* delta:

\`\`\`json
{
  "states": [
    {"label": "N", "directory": "00_N", "delta_electrons": 0},
    {"label": "p005", "directory": "plus_005", "delta_electrons": 0.05},
    {"label": "p010", "directory": "plus_010", "delta_electrons": 0.10},
    {"label": "p015", "directory": "plus_015", "delta_electrons": 0.15},
    {"label": "m005", "directory": "minus_005", "delta_electrons": -0.05},
    {"label": "m010", "directory": "minus_010", "delta_electrons": -0.10},
    {"label": "m015", "directory": "minus_015", "delta_electrons": -0.15}
  ]
}
\`\`\`

The agent, NOT the user, inventories existing calculations and writes this
manifest with **actual** counts. The quantities 0.05/0.10/0.15 are
examples, not mandatory values. All states use **same fixed positions**,
cell, pseudopotential, XC/smearing, spin policy, KPOINTS and fine FFT grid.
Use single-point ionic settings (typically NSW=0), validate SCF.
A comparison between individually relaxed charged structures is not
fixed-external-potential Fukui. Reference charge need not be zero.

Preflight, non-destructive (prefer user-approved root):

\`\`\`bash
python tools/periodic-cdft/scripts/preflight.py \
  --root /project/fukui_vasp \
  --manifest /project/fukui_vasp/cdft_states.json
\`\`\`

After the output has passed operator review, the agent may record a
machine-readable manifest fingerprint in an already-prepared output dir:
\`--write /project/fukui_vasp/postprocess/periodic_cdft/comparison/preflight.json\`.
No overwrites. \`SCF_EDIFF_marker=false\` is a warning that requires manual
review, NOT permission to proceed. Source CHGCAR/POTCAR never leave machine.

VASP stores its first scalar CHGCAR grid as \`rho(r)*Vcell\` with
\`sum(raw)/Ngrid = valence NELECT\`. It is **not** a density in e/Å³ until
divided by real cell volume. Multiwfn/Critic2/FukuiGrid may choose different
output units. Verify exported grid integrals **after conversion**.

## 1. Three engines, same finite differences

Compare at the same **nonzero** \`δ>0\` available on *both* sides, e.g.
0.10 e. If electron counts are not symmetric, use separate positive
and negative actual δ values. Prepare \`f+\` and \`f-\` in each engine.

**Common field-output QA after each engine:** collect fplus, fminus,
fzero and dual in individual Gaussian `.cube` files, with **positive
grid counts (bohr units)** and identical axis/origin/sample order.
Do not accept mismatched unit-convention cubes as equivalent.
Our independent `scripts/grid_audit.py` compares all same-finite-
difference engines pointwise and checks `∫f±≈1`, `∫f0≈1`,
`∫dual≈0`, and both pointwise identities. Example:

```bash
python tools/periodic-cdft/scripts/grid_audit.py \
  --cube critic2:fplus:/project/fukui_vasp/postprocess/periodic_cdft/critic2/fplus.cube \
  --cube critic2:fminus:/project/fukui_vasp/postprocess/periodic_cdft/critic2/fminus.cube \
  --cube critic2:fzero:/project/fukui_vasp/postprocess/periodic_cdft/critic2/fzero.cube \
  --cube critic2:dual:/project/fukui_vasp/postprocess/periodic_cdft/critic2/dual.cube \
  --cube multiwfn:fplus:/project/fukui_vasp/postprocess/periodic_cdft/multiwfn/fplus.cube \
  --cube multiwfn:fminus:/project/fukui_vasp/postprocess/periodic_cdft/multiwfn/fminus.cube \
  --out /project/fukui_vasp/postprocess/periodic_cdft/comparison/grid_audit.json
```

Add analogous `fukuigrid-fd` or `fukuigrid-interp` cubes when
the local version is separately validated; interpolation is NOT
subject to the exact finite-difference engine-agreement threshold.
The script creates `grid_audit.json` and a Chinese
`grid_audit.md`, and never edits input cubes. This does not
replace source NELECT preflight or validate PBC electrostatics.

**Multiwfn** (already installed on user's machine):
- Use local executable and installed manual to load one VASP density as
  cube through **grid-data main function 13** and convert other CHGCARs
  onto the SAME real-space origin, axes and grid. Validate one conversion
  with electron-number integration before automating menu sequences.
- Documented menu path for appropriate versions: main 13, grid arithmetic
  submenu 11, operation 4 (subtract a second grid); verify **operand order**
  with a deliberately simple positive/negative test. Export to cube
  without interpolation/normalization changes; record menu transcript.
- \`f+ = (rho_p−rho_N)/δ+\`; \`f- = (rho_N−rho_m)/δ-\`. If menu paths,
  CHGCAR conversion or cube export differ in the installed build, STOP
  and label **UNVERIFIED**, do not try main function 22 on a VASP grid.

**Critic2** (external executable, not bundled). The agent may
generate its validated one-shot four-field input by:
```bash
python tools/periodic-cdft/scripts/make_critic2.py \
  --root /project/fukui_vasp \
  --preflight /project/fukui_vasp/postprocess/periodic_cdft/comparison/preflight.json \
  --plus-label p010 --minus-label m010 \
  --workdir /project/fukui_vasp/postprocess/periodic_cdft/critic2
```
Use explicit `--execute` only after the researcher authorized local
postprocessing and the installed syntax has been confirmed, then check
all four cube files with `grid_audit.py` before scientific reporting.
Reference protocol is **not evidence of having locally run Critic2**.

**Critic2** syntax template (external executable), from
upstream LOAD and CUBE GRID docs; example for two INPUT CHGCAR paths
with \`δ+ = 0.10\`:

\`\`\`text
CRYSTAL 00_N/POSCAR
LOAD VASP 00_N/CHGCAR ID neutral
LOAD VASP plus_010/CHGCAR ID plus
LOAD AS "($plus-$neutral)/0.10" SIZEOF neutral ID fplus
SUM fplus
CUBE GRID FILE fplus.cube FIELD fplus
\`\`\`

For the other direction:
\`\`\`text
CRYSTAL 00_N/POSCAR
LOAD VASP 00_N/CHGCAR ID neutral
LOAD VASP minus_010/CHGCAR ID minus
LOAD AS "($neutral-$minus)/0.10" SIZEOF neutral ID fminus
SUM fminus
CUBE GRID FILE fminus.cube FIELD fminus
\`\`\`

Place input and generated output in the proper local isolated workdir;
adjust RELATIVE PATHS to the actual working directory, and check the
installed binary accepts expression names. Generate \`f0\`, \`dual\`
via additional \`LOAD AS "($fplus+$fminus)/2"\` and
\`LOAD AS "$fplus-$fminus"\` on fields from the same two-sided set, or
by similarly documented FIELD expressions; preserve all input metadata.
Upstream docs:
https://aoterodelaroza.github.io/critic2/manual/fields/ ,
https://aoterodelaroza.github.io/critic2/manual/graphics/ .
Use \`SUM\` on each field to verify expected normalized cell integrals.
Do **not** treat Critic2's built-in AIM basin electron populations as
identical to user-selected Bader/Chargemol atomic charge models.

**FukuiGrid** (user's external git clone, GPL-3.0, NOT copied into AICC):
- Source at \`cacarden/FukuiGrid\`, read commit SHA, version, local
  dependencies, user-visible license; run in a dedicated work folder.
- **Finite differences:** FukuiGrid's grid addition/subtraction/scaling
  can implement exactly the same \`f+\`/\`f-\` as the other two codes.
  The published CPC article describes both finite difference and
  interpolation. For a raw density check, compute normalized differences
  directly; validate the writer's output *including true interior ZERO*
  samples and \`Ngrid\` values before claiming any valid output. The
  upstream \`write_fukui_file\` in the 2025-12-17 SHA
  \`a9d349044ea52bbae22028b219e13b5bc94a10de\` contains
  \`for value in row if value != 0\`, which can silently drop valid
  zero-valued data. **Treat it as a BLOCKER until a local fixed upstream
  release or an independently verified noncorrupt writing path is used.**
  Do not make changes to the researcher's clone silently.
- **Interpolation:** Use separate 4-point sets on EACH side if
  available; menu \`1 -> 11\` for f- with default δN
  \`[-0.15,-0.10,-0.05,0]\`, \`1 -> 12\` for f+ with
  \`[0,+0.05,+0.10,+0.15]\` in the cited version; exact input order
  and δ values are critical. The source routine
  \`Fukui_interpolation(CHGCAR1,CHGCAR2,CHGCAR3,CHGCAR4,dn=...)\`
  fits a linear slope at each point; this is NOT the same estimator as
  δ=1 or δ=.1 finite differences. Check there are enough distinct points,
  record fit residuals (the upstream's single correlation diagnostic is
  not per-grid-point R²).
- **Fukui potential (optional)** has two *correction approaches*:
  \`electrodes\` and \`SCPC\`. The former requires an appropriate
  slab/electrode geometry and dielectric/surface assumptions;
  SCPC requires genuine external \`z-vcor.dat\` correction. Neither
  is a generic bulk periodic \`f+\`/\`f-\` alternative, and neither
  is automatically applicable to Na3PS4 bulk. If files or physical
  boundary conditions absent: \`NOT_APPLICABLE\` — **no fabricated data**.
- Point-charge interaction estimates via the paper's perturbative
  expansion additionally require a well-defined external probe/charge
  and reference. They are not required just to compare Fukui densities.

## 2. Derived observables and conditional opportunities

Once *valid* f+ and f- from an individual method exist:
\`\`\`text
f0(r)      = [f+(r) + f-(r)] / 2
dual(r)    = f+(r) - f-(r)
∫f+ ≃ 1,  ∫f- ≃ 1,  ∫f0 ≃ 1,  ∫dual ≃ 0
\`\`\`

Additionally useful: signed min/max, integral of negative/positive lobes,
planar mean along a **declared physical** crystallographic/surface axis,
spatial localization and direct pointwise comparison. These are
postprocessing diagnostics, not additional conceptual-DFT "theorems".
For identical f+ and f- grids, produce f0 and dual with field algebra
rather than additional electronic SCF runs.

**Condensed atomic Fukui**, from **validated per-state atomic charges**
for the SAME population model:
\`\`\`bash
python tools/periodic-cdft/scripts/condensed.py \
  --preflight postprocess/periodic_cdft/comparison/preflight.json \
  --method bader \
  --neutral 00_N/postprocess_summary/bader_atoms.csv \
  --plus plus_010/postprocess_summary/bader_atoms.csv \
  --minus minus_010/postprocess_summary/bader_atoms.csv \
  --delta-plus 0.1 --delta-minus 0.1 \
  --output postprocess/periodic_cdft/comparison/condensed_bader.csv
\`\`\`
Other methods:
\`ddec6\`, \`chargemol-h\`, \`chargemol-cm5\`,
\`multiwfn-h\`, \`multiwfn-cm5\`. Each requires every state, same
atom indexing and complete output; report unavailable methods, do
not fill missing values by guessing. The script refuses absent or
nonconserved atomic responses and writes an actual Chinese scientific
summary, not CSV only. Different population definitions must remain
distinct; Hirshfeld-I is currently **blocked** unless convergence has
been independently validated — Li2S case was not converged.

**Additional CDFT global indices:** vertical ionization energy,
electron affinity, electronegativity, hardness, softness and Parr
electrophilicity can be derived only from **justifiable total
energy differences with a physical vacuum/reference and PBC charged
cell correction**. Report \`NOT_VALIDATED_FOR_CHARGED_PBC\` by default;
do NOT compute a table of spurious \`I\`, \`A\` and \`η\` from arbitrary
background-charged VASP TOTEN. Same for physical reaction rates or
barriers; a Fukui map alone cannot predict them.

## 3. What the comparison report must include

AICC's agent is responsible for publishing a **plain Chinese,
source-traceable** \`postprocess/periodic_cdft/comparison/periodic_cdft_report.md\`,
with these report-level components in this one file (no extra Markdown
sprayed into the repository root):

- A simple, explicit title, system, all electronic states and δ values;
  functional, PAWs, geometry freeze, spin, grid, versions + executable
  paths. Original files' SHA-256 or immutable paths.
- Matrix of \`f+\`, \`f-\`, \`f0\`, \`dual\` by Multiwfn/ Critic2/
  FukuiGrid finite differences; FukuiGrid interpolation separately.
  For each, actual output path, format, units, charge integral and
  status \`PASS\`, \`FAIL\`, \`UNVERIFIED\` or \`NOT_APPLICABLE\`.
- Numeric consistency checks and explanations in normal language;
  *not* invented results, generic "more reactive" labels or a claim
  that the software agrees unless grid-point overlap is checked.
- Condensed f_A+/f_A-/f_A0/dual all atoms and elements per supported
  charge scheme, with warning when basins or references change.
- If a slab Fukui potential actually exists, report both electrodes
  and SCPC branches **separately** with inputs and limitation.
- At least one peer-to-peer signed field difference or correlation
  metric after matching cube origin, axes, units and shapes; variation
  from code must be separated from variation in electronic perturbation.
  \`N±1\` vs \`N±0.1\` not a direct code-only agreement benchmark.
- A short PPT-quotable conclusion **only if** data passed tests; say
  "未通过数值验收，暂不用于反应位点判定" where appropriate.
  Figures for publication go through Stormy-drawing Skill.

## 4. Failure-mode checklist and ownership

\`CHGCAR\` vs \`CHG\` vs all-electron densities are not interchangeable.
Do not silently normalize each field to an integral of 1: such
renormalization can hide a wrong NELECT or wrong cell. Never clip
negative Fukui lobes. Be careful with spin magnetization grids,
PAW augmentation, parallel-grid orientation, out-of-order atoms,
tetragonal noncubic cells, self-consistent occupation/state crossings,
electronic finite-size/delocalization, compensated PBC backgrounds and
physical reactivity interpretation.

For equal δ and scientifically matching inputs, Critic2, Multiwfn and
FukuiGrid finite differences should be **arithmetically close** within
the output grid/interpolation precision. If they differ greatly, it is
a test failure until density input, normalization, grid orientation,
sign, zero-discard bugs and algorithm settings are checked; it is **not**
a legitimate example of competing conceptual-DFT physical predictions.
FukuiGrid's separately fitted near-neutral derivative can differ
for substantive physical/approximation reasons.
