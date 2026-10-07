---
name: vasp
description: Prepare, validate, run, and troubleshoot VASP DFT calculations for periodic materials. Use for static SCF, ionic/cell relaxation, DOS, band structure, charge-density difference, Bader analysis, spin density, partial charge, ELF, work functions, magnetization, adsorption energies, vacancy formation, reaction energies, surface thermodynamics, surface reaction kinetics, electrocatalytic CHE step diagrams and surface Pourbaix diagrams, VASPsol/VASPsol++ implicit-solvent and constant-potential setup, vibrational frequencies, Wulff construction, free-energy corrections, AIMD/trajectory analysis/enhanced sampling, and VTST NEB/Dimer transition-state setup. (For LOBSTER COHP/COOP bonding analysis, the `lobster` skill drives the projection; VASP just provides the static wavefunction.)
---

# VASP

## Required inputs

- Structure (`POSCAR` or an accepted `structure-prep` artifact).
- POTCAR source and element-to-potential mapping, plus task, executable, and site
  convention.
- Method fingerprint: functional, ENCUT, k-policy, smearing, convergence, spin/U,
  dispersion/solvation, and task-specific settings.
- For reproductions, source settings and all known departures.

## Route map

| Need | Load or run |
|---|---|
| build static/relax/reaction inputs and choose global policies | `references/running.md` |
| preflight, parse, and judge convergence | `scripts/check_inputs.py`; `scripts/parse_vasp.py`; `references/validation.md` |
| fork checks: locked settings before submission, too-close atoms before and after relaxation, same settings before combining energies | `scripts/check_locked_params.py`; `scripts/check_distances.py`; `scripts/compare_settings.py`; `references/locked-parameters.md` |
| match crashes, warnings, or convergence failures | `references/errors.md` |
| DOS, bands, PDOS, and d-band analysis | `references/dos-band.md`; `tools/vaspkit/references/dos-band.md`; `knowledge/electronic-structure.md` |
| charge, Bader, spin, partial charge, work function, ELF, or fields | `references/electronic-analysis.md`; `references/volumetric-visualization.md`; `scripts/bader_summary.py`; `tools/vaspkit/references/electronic-analysis.md` |
| DFT+U and magnetism | `references/u-values-magmom.md`; `knowledge/hubbard-u-and-magnetism.md` |
| CI-NEB, Dimer, or IDPP | `references/vtst-neb-dimer.md` |
| electrochemical CHE/VASPsol/VASPsol++ | `references/electrochemistry.md`; `knowledge/electrochemistry.md`; `knowledge/thermochemistry-and-free-energy.md` |
| surface Pourbaix diagrams, dissolution, and phase-boundary audits | `knowledge/surface-pourbaix.md`; `references/electrochemistry.md`; `scripts/surface_pourbaix.py`; `examples/surface-pourbaix-audit/` |
| AIMD, enhanced sampling, and trajectory analysis | `references/aimd.md`; `knowledge/molecular-dynamics.md`; `tools/vaspkit/references/aimd-postprocessing.md` |
| surface thermodynamics, kinetics, and microkinetics | `knowledge/surface-thermodynamics.md`; `knowledge/reaction-kinetics.md`; `tools/vaspkit/references/thermochemistry.md`; `tools/catmap/SKILL.md` |
| GPU/OpenACC execution | `references/gpu-openacc.md`; `tools/hpc-submit/references/running.md` |
| COHP/COOP bonding | `tools/lobster/SKILL.md`; `knowledge/bonding-analysis.md` |
| scientific visualization or upstream documentation | `knowledge/scientific-visualization.md`; `references/resources.md` |

## Local, inspectable run directories

For this fork, a production VASP calculation should look like a calculation a human
researcher can inspect directly. Put the actual inputs used for the run in the run
directory itself: `POSCAR`, `INCAR`, `POTCAR`, an explicit `KPOINTS` when the chosen
k-point policy uses one, and the submission script. Do not replace these with symlinks
to shared templates or with settings that exist only inside a batch launcher.

Automation is encouraged when it removes repetition. A helper may create many complete
run directories in one pass. After generation, each directory must remain understandable
and runnable without reading the helper's source code.

When VASPKIT is installed and configured, prefer it for routine VASP input generation
and routine VASP post-processing. Generate files inside the target run directory, then
validate them here. VASPKIT's generated defaults are starting points, not method
authority; the approved method fingerprint and `locked_parameters.md` still control.

A locally generated licensed `POTCAR` may remain in the user's private run directory.
Never commit it, print its full contents, or include it in a public/shared handoff
archive. Record only allowed provenance such as potential labels, version/source path,
and hashes where appropriate.

## Workflow

1. Choose the task and load `references/running.md` plus the matching specialized
   reference before generating inputs. Record the full method fingerprint and source.
2. Run `uv run scripts/check_inputs.py` with the production policy in
   `references/validation.md`; resolve or explicitly waive every warning.
3. Execute through `hpc-submit`, preserving the exact inputs and runtime provenance.
4. Run `scripts/parse_vasp.py` and apply task-specific validation. On failure, match
   `references/errors.md`, change one cause, and rerun only with approval/ownership.

## Hard guardrails

- Check that POSCAR species order matches POTCAR; never invent potentials or print
  licensed POTCAR contents. Record only permitted provenance such as TITEL lines.
- Generate inputs from `references/running.md`, not memory. Record every departure from
  its numerical, physics, executable, or parallelization policy.
- No energy from an unconverged run enters any comparison or reaction expression.
- Keep every energy in one expression method-compatible: functional, potentials,
  ENCUT, k-density, convergence, spin/U, and relevant corrections.
- Slab, surface, adsorbate-on-surface, interface, and asymmetric 2D calculations
  use the symmetry policy in `references/running.md`; any enforced symmetry must be
  tested and recorded.
- Preserve `CONTCAR`, `OUTCAR`, `vasprun.xml`, and the actual `INCAR`, `KPOINTS`, and
  POTCAR provenance used.
