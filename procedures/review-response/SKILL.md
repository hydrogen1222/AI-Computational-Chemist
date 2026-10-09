---
name: review-response
description: Help an author triage computational reviewer comments, design defensible modeling/analysis to address them, evaluate evidence, and draft an honest response; execution remains optional and authorized by the user.
---

# Computational Peer-Review Response

This is an **optional, single-agent** procedure, not an orchestration service.
Use for manuscript + reviewer comments, not for ordinary modeling questions.
The author's scientific judgment and manuscript strategy remain authoritative.

## Intake and method baseline

Read the manuscript, SI, reviewer reports and any original inputs/outputs.
Identify reviewer comments with stable IDs and locate source passages.
Establish a method fingerprint, distinguishing verified settings from gaps:
structures, phases, charges, sampling, reference states, functionals,
basis/pseudopotentials, corrections, software and convergence criteria.
A designed model for a purely experimental manuscript is **exploratory**
unless validated against relevant evidence. Never claim byte-identical
reproduction from an incomplete source.

## Triage before computing

For each comment distinguish `compute-new`, `reanalyze`,
`method-challenge`, `add-figure`, `text-only`, or
`needs-human-decision`. State:

- the exact concern and **direct observable** that would address it;
- evidence already available versus missing work and suitable controls;
- whether a cheaper proxy answers a *different* question;
- model choices, methods, scope/cost and consequences for the manuscript.

Present a coherent plan for author approval before any expensive calculation.
For modeling tasks, use `scientific-modeling`; for source extraction,
`literature-to-calculation`; for engine details, the corresponding tool
skill. **No task DAG or project state machine is required.**

## Assess and draft

Check technical convergence separately from scientific relevance.
Classify each claim as `addresses`, `contradicts`, `inconclusive`,
or `needs-follow-up`. Never bury contradictory results or reinterpret
an exploratory calculation as direct experimental confirmation.
When evidence challenges a manuscript claim, show it to the author and
offer defensible revisions. The response letter/SI package is an **author
draft**; do not submit it to a journal.

Preserve source paths, units, method differences, figures and limitations.
Use the existing references in this procedure for comment taxonomy,
ingestion and response text, loaded only as needed. Prefer reusing existing
manuscript/project documents over creating additional administration files.
Do not submit jobs without specific authorization.

## References

- `references/comment-taxonomy.md` — comment classes and required evidence.
- `references/ingestion.md` — extracting manuscript/SI/reviewer evidence.
- `references/response-templates.md` — optional response structures.
- `references/response-package.md` — drafting the response.
- `procedures/scientific-modeling/SKILL.md` — model design and validation.
- `tools/structure-prep/SKILL.md` — actual structure construction.
