---
name: deepmd
description: DeePMD-kit and Deep Potential Molecular Dynamics workflows. Use for dpdata dataset conversion from VASP/CP2K, DeepMD input.json setup, dp train/freeze/compress/test, DP descriptor PCA/t-SNE dataset-distribution visualization, DP model deviation, DPLibrary reuse checks, and LAMMPS DPMD deployment.
---

# DeePMD-kit / DPMD

## Required inputs

- Filtered, converged DFT/ab-initio labels with source-file provenance and one
  consistent method fingerprint.
- The production target: composition, phases, defects/interfaces, thermodynamic range,
  reactive/diffusive events, and required observables.
- Element order/`type_map`, dataset split policy, training resources, and deployment
  engine.

## Route map

| Need | Load or run |
|---|---|
| design/convert datasets, configure training, and deploy DPMD | `references/running.md` |
| decide model readiness, metrics, stability, and model-deviation use | `references/validation.md` |
| prepare training inputs and manual training commands | `references/running.md` |
| generate individual diagnostics or verify the QA package | `scripts/plot_deepmd_postprocess.py`; `scripts/deepmd_descriptor_pca.py`; `scripts/check_deepmd_qa.py` |
| map dataset coverage with DPA1/PCA/t-SNE | `references/dataset-embedding.md` |
| diagnose training, data, type-map, or MD failures | `references/errors.md` |
| draft manual training/deployment scripts | `references/running.md`; `tools/lammps/SKILL.md` |
| interpret MLP and MD results | `knowledge/machine-learning-potentials.md`; `knowledge/molecular-dynamics.md` |
| consult DeePMD/DP-GEN/DPLibrary resources | `references/resources.md` |

## Workflow

1. Define the production domain, assemble/filter labels according to
   `references/running.md`, and preserve the method fingerprint and type order.
2. Convert and split data, configure `input.json`, and hand the researcher
   explicit commands for manual training. Afterward, analyze the existing
   checkpoints and test results with the dedicated QA scripts.
3. Apply `references/validation.md` and `scripts/check_deepmd_qa.py`; expand data or
   revise one cause at a time when a gate fails.
4. Prepare a validated LAMMPS DPMD input and optional batch script. The
   researcher decides when to submit short validation and production runs.

## Hard guardrails

- Cover the intended composition, structures, volume/strain, temperature, and relevant
  events. Apply the dataset-size and high-temperature coverage policies in
  `references/running.md`; label smaller sets as pilot/non-production.
- Do not mix incompatible DFT labels in one dataset. Record functional, basis/ENCUT,
  k-point, U/spin, convergence, and potential-family choices.
- Treat `type_map` order as an interface contract across dpdata, the model, and LAMMPS.
- Validate outside training frames with held-out errors, learning curves, parity and
  coverage diagnostics, physics checks, and short MD stability tests. Embeddings alone
  are not validation.
- Do not release a model to DPMD or reporting until the fixed QA chain passes, or a
  visible waiver and limitation records every failed gate.
- Derive scientific observables only from equilibrated production trajectory segments.
