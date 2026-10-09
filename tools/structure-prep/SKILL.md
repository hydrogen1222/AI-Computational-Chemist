---
name: structure-prep
description: Build and audit real atomistic structures from CIF/POSCAR/XYZ/PDB/SMILES and trusted sources: supercells, interfaces, slabs, terminations, defects, substitutions, adsorbates and molecular conformers.
---

# Atomic Structure Preparation

This skill provides practical building and geometry checking for **one
scientific modeling agent**. Use pymatgen/ASE for periodic structures and
RDKit for finite molecules. The user does **not** need to write code.

## Intake and construction

- Prefer user-supplied or project-local structures. If missing, use a
  documented source (e.g. MP database ID, article CIF, experiment) or mark
  a designed/reconstructed starting model as exploratory.
- Keep frozen originals and source identifiers. Record each transformation
  (cell matrix, Miller index/termination, vacancy or substitution indices,
  interface match, separation/vacuum, charge/spin).
- Enumerate meaningful inequivalent candidate sites when their choice could
  alter the scientific conclusion; do not select one without rationale.
- Write and **run** reproducible builder scripts where the environment permits;
  inspect real structures and output files. If unable to run, say so plainly.

## Routing

| Situation | Read / run |
|---|---|
| Source, convert, build, edit, and database access | `references/running.md` |
| Validate geometry after each transformation | `references/validation.md`; `scripts/audit_structure.py` |
| Scientific/model-adequacy critique | `references/model-review.md` |
| Build slabs and adsorbates | `scripts/make_slab.py`, `scripts/place_adsorbate.py` |
| Doping, substitution, vacancy, interstitial | `scripts/dope_structure.py` |
| Format conversion / SMILES to XYZ | `scripts/convert_structure.py`, `scripts/smiles_to_xyz.py` |
| Geometry or structure-generation failure | `references/errors.md` |
| Official databases and tool references | `references/resources.md` |

## Distinct checks

**Numerical:** intended formula/count, lattice/cell, symmetry tolerance,
unintended contacts (also across PBC), slabs/vacuum/layers/fixed flags,
periodic-image and adsorbate separations, correct atom/site indexing.

**Scientific:** phase and termination relevance, charge/spin/oxidation
chemistry, stoichiometry, model size/strain/sampling, and whether the
model genuinely tests the target mechanism. Passing one does not imply
passing the other.

A reviewer can be the same agent performing an explicit second reasoning
pass; no separate approval service or task state files are required.

## Output and permissions

Provide candidate CIF/POSCAR/XYZ files, source IDs, build scripts and a
compact model summary with actual checks and unresolved limitations. Keep
full audits as files if generated; avoid pasting huge neighbor lists.
Route optional computation-input preparation to the appropriate engine skill.
**Do not launch/monitor production calculations unless explicitly authorized.**
