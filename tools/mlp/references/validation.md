# Validating ML Potentials

> Load this when: deciding whether a non-DeePMD MLP is fit for its declared use, or
> choosing among pretrained (foundation) checkpoints. For
> DeePMD metrics, committee policy, and model-deviation thresholds, use
> `tools/deepmd/references/validation.md`.

## Evidence gates

1. **Held-out error:** report energy, force, and stress metrics relevant to the target
   use, plus parity/residual plots separated by system or composition. Thresholds are
   project- and chemistry-dependent; do not promote generic example values into a
   universal production bar.
2. **Physics checks:** compare relevant equation-of-state, structural, defect,
   adsorption, barrier, vibrational, or other observables against the labeling method.
3. **Dynamics checks:** test stability, conservation, and target state points using
   `tools/lammps/references/validation.md` or the deployment engine's validator.
4. **Distribution coverage:** demonstrate coverage of the intended compositions,
   temperatures, pressures, phases, defects, and reaction environments. Use a
   committee or architecture-specific uncertainty method when warranted.

Frames outside the demonstrated trust region are candidates for labeling, not
production evidence.

## Choosing among pretrained (foundation) models

Pretrained checkpoints are released faster than a project runs, so plan with a rule
and decide the files at run time.

1. **Candidates by rule, not by name.** For each model family the runtime supports,
   take the newest checkpoint (or head/branch of a multi-head model) trained on the same
   level of theory as the project's reference labels — PBE labels need PBE-trained
   heads, not r2SCAN ones. When a multi-head model has a head trained on the target
   chemistry (for example a solid-electrolyte head), include it as a separate
   candidate. Excluding a family needs a recorded reason, such as earlier tests on the
   same chemistry or a model that is too slow or does not fit in GPU memory.
2. **Freeze the reference set, not the candidate list.** The expensive and
   model-independent part is the DFT reference: sampled frames, single-point labels,
   and barrier paths. Store it once. Evaluating a newly released checkpoint is then only
   inference on the same set, so candidates can be added at any time.
3. **Pool the frames.** Sample configurations from more than one candidate's
   trajectories and evaluate every candidate on the same pooled frames. A model scored
   only on its own trajectory can hide its errors.
4. **Compare barriers, not only energies and forces.** Universal potentials can
   systematically soften the potential-energy surface and underestimate migration
   barriers (Deng et al., *npj Comput. Mater.* 2025; arXiv:2405.07105). Include at
   least one barrier path for each mechanism the production result depends on.
5. **Fix the model identity only on acceptance.** Once a model is accepted for a phase
   or use, production runs that exact file (hash), task/head, dtype, and inference
   mode. Any change means re-validating on the frozen reference set.

## Reporting

Record dataset size and coverage, split protocol, labeling fingerprint, model/checkpoint
identity, all validation metrics, physics tests, and the exact claimed domain. Never
quote training-set error as model quality or extrapolate a validation claim beyond the
tested domain.
