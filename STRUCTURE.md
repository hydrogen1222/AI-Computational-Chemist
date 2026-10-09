# AICC Repository Structure

This repository provides **one agent with modular, on-demand skills**. The
researcher runs and monitors production calculations. There is no scheduler
service or mandatory project document protocol.

- `procedures/`: scientific tasks that combine reasoning and tools. The default
  entry is `scientific-modeling`; literature extraction and reviewer response
  are optional.
- `tools/`: engine- or operation-specific help (structure preparation, VASP,
  CP2K, ORCA, analysis, visualization, optional HPC submission).
- `knowledge/`: scientific background that survives switching codes; references,
  **not** separate agents or executable skills.
- `procedures/batch-postprocessing/`: an optional one-agent workflow for
  analyzing many finished calculations with existing tool skills.
- `benchmark/`: standalone evaluation archive, not default agent context.
- `aicc/`: optional local skill discovery/install diagnostics CLI.

Each installed skill has `SKILL.md` with a short trigger and routing map. Load
only relevant `references/` for the current task; call `scripts/` when a
repeatable builder or checker is needed. Existing directory conventions for
individual tool skills (running/validation/errors/resources) still apply.

## One-agent scientific modeling

```text
question -> physical model options -> user decision on material choices
         -> atomistic generation -> deterministic geometry audit
         -> scientific model criticism -> deliver structure + build script
                                      -> user submits simulations manually
                                      -> agent analyzes existing outputs
```

Model criticism is a reasoning pass performed by the working agent.
The researcher can seek independent scientific review outside AICC.

## Files for a new standalone modeling task

Keep the user's existing layout if present. Otherwise this is a *suggested*
minimal layout, not a required scaffold:

```text
models/
  model.md            # short rationale, assumptions, candidate table, checks, limitations
  source/             # frozen input structures and source IDs
  candidates/         # actual CIF/POSCAR/XYZ files
  scripts/            # reproducible builders and required parameters
```

Add files only when they hold real scientific information or reproducibility
evidence. Do not auto-create `00_project_overview.md`, `01_project_status.md`,
multiple work ledgers, review briefs, glossary files or `.research/`.

## Contributions

- Extend `knowledge/` for code-independent modeling physics and interpretations.
- Extend `tools/structure-prep/` for geometry builders and deterministic audits.
- Extend other engine skills for exact syntax, checks, and failure recovery.
- Put decisive scientific/model-choice guidance in
  `procedures/scientific-modeling/SKILL.md`; link rather than copying technical
  tutorials or requiring extra workflow machinery.
- Verify real outputs, edge cases and non-destructive behavior. Cite reference
  sources where decisions depend on empirical or published evidence.
