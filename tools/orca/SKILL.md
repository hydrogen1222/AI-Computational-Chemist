---
name: orca
description: Prepare, validate, run, and troubleshoot ORCA 6 molecular quantum chemistry jobs. Use for single points, geometry optimization, frequencies and thermochemistry, clusters and molecules, open-shell states, dispersion-corrected DFT, and producing wavefunction files for Multiwfn (orbitals, charges, conceptual DFT / Fukui functions).
---

# ORCA

Written for ORCA 6 (checked against the 6.1 manual). ORCA 5 inputs mostly run, but keywords and
defaults changed between major versions; when an input fails on a keyword, check the manual of the
installed version before anything else.

Machine facts (install path, cores, memory, scratch, launch command) are
site-specific. Request the researcher's known configuration rather than
relying on removed scheduler templates or inventing settings.

## Required inputs

- 3D coordinates (from `structure-prep` for a new cluster or molecule).
- **Charge and multiplicity, never guessed silently**: state where they come from. The input check
  script refuses a multiplicity whose parity does not match the electron count.
- Method, basis, dispersion, solvent (if any), and the job type. A source paper's level wins for reproductions.
- What the result is for: an energy, a geometry, thermochemistry, or a wavefunction for Multiwfn.

## Where to find what

| Situation | Go to |
|---|---|
| tool-agnostic molecular QC choices: method, basis, SCF state, Opt/Freq, solvent, BSSE | `knowledge/molecular-qc-practical-rules.md` |
| writing an input: layout, ORCA 6 defaults, templates per job type, cores and memory | `references/running.md` |
| before submitting: run the input check | `uv run scripts/check_orca_input.py JOB.inp` |
| after the run: termination, SCF, optimization, imaginary modes, energies | `uv run scripts/parse_orca.py JOB.out`, then `references/validation.md` |
| the job stopped with an error, or SCF / optimization will not converge | `references/errors.md` (match the exact output string first) |
| wavefunction for Multiwfn (orbitals, charges, ESP, conceptual DFT) | `references/running.md` ("Wavefunction files for Multiwfn"), then `tools/multiwfn/SKILL.md` |
| Na3PS4/solid-state local reactivity by embedded clusters | `references/running.md` ("Periodic-solid to embedded-cluster research boundary"), then `tools/multiwfn/references/conceptual-dft.md` |
| conceptual DFT: Fukui functions, dual descriptor, global reactivity indices | `tools/multiwfn/references/conceptual-dft.md` |
| manual pages and other sources | `references/resources.md` |
| example rules | `examples/README.md` |

## Workflow

1. Decide the quantity first, then the level of theory (`knowledge/molecular-qc-practical-rules.md`).
2. Write the input from `references/running.md`; record where charge and multiplicity come from.
3. Run `uv run scripts/check_orca_input.py JOB.inp` (add `--mem-gb` with the machine's free memory). Fix every FAIL. A WARN for `* pdbfile`/QM/MM means **the checker has NOT validated the QM electron count or embedded-region assignment**; resolve this with the structural/model checklist before submitting.
4. Give the researcher a manual command or script using ORCA's **full path**,
   never directly under `mpirun`, with output redirected to `JOB.out`.
   The agent does not submit or monitor ORCA jobs.
5. Run `uv run scripts/parse_orca.py JOB.out`; apply `references/validation.md`. On failure go to `references/errors.md` and change one thing at a time.
6. Hand validated `.gbw` / molden files to Multiwfn only after step 5 passes.

## Hard guardrails

- Opt and Freq at the same level of theory; a minimum has 0 imaginary modes.
- Never carry an unconverged SCF or optimization into frequencies, energies, or Multiwfn analysis.
- Energies compared across species share functional, basis, dispersion, solvent, grid, and RI settings.
- State the energy type (electronic E, E+ZPE, H, G) and unit on every number; ORCA prints Hartree (Eh).
- Keep the `.inp`, `.out`, `.gbw`, and the final `.xyz`; record the ORCA version printed in the output header.
- Use the **installed** ORCA/Multiwfn version and its matching manual; examples in this repository are guides, not a license to assume that menu numbers, conversion formats, or crystalprep flags still work. Do not download or redistribute proprietary manuals into this repository.
- Embedded-crystal Fukui analysis is exploratory until cluster-size, embedding, electron binding, spin and periodic cross-checks pass. Do not call cluster IP/EA the bulk electrochemical stability window or use conceptual-DFT indices as substitutes for VASP reaction energies/barriers.
