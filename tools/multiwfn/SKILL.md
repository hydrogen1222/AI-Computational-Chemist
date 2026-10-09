---
name: multiwfn
description: Run and interpret Multiwfn molecular wavefunction analysis and periodic VASP CHGCAR-based Hirshfeld, CM5 and Hirshfeld-I charges. Use for fchk/wfn/molden/cube-based orbital plots, population/charge analysis, spin density, NTO and TD-DFT state analysis, conceptual DFT (Fukui functions, dual descriptor, global reactivity indices), electrostatic potential, ELF/LOL/AIM/NCI/IRI-style analyses, spectra post-processing, and VMD/cube handoff.
---

# Multiwfn

Multiwfn is a post-processing and wavefunction-analysis tool. It does not validate the upstream quantum-chemistry calculation; first confirm the Gaussian/ORCA/CP2K/etc. job is converged and scientifically valid.

Inputs from ORCA: convert the validated `.gbw` with `orca_2mkl <job> -molden` (see `tools/orca/references/running.md`).

## Required inputs

- Wavefunction/data file: preferably `.fchk`, `.wfn`, `.wfx`, `.molden`, or cube/grid files.
- Upstream provenance: method, basis, charge/multiplicity, solvent, dispersion, state number when relevant.
- Analysis target: charge, orbital/NTO, spin density, ESP, ELF/LOL, AIM, NCI/IRI, spectrum, or cube export.
- Figure/report target: exploratory, SI-ready, or publication-ready.

## Where to find what

| Situation | Go to |
|---|---|
| choosing and running common Multiwfn analyses | `references/running.md` |
| orbital/NTO, charge, spin density, ESP/ELF/NCI/IRI, UV/ECD spectrum workflows | `references/orbital-charge-spectra.md` |
| conceptual DFT: Fukui functions, dual descriptor, condensed indices, IP/EA/hardness/electrophilicity | `references/conceptual-dft.md` |
| periodic VASP CHGCAR: Hirshfeld, CM5, Hirshfeld-I and Chargemol comparisons | `references/periodic-stockholder.md`; `scripts/prepare_periodic_chgcar.py`; `scripts/collect_periodic_charges.py` |
| periodic VASP CHGCAR Fukui via grid operations + two other engines | `tools/periodic-cdft/SKILL.md` (different from orbital CDFT main menu 22) |
| conceptual DFT for a periodic solid via an embedded cluster | `references/conceptual-dft.md` + `tools/orca/references/running.md` (embedded-crystal section), with periodic VASP cross-checks |
| ORCA output as Multiwfn input (`.gbw` -> Molden) | `tools/orca/references/running.md` ("Wavefunction files for Multiwfn") |
| checking whether a Multiwfn result is usable | `references/validation.md` |
| bad input file, missing orbitals, cube/rendering problems, strange charges | `references/errors.md` |
| official manual, Sobereva tutorials, VMD/cube-related resources | `references/resources.md` |
| figure strategy and quality floor | `knowledge/scientific-visualization.md` |
| charge/bonding interpretation | `knowledge/electronic-structure.md`, `knowledge/bonding-analysis.md` |
| TD-DFT state interpretation | `knowledge/molecular-qc-practical-rules.md` and `tools/gaussian/references/td-dft.md` |

## Workflow

1. Validate the upstream calculation with the engine skill.
2. Convert/check the input file: Gaussian `.chk` -> `.fchk` with `formchk`; ORCA `.gbw` -> `.molden.input` with `orca_2mkl <job> -molden`.
3. Choose the narrow analysis path from `references/orbital-charge-spectra.md`, `references/running.md` or **`references/periodic-stockholder.md` for periodic VASP densities**.
4. Record menu path/options, file provenance, isovalues/cutoffs, grid settings, and state/orbital indices.
5. Interpret with the relevant `knowledge/` file; do not overclaim from a single population or picture.

**Scope note:** Multiwfn can compute ordinary Hirshfeld, CM5 and iterative
Hirshfeld-I from a compatible periodic CHGCAR. For DDEC6 net charges,
SBO and periodic pairwise DDEC6 BO retain **Chargemol**; Multiwfn does
not replace Chargemol's DDEC6 implementation. MBIS is intentionally
not added in this workflow. Never mix all-electron reconstructed
densities and VASP valence grids without reporting the distinction.

## Hard guardrails

- Mulliken charges are quick diagnostics, not robust evidence, especially with large/diffuse basis sets.
- A molecular orbital picture is not a population analysis; an isosurface is not a charge-transfer magnitude.
- NTOs are preferred over raw orbital-transition lists for mixed TD-DFT states.
- Every figure must record file source, isovalue/cutoff, sign/color convention, and state/orbital index.
- Do not use Multiwfn output to rescue an unconverged or wrong-state upstream calculation.
- Conceptual DFT: N, N+1 and N-1 at one geometry and one level **and one fixed external potential**; record whether the source is an isolated molecule or a crystal-embedded cluster. Always state the hardness convention and sign of vertical EA.
- Condensed Fukui requires one consistent population definition across all three electronic states. Conventional Hirshfeld is a reproducible baseline; Hirshfeld-I or other schemes are optional sensitivity checks, not interchangeable measurements. Do not assume the installed menu supports a scheme without checking its manual.
- Menu numbers, input-conversion commands and their output interpretation must be checked against the user's installed Multiwfn version before any batch scripting. The Skill is a documented procedure and checklists, **not** a tested wrapper for every Multiwfn function.
