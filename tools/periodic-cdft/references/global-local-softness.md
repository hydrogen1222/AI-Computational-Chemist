# Validated global electronegativity, hardness and local softness (periodic cDFT)

This document complements `three-engine-protocol.md`. **CDFT means conceptual DFT**, not constrained DFT. For a periodic solid, do not automatically apply isolated-molecule finite-difference formulas to background-charged VASP cells.

## Scientific definitions and naming

At fixed external potential and fixed nuclear geometry, the global electronic chemical potential is `mu=(dE/dN)_v` and conceptual electronegativity is `chi=-mu`. A conventional molecular *vertical* finite-difference approximation uses **integer** charge states:

- `I = E(N-1)-E(N)`, `A = E(N)-E(N+1)`, after physically justified alignment and finite-size/electrostatic corrections.
- `chi=(I+A)/2` (eV). **For this executable's derivative-consistent local-softness route**, `eta_response=I-A` (eV), `S_response=1/(I-A)` (eV^-1), so `s(r)=S_response*f(r)` matches the approximate chain-rule `(d rho/d mu)_v=(d rho/d N)_v*(d N/d mu)_v`.
- **Alternative common chemistry convention:** `eta_half=(I-A)/2` (eV), and some authors call `S_half=1/eta_half=2/(I-A)` the softness. This differs by a factor of two from `S_response`. PR #36 exports `hardness_eV=eta_response`, `hardness_half_gap_eV=eta_half`, `softness_inv_eV=S_response`; it **must not multiply f by S_half while claiming the derivative-consistent response**. When comparing with a paper or Multiwfn, always state the formulas, not just the words hardness/softness.
- `s+(r)=S*f+(r)`; `s-(r)=S*f-(r)`; `s0(r)=S*f0(r)`; `s_dual(r)=S*(f+(r)-f-(r))`. The last is a *derived signed difference of local softness* and not a separate universal reactivity measure.
- `s_A+=S*f_A+`, `s_A-=S*f_A-`, `s_A0=S*f_A0`, `s_A,dual=S*dual_A` **within each charge partition separately**.
- Integral/sum QA: `integral(s+)=integral(s-)=S`, `integral(s_dual)=0`; `sum_A(s_A+)=sum_A(s_A-)=S`, `sum_A(s_A,dual)=0`. Negative local lobes remain signed and are not clipped.
- Space-resolved `s(r)` has units eV^-1 Å^-3 or eV^-1 bohr^-3 (depending on original cube); atomic `s_A` has eV^-1.

**Do not claim unique atomic electronegativities or chemical hardnesses:** atomic electron populations alone do NOT supply atomic I/A or independent atomic chemical potentials. Atom-resolved electronegativity models require separate definitions/parameters and are *not* the condensed Fukui or condensed softness. Local hardness is definition-dependent/controversial, and is **not** `1/s(r)` (nor `1/s_A`). For HSAB, discuss distinct electron-accepting `s+` and electron-donating `s-` at the same physical model and partition, and validate against actual interfacial chemistry; the map cannot predict kinetic barriers. With `dual=f+-f-`, positive dual means relatively electron-accepting/electrophilic **site** (attacked by a nucleophile), while negative means electron-donating/nucleophilic **site** (attacked by an electrophile); do not swap site and attacking-reagent labels.

## Periodic solids: decision gate before numbers

1. Existing `N, N±0.1` CHGCARs **are good for near-neutral density Fukui**, not integer `I/A`. Uncorrected `E(N±0.1)` does NOT equal `E(N±1)`; multiplying fractional slopes into naive I/A is forbidden.
2. Bulk charged PBC VASP uses a compensating background; energy differences can have electrostatic finite-size artifacts and no unambiguous absolute vacuum scale. A slab with defensible vacuum/electrode alignment or a carefully validated *corrected, same-system* charged-cell energy model may support further analysis **only** when charge-state convergence/corrections and common energy reference are documented. In a delocalized infinite semiconductor or metal, electron addition/removal and thermodynamic chemical potentials need a dedicated bulk/electrode model; small finite-cell artifacts are not global molecular hardness.
3. A PBE Kohn-Sham band gap is **not** automatically a validated fundamental `I-A`; hybrid/GW/experimental gap approaches are **labeled proxies** with declared caveats, not acceptable inputs to the strict I/A calculator. Hardness/softness depend on system size and electronic ensemble; report supercell/formula-unit normalization and smearing.
4. Do not combine `I/A` from an isolated ORCA cluster with `f(r)` from an unrelated VASP periodic crystal to obtain `s(r)`; the same external potential/electronic model is required.
5. Absolute `chi` needs a declared physical reference; relative/common-reference comparisons require explicit alignment. No rigorous `I/A` evidence => `NOT_VALIDATED_FOR_CHARGED_PBC` for `chi,eta,S,s`, **but the Fukui outputs remain valid as arithmetic tests**. No additional VASP runs are automatically authorized.

Reference starting points:
- Yang & Parr, *PNAS* 82, 6723 (1985), https://doi.org/10.1073/pnas.82.20.6723
- Pucci & Angilella, *Foundations of Chemistry* 24, 59 (2022), https://doi.org/10.1007/s10698-022-09416-z
- https://vasp.at/wiki/Electrostatic_corrections
- https://vasp.at/wiki/Vacuum_reference_theory

## Evidence-gated reproducible calculation

`scripts/softness.py` never extracts energies from raw OUTCAR. First verify externally derived vertical integer `I,A` values for **the same system used in preflight and the Fukui grids**, including the charge corrections and common reference. A researcher must review the energy model; an agent cannot self-certify physical validity.

Create `postprocess/periodic_cdft/comparison/validated_ia.json` with **real** evidence (schema only; the values below are not real data and must not be pasted into production):

```json
{
  "status": "VALIDATED_VERTICAL_IA",
  "reviewed_by_researcher": true,
  "physical_model": "corrected_charged_supercell",
  "preflight_sha256": "<SHA256 of the exact preflight.json bytes>",
  "source": "<validated numerical energy report/path/DOI>",
  "reference": "<common physical energy reference>",
  "correction_record": "<electrostatic finite-size corrections, potential alignment, convergence evidence>",
  "charge_state_protocol": "corrected_integer_vertical_add_remove",
  "I_eV": 0.0,
  "A_eV": 0.0
}
```

The `I_eV` and `A_eV` fields above are **placeholders**: the command will reject `I<=A`; never use them as results. The supported `physical_model` labels are `corrected_charged_supercell`, `vacuum_aligned_slab`, and `electrode_referenced_interface`; labels are descriptive, **not evidence of a correction**. This program checks provenance metadata, consistency and algebra; it cannot independently certify the physical truth of supplied I/A. The `preflight_sha256` prevents silent cross-case mixing.

With approved evidence and a `grid_audit.json` that actually passed, run:

```bash
mkdir -p /project/Li2S/postprocess/periodic_cdft/local_softness
python tools/periodic-cdft/scripts/softness.py \
  --evidence /project/Li2S/postprocess/periodic_cdft/comparison/validated_ia.json \
  --preflight /project/Li2S/postprocess/periodic_cdft/comparison/preflight.json \
  --grid-audit /project/Li2S/postprocess/periodic_cdft/comparison/grid_audit.json \
  --engine critic2 \
  --condensed /project/Li2S/postprocess/periodic_cdft/comparison/condensed_ddec6.csv \
  --output-dir /project/Li2S/postprocess/periodic_cdft/local_softness
```

Use whichever verified engine/condensed charge method is present; `--condensed` can repeat. Prerequisite: the matching `condensed_*.md` has a PASS marker, all four `fplus/fminus/fzero/dual` cubes appear in audited fields, and the destination exists and has no conflicting outputs. Output: `global_indices.json`, four signed `*_s_*.cube`, and optional `softness_*.csv`. Atomic sums should match global softness and the spatial cubes' integrals after scaling. No source files are overwritten. To include audited energy numbers in the **same single Chinese report**, rerun `scripts/report.py` with `--softness-json /project/Li2S/postprocess/periodic_cdft/local_softness/global_indices.json` and a **new, non-existing** `--out` path; do not overwrite an existing report. This report option is optional and never creates energy numbers by itself.

**For the 3-atom Li2S N±0.1 proof-of-software case, no validated integer I/A is available.** Expected behavior: report `NOT_VALIDATED_FOR_CHARGED_PBC`; do not create fictional softness or insist on extra expensive calculations just to make every column numerical. Agent should add vetted outputs, methodological limitations and any missing status to the **single existing project comparison report**, rather than scattering root Markdown files.

## Software availability checklist (external, not bundled)

- Existing: VASP, Multiwfn, Critic2, Chargemol (verify on each actual machine; availability differs across computers).
- For **third spatial engine**: clone https://github.com/cacarden/FukuiGrid in `~/apps/FukuiGrid`. Its README requires Python 3 with `numpy scipy pandas matplotlib`; run `python3 FukuiGrid.py` in its isolated Python environment, then test the zero-valued-grid writer regression in `three-engine-protocol.md` before accepting any cube.
- For **Bader condensed indices**: https://github.com/henkelmangroup/bader ; use the upstream Linux binary or compile its Fortran source, confirm `bader -h` and set `AICC_BADER_BIN` if the executable is not on PATH. For each charge state use `chgsum.pl AECCAR0 AECCAR2`, then `bader CHGCAR -ref CHGCAR_sum`. This is *not* a `pip install bader` Python package.
- Useful external commands to inspect: `command -v bader`, `command -v python3`, `python3 -c 'import numpy, scipy, pandas, matplotlib'`. The agent, not the user, should capture paths/versions and preserve upstream code.
- **No extra universal package** can magically turn charged PBC TOTEN into validated I/A. Material-appropriate electrostatic correction and energy-reference methods require an explicit scientific model and convergence checks; do not auto-install defect correction software as a substitute.

## Regression test

`python3 -m unittest discover -s tools/periodic-cdft/tests -p 'test_softness.py' -v`

The tests use only small synthetic cubes and CSVs; they verify I/A algebra, conservation, matching fingerprints, missing approvals, faulty charge grids, invalid gaps and overwrite refusal. They also check the response-consistent factor-of-two against the separately reported half-gap hardness. Synthetic numbers do not constitute a scientific validation of periodic Li2S hardness or softness.
