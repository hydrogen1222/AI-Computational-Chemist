# review-response examples

Small, scientific reviewer-response examples using locally reproducible
ASE-EMT toy calculations. They demonstrate method consistency, evidence
assessment and honest reporting without project state machines.

**Privacy:** examples use fabricated manuscripts and reviewer reports only. Never
place a real manuscript, real reviewer text, or real engagement details here.

**Each example contains:** the fake `inputs/` (manuscript + reviews), the artifacts
of the analysis steps (`method-fingerprint.md`, `triage.md`),
the verified calculation `scripts/`, and an `expected-output.md` (trimmed numbers +
pass criteria, never bulky raw output). A run that validates ends in a drafted
`response-package.md`; a run whose result *contradicts* a manuscript claim halts at
evidence review and ends in an `escalation.md` rather than a misleading response. The
per-example `README.md` states what it demonstrates, the expected result, runtime,
and what to adapt for a real case.

## Cases

| Case | Mode | Demonstrates | Compute |
|---|---|---|---|
| `toy-vacancy-pt-vs-au/` | designed (B) | full Phase 0–5 flow incl. all three triage classes and the `addresses` outcome | ASE-EMT, ~5 s, local |
| `toy-contradicts-au-vs-cu/` | designed (B) | the `contradicts` integrity branch: result undermines the claim → halt at Phase 4, `escalation.md` instead of a package | ASE-EMT, ~5 s, local |
