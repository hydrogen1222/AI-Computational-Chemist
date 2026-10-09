# Validating Multiwfn Results

> Load this when: deciding whether a Multiwfn-derived charge, orbital/NTO plot, spectrum, cube, or scalar-field analysis can support a report or manuscript claim.

Multiwfn validates nothing about the upstream calculation. Start by checking the engine output: normal termination, SCF/opt/freq validity, correct state, and provenance.

## Pre-analysis checks

- Input file contains the required information: basis, orbital coefficients, density/state data, spin data when needed.
- The `.fchk`/`.wfn`/`.molden` comes from the same final calculation being discussed.
- Orbital/state indices are mapped to the upstream output, not chosen by visual appeal.
- Charge/multiplicity and spin treatment match the claim.

## Result checks

| Result | Minimum validation |
|---|---|
| atomic charge table | scheme named; basis/method stated; trend compared under identical settings; periodic CHGCAR uses true POTCAR ZVAL, grid and charge-closure checks (`references/periodic-stockholder.md`) |
| spin density | open-shell or broken-symmetry state verified; sign convention and isovalue recorded |
| MO/NTO figure | orbital/state index, occupation/transition, isovalue, and phase/color convention recorded |
| TD spectrum | state list, oscillator/rotatory strengths, broadening, conformer weights recorded |
| conceptual DFT (Fukui, dual descriptor, global indices) | N/N+1/N-1 use one QM geometry, level **and fixed external embedding**; selected charge/spin states checked; condensed population convention and sum tested; bound-state/basis sensitivity, EA sign, hardness convention and cluster/boundary limitations stated (`references/conceptual-dft.md`) |
| ESP/ELF/LOL/NCI/IRI/AIM | scalar function, grid/cutoff/isovalue, and interpretation limit stated |
| cube/VMD figure | cube type, isovalue, color sign, camera/render path, and source file recorded |

## Solid-state stockholder validation

- Original CHGCAR was from a converged calculation; staged Nval first
  line matches the **actual** POTCAR TITEL/ZVAL sequence and OUTCAR NELECT.
  For Li_sv use ZVAL=3, not the common Li 1-valence assumption.
- Save per-method Multiwfn version, full interactive menu logs and
  atomrad reference library used in Hirshfeld-I. Verify H-I actually
  converged by reading its iterative log; an end-of-run charge table
  is not sufficient by itself.
- Enforce one atom/order mapping, finite charges, and charge-sum closure.
  Calculate sensitivity to grid spacing for representative dense/ionic
  systems before interpreting small differences.
- Cross-check Multiwfn H and CM5 against Chargemol's separately
  computed H/CM5; **differences are diagnostics, not necessarily bugs**,
  because input reconstruction, free-atom references and grids can differ.
  H-I and DDEC6 are distinct definitions, not numerical replicas.
- MBIS and Multiwfn bond-index calculations are not part of this task.

## Interpretation limits

- Charge schemes are model-dependent. Use charge trends, not isolated absolute values, unless a specific scheme is justified.
- A single scalar field is rarely sufficient for charge transfer or bonding. Pair it with charges, orbital/NTO, spin density, COHP/AIM, or structural evidence as appropriate.
- NCI/IRI/ELF pictures are qualitative unless the chosen metric and region integration are explicitly reported.
- Spectra are sensitive to conformers, broadening, solvent model, functional, and state count.

## Verification of batch execution

A successful operating-system exit code from Multiwfn does **not** guarantee
successful analysis. A supplied real ORCA 6.1.1 / Multiwfn 2026.10.1
integration example exhibited a zero-byte cube after a hidden submenu question
consumed the next scripted menu response, while the program returned 0.
Before scripted post-processing batches, validate:
- exact expected output file names and plausible nonzero sizes;
- numeric/text format completeness (cube grid header and count, atom count
  and table rows, state/charge identity, computed units and signs);
- known sum-rule checks for N/N+/-1 density differences, when applicable;
- stdin-command transcript and program log for wrong menu branches,
  Fortran input exceptions and unexpected prompts;
- correct source of each energy/wavefunction and the version recorded at run time.

Re-execute an incorrect menu sequence; do not accept the artifact because a
message says `Done!` or a shell reports success.

## Report-ready threshold

A Multiwfn result is report-ready only when the upstream calculation is valid,
the analysis path is reproducible, and the claim states exactly what the analysis
can and cannot prove. For an embedded-cluster solid-state Fukui calculation,
passing normalization tests alone is insufficient: require convergence of
QM size/embedding, no spurious edge electronic states, an unchanged external
potential across N/N+1/N-1, and explicit comparison with the appropriate
periodic VASP observables before interpreting trends in chemical stability.
Record the exact installed Multiwfn version and interactive menu path; do
not assume that an untested batch menu script matches the latest release.
