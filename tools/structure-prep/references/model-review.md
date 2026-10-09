# Scientific Model Review (One-Agent Checklist)

> Load this when: checking whether an atomistic model is scientifically justified,
> not merely geometrically valid. One agent may build and independently critique
> its own candidate; a separate reviewer is optional, not required.

## Question-to-model correspondence

- Name the specific hypothesis, target observable and strongest competing
  interpretation. Does the model contain the physics needed to discriminate?
  For instance, a bulk interstitial may probe insertion but not the kinetics
  of an explicit metal/electrolyte interface.
- State what is fixed or neglected: environment, reservoirs, pressure/temperature,
  electric field, charge compensation, timescale, solvent, amorphous disorder.
- For a literature reproduction, identify original structures/method details.
  If absent, label the model reconstructed or exploratory.

## Candidate selection and provenance

- Identify the original source files and database release/entry IDs.
- Check polymorph, orientation, symmetry tolerance, defect/adsorbate sites,
  charge/multiplicity or magnetic order. Why were some candidates excluded?
- For surfaces: facet precedent, Miller index, exposed terminations, top/bottom
  chemistry, polar or asymmetric slabs and possible dipole effects.
- For metal/electrolyte interfaces: both phases, facets/terminations, chosen
  alignment, commensuration strain of **each** side, interface separation,
  periodic replicas and possible artificial reconstructions.
- For defects/disorder: supercell, distinct sites, charge compensation,
  concentration, local environments, number of configurations and sampling bias.

## Geometry and computational economy

Inspect the deterministic output from
`tools/structure-prep/scripts/audit_structure.py` where applicable.
Verify composition, cell vectors, vacuum, distances including PBC images,
fixed layers, intended anchors, minimum image separations and atom counts.
Distance heuristics are **screens**, not universal chemical bonding laws;
justify exceptional bonds, constrained intermediates, and short contacts.

Check cell/slab thickness, lateral size, adsorption coverage, defect images,
strain and costly excess vacuum. Demand convergence/controls when a
scientific claim is sensitive to finite size or model choice, not an
universal atom-count or vacuum cutoff.

## Outcome

Write a *short* note in the existing model report:

- **Usable:** adequate for the stated bounded question (not every question).
- **Revise:** specify the next change and why.
- **Exploratory/limited:** may be built and investigated, but flag missing
  precedent, model bias or lack of physical correspondence.
- **Invalid:** unphysical or inconsistent without a defensible hypothesis.

Report the model files and full audit paths, the decisive checks, unresolved
alternatives, and claims that **cannot** be made from this model. A geometry
checker alone cannot approve a scientific interpretation. No task database or artificial approval report is necessary.
