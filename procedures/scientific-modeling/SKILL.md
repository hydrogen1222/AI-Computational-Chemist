---
name: scientific-modeling
description: Use when a computational chemistry or materials research question needs physical-model selection, atomistic structure construction, competing model comparison, validation, or a reproducible candidate model package. One agent designs and builds; HPC execution is optional and user-authorized.
---

# Scientific Modeling — from question to defensible atomistic model

This is the **primary AICC skill**, usable by one coding-capable agent.
The user need not know ASE, pymatgen or Python. The goal is not to fill a
workflow dashboard: it is to produce scientifically meaningful, real structures
with an honest account of what they can test.

## 1. Clarify what is being modeled

Begin with the intended physical process and **observable** (thermodynamic
preference, local bonding, redox, migration barrier, interface reconstruction,
transport, spectra, etc.). Separate:

- **Physical representation:** bulk vs slab vs finite cluster vs explicit
  interface vs defect/insertion vs reactive trajectory, reservoirs, boundary
  conditions, charge/electron treatment, timescale.
- **Atomistic representation:** phase, cell, facet/termination, disorder,
  site, coverage, concentration, orientations and configurations.
- **Numerical approach:** DFT/MD/ML potential, reference energies, pathway
  search, sampling and comparisons.

A good-looking optimized geometry does **not** establish that the physical
representation answers the question. If the user's question is underspecified,
propose a small, contrasted set of defensible models with a reason for each;
ask for a decision only when different assumptions materially change the
science or resources. Use literature/database evidence, distinguish direct
sources from analogy, and label unsupported choices exploratory. Do not
manufacture papers, structures or experimental observations.

## 2. Compare before building

For each worthwhile candidate, briefly state:

1. Scientific hypothesis and discriminating observable.
2. Physical approximation and alternative(s) it excludes.
3. Starting structure source, phase/termination/defect/charge/spin choices.
4. Main confounders (finite size, reconstruction, polar/charged cells,
   artificial strain, reservoir consistency, starting-geometry bias).
5. Minimum set of controls/comparisons and expected calculation expense.

Prefer **a small set of informative candidates** over hundreds of redundant
geometries. Enumerate ambiguous, inequivalent sites when the scientific
conclusion is sensitive to them, rather than selecting a convenient site
silently.

For example, Na-metal reduction of Na3PS4 can motivate bulk reaction
thermodynamics, Na insertion/defect models, or an explicit Na/Na3PS4
interface. These answer different questions; a single isolated Na insertion
cannot by itself demonstrate interface kinetics or an SEI mechanism.

Use `knowledge/periodic-dft-modeling.md`, `knowledge/periodic-electrostatics.md`,
`knowledge/surface-thermodynamics.md` and other relevant scientific references
as appropriate. For published targets, first consult
`procedures/literature-to-calculation/`.

## 3. Build actual structures

Load `tools/structure-prep/SKILL.md`. Inspect user-supplied/project-local inputs
first; obtain database/literature structures with stable identifiers, retain
frozen originals and record provenance. Implement transformations with appropriate
available software (pymatgen/ASE for periodic structures, RDKit for molecules).
Use the shipped scripts where they fit; if they do not, write a small documented
builder instead of requiring the user to write or debug code.

Record the transformation chain and parameters (e.g. supercell matrix,
Miller index, termination choice, vacuum, atom/site indices, coordinate
convention, interfacial match strain, seeds for stochastic generation).
Create actual candidate CIF/POSCAR/XYZ files, inspect them, and keep an
executable build script. **Never claim to have generated or validated files
if the runtime could not run the builder.** In that case deliver the code,
state exactly what is untested, and do not present model candidates as real.

## 4. Criticize in two independent ways

**Geometry/numerical audit:** composition, atom count, lattice and symmetry
tolerance, vacuum/orientation, unintended contacts including periodic images,
selective dynamics, nearest adsorbate/defect-image separation, geometric
consistency after conversion. Run the deterministic audit in `structure-prep`
where supported.

**Scientific-model audit:** physical correspondence to the question;
phase/termination precedent, charge/spin and stoichiometry, reservoirs,
polar/asymmetric surfaces, interface strain, finite-size/coverage bias,
symmetry-equivalence of candidates, control calculations and alternative
interpretations. Read `tools/structure-prep/references/model-review.md`.
A numerically passing geometry may still be a scientifically misleading model.
A niche exploratory model with no direct literature precedent may still be
worth building if assumptions and limitations are honest.

Revise the model when checks fail; otherwise record unresolved warnings and
what comparisons could resolve them. No machine-readable approval gate,
lease or second agent is required.

## 5. Deliver a compact, reproducible model package

Reuse existing project documentation if present. For a new standalone project
`models/model.md` plus `models/source/`, `models/candidates/`, and
`models/scripts/` are a suggested minimal layout, not a mandated schema.
The human-facing report should give:

- the scientific question and why the chosen models differ;
- a candidate-to-file table, provenance, and relevant dimensions/counts;
- exact builder command/configuration and actual validation commands/outcomes;
- warnings, assumptions, rejected possibilities, and limits on the claims;
- the *next scientific decision*, not a Slurm job plan.

An actual structure/model package is the default deliverable. On explicit
request, also prepare engine input files using the corresponding tool skill.
**Do not submit, monitor, restart or cancel production simulations without
a separate user authorization** for those operations. Standalone analysis
of already available outputs may use engine parsers on request.

## Routing

| Need | Load |
|---|---|
| Construct, enumerate, convert, inspect geometry | `tools/structure-prep/SKILL.md` |
| Human scientific model audit | `tools/structure-prep/references/model-review.md` |
| VASP/CP2K/ORCA/Gaussian/etc. input methods | respective `tools/<engine>/SKILL.md` |
| Published paper to model requirements | `procedures/literature-to-calculation/SKILL.md` |
| Electron structure, surfaces, MD, thermodynamics | relevant `knowledge/` entry |
| Batch post-processing of many completed simulations | `procedures/batch-postprocessing/SKILL.md` |
| Optional authorized cluster execution | `tools/hpc-submit/SKILL.md` |
