---
name: literature-to-calculation
description: Extract the physical models, structure sources, methods, comparators, and missing reproduction information from a paper, SI or report, then hand a defensible model target to scientific-modeling.
---

# Literature to Scientific Model

Use for published methods, supporting information, calculation figures,
reviewer materials or a third-party report. This skill extracts **evidence
and assumptions**, not a project task database.

## Extract precisely

For each proposed model/observable, establish:

1. Source identity (title/DOI/arXiv if available) and exact figure/table/page.
2. Scientific claim or hypothesis; the **observable** used to support it.
3. System representation: phase, bulk/surface/interface, chemical environment,
   composition, defect/adsorbate, charge/spin, temperature and boundary conditions.
4. Structure provenance: original coordinates/data ID vs described but missing
   geometry; symmetry, surface termination, cell size and inequivalent sites.
5. Method/source details: code/version, XC functional, basis/PAW, U/vdW,
   cutoff, k-mesh, relax constraints, reference states and corrections.
6. Comparator (published trend/number/experiment) including units, sign
   convention and what remains genuinely unverified.
7. Which details block **exact reproduction**, versus which could support a
   deliberately designed *exploratory* analog.

When original structures or method details are missing, **do not make them up
or claim reproduction**. Offer bounded reconstruction options, preserve the
source and label the assumptions. First inspect user-supplied/project-local
files; search public sources when useful and available.

## Handoff

Return a compact human-readable evidence summary and candidate model
specification. Use `procedures/scientific-modeling/SKILL.md` for evaluating
alternative physical models, `tools/structure-prep/SKILL.md` for actual
structure construction, and the relevant engine skills for method syntax.

Reuse a pre-existing project file, or place the evidence directly in
`models/model.md`; do not create `.research/`, artifact registries,
mandatory YAML state, duplicate root reports, or role handoff packages.
