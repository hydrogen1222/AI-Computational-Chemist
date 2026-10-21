---
name: mlp
description: Machine-learning interatomic potentials other than DeePMD (MACE and foundation/pretrained models, NequIP, NEP and others) — method choice, dataset contracts, fine-tuning, validation and active learning. DeePMD-kit operation lives in `deepmd`.
---

# Machine-Learning Potentials

Method choice and validation for any MLP, plus operating notes for MACE and pretrained models. DeePMD-kit lives in `tools/deepmd`; MD deployment in `tools/lammps`; DFT labels in `tools/vasp` or `tools/cp2k`; the science in `knowledge/machine-learning-potentials.md`.

## Where to find what

| Situation | Go to |
|---|---|
| DeePMD-kit/DPMD dataset prep, `input.json`, `dp train/freeze/test`, model deviation | `tools/deepmd/` |
| general MLP concepts, dataset design, symmetry/equivariance, program taxonomy | `knowledge/machine-learning-potentials.md` |
| dataset contracts, MACE training/fine-tuning, deployment, active-learning loop | `references/running.md` |
| is this model production-ready? held-out errors, physics checks, distribution coverage | `references/validation.md` |
| which pretrained/foundation checkpoint to use; adding a newly released model | `references/validation.md` ("Choosing among pretrained models") |
| generic training failures or MACE fine-tuning problems | `references/errors.md` |
| external documentation for programs not covered by a dedicated tool skill | `references/resources.md` |

## Hard guardrails

- Only converged DFT frames become labels; one dataset = one method fingerprint (no mixed settings).
- Model quality is quoted from held-out data only — never training-set error.
- A potential is valid only inside its demonstrated distribution. Use the
  architecture-appropriate uncertainty or committee check when the risk or workflow
  requires it; out-of-range frames are retraining candidates, not production evidence.
- Per-iteration provenance: dataset paths/hash, config, seeds, checkpoint, test metrics.
