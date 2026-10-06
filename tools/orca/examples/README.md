# ORCA examples

Verified examples only: each was actually run, and its README records the ORCA version, date and
machine. An unverified example is worse than none, because agents copy examples with full confidence.

Each example directory holds the `.inp`, a `README.md`, and an `expected-output.md` with the parsed
summary and short output excerpts (never whole outputs, never `.gbw` files).

Per-example `README.md` template:

```markdown
# <name>
Demonstrates: <what question this answers>
Expected result: <the number or behavior, with units>
Runtime: <walltime on what resources>
Verified: <ORCA version, date, machine>
Adapt by changing: <the lines someone edits for their system>
```
