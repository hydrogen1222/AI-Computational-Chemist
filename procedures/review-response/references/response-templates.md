# Optional Reviewer-Response Templates

> Load this when: a manuscript + reviewer comments need an optional method
> fingerprint or compact reviewer-comment status table. Do not create these
> files for unrelated scientific modeling.

There is no mandatory `.research/` state or project DAG. Reuse an existing
manuscript/project record when possible. If author coordination benefits from
a separate table, the following formats are examples, **not schemas**.

## Method fingerprint

```markdown
# Method fingerprint
- source: manuscript / supplementary information / original input files
- origin: manuscript-derived | literature-derived | designed | mixed
- status: reproduction | reconstruction | exploration

| Setting or model choice | Value | Verified source or assumption |
|---|---|---|
| Structure / phase / termination | ... | DOI, entry ID or chosen hypothesis |
| Functional / pseudopotential / cutoff / k mesh | ... | original input or source |
| Reference states and corrections | ... | ... |
| Sampling / coverage / spin | ... | ... |

- Comparisons requiring matched settings: ...
- Unresolved inputs or methodological changes: ...
```

An exploratory or reconstructed structure cannot be claimed as an exact
reproduction. Disclose substantive method deviations, especially for
comparative energies and barriers.

## Comment triage

```markdown
| ID | Reviewer concern | Required observable | Route | Evidence/status |
|---|---|---|---|---|
| R1.C2 | ... | ... | compute-new / reanalyze / method-challenge / add-figure / text-only | ... |
```

When a proxy answers only an adjacent question, mark it explicitly.
Request author input for scientifically consequential ambiguity, method
changes, optional expensive computation and contradictions.

## Optional one-page scoreboard

```markdown
| Comment | Status | Scientific outcome | Supporting file | Next step |
|---|---|---|---|---|
| R1.C2 | planned / running / reviewed | addresses / contradicts / inconclusive / needs-follow-up | path | ... |
```

The scoreboard is a human-readable aid, not another task database.
Convergence is not evidence of scientific relevance. Contradictions
must be prominent in the actual author response. Final text is
an author-approved draft; do not submit anything to a journal.
