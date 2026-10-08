---
name: comp-chem-workflow
description: Entry point and controller for computational chemistry and materials workflows. Use when the agent must design, prepare, run, monitor, resume, validate, or report multi-stage atomistic work - DFT, quantum chemistry, MD, machine-learning potentials, phonons, HPC pipelines, benchmarks, reproductions, or literature/reviewer-derived calculations.
---

# Computational Chemistry Workflow Controller

Use this skill first for nontrivial computational work. It owns the **scientific
lifecycle, workflow compilation, and cross-engine validation discipline**. Durable
project state in this fork uses the two human-facing root documents and the detailed
records under `docs/`, as defined in `AGENTS.md`. Engine input/output details belong to the relevant tool skill and
scheduler operation to `hpc-submit`.

## Entry decision

| Starting point | Route |
|---|---|
| Scientific question or new calculation | Scope the full lifecycle below. |
| Existing inputs/run directory | Inspect in place, then use the producing engine skill and `hpc-submit` if execution is needed. |
| Existing outputs | Use the producing engine skill's parser and analysis guidance. |
| Third-party paper/SI/report | Start with `literature-to-calculation`. |
| Manuscript plus reviewer comments | Start with `review-response`; it invokes this procedure for approved calculations. |
| User supplies an existing workflow | Preserve its scientific intent, identify only the genuinely unresolved scientific choices, then compile it into user-readable work packages and executable calculation directories. |
| Multi-stage, HPC, resumable, or multi-owner project | Use the fixed project-root files in `AGENTS.md`; do not create `.research/`. |
| Existing job to resume or monitor | Reconcile durable state, scheduler state, logs, and parser verdicts; never resubmit blindly. |

## Human-first workflow compilation

For a new scientific project, do not jump from the user's first message directly to
input files.

1. **Task definition by SI.** Restate the scientific question in a few plain sentences,
   list what is already decided, and surface at most one scientifically consequential
   ambiguity at a time. Do not interrogate the user about routine engine details that
   can be derived from project conventions or tool guidance.
2. **Scientific roadmap by SI.** Break the task into a small number of scientific
   subquestions. Each roadmap item states what it is trying to learn, why it belongs
   at that point, and which earlier result it depends on. The roadmap stays
   code-independent.
3. **User approval.** The user sees and approves the scientific roadmap before major
   expands it into execution.
4. **Work packages by major.** Translate each approved roadmap item into a small number
   of coherent work packages. A work package is one human-meaningful unit even when it
   contains many cases, temperatures, configurations, or repeated calculations.
5. **Execution detail by major/vice.** Only after the work packages are approved should
   they be expanded into directories, scripts, submissions, monitoring, recovery, and
   parsing.

For each user-readable work package, keep the summary short and answer these fields in
plain scientific language:

- name;
- purpose;
- calculation objects;
- what we will know when it is finished;
- completion criterion;
- next scientific use.

Do not expose command-by-command execution detail in this summary. Low-level detail
belongs in the execution sheet and calculation directories.

## User-appointed major/vice execution boundary

The SI / major / vice terms are **roles**, not built-in agent primitives.
The user chooses the runtime and session for each role. For instance,
the user may run Codex as major and separately open dsh-tui as vice.
The two do not have to be children of one process, share a chat history,
or even use the same model.

**Major may prepare, verify, and document execution; major does not
self-authorize vice.** Do not call Codex's subagent/spawn tools,
start another agent session or autonomous job, or appoint a helper as
the vice executor without the user's explicit permission for this
handoff and runtime. An internal helper doing bounded drafting or code
review must not submit, monitor, cancel, or restart calculation jobs or
be described as vice. Do not silently substitute a different execution
platform if dsh-tui is the approved vice.

Record the user's project-specific runtime mapping in
`docs/reviewer_brief.md` (no tokens, API keys or secrets).
Major prepares `docs/execution_sheet.md` as a **portable handoff**,
naming the approved Work package, its complete self-contained
calculation directories and exact command/preflight/expected-output
paths, locked parameters, host/allocation constraints, permitted
automatic recovery, and the explicit stop point. The independent vice
reads the overview/status as context, the execution sheet as
instructions, the ledger as actual historical evidence, then
reconciles directories and scheduler state before running. It writes
actual execution facts into `docs/calculation_ledger.md`; major
synthesizes results for the human. Only the **user** starts the named
vice runtime and authorizes release of the Work.

If major and vice do not see an identical project path on the
target machine, include an explicit file-transfer/synchronization
plan. If the vice runtime, site configuration, or execution permission
is unresolved, stop at handoff: do not work around it by spawning an
unapproved agent or directly submitting jobs as major.

## Core decisions before input generation

Record:

- the scientific objective and falsifiable success criteria;
- a code-independent proposal for the calculations that answer it;
- model, method, reference states, assumptions, and explicit non-goals;
- the downstream code chosen from availability and group convention;
- execution target, approximate cost, and required approval.

Choose the science first and the engine second. Missing structures or incomplete source
methods change the route to a disclosed designed/reconstructed model; they do not
license invented inputs. Use `structure-prep` and, for surface/defect/adsorbate models,
the orchestrator's model-structure review. For an unresolved scientific fork with
material cost or interpretive impact, stop at the applicable approval breakpoint.

## Workflow

```text
intake -> scope and success criteria -> structure preparation -> method selection
  -> input generation -> preflight -> execution/monitoring/recovery
  -> parsing -> scientific validation -> evidence review
  -> accepted claim, explicit limitation, or follow-up task
```

Before every generated job, run the engine skill's prescribed input checks. Use
`hpc-submit` for submission/monitoring/recovery and the engine's exact-error guidance
for failures. On resume, continue from the earliest unfinished or unaccepted evidence,
not from chat memory.

## Validation and iteration

Report every result at its actual rung:

```text
files exist -> terminated normally -> technically converged -> scientifically valid
```

The engine parser/checker decides technical convergence. Scientific validation checks
that references and settings are comparable, magnitudes and structures are sane, and
the result still answers the registered objective. A converged number is not
automatically a valid or accepted claim.

After each coherent calculation wave, assemble evidence and classify the scientific
outcome as `addresses`, `contradicts`, `inconclusive`, or `needs-follow-up`.
Follow-up outcomes create new work; they are not repaired by drafting. Final reporting
uses accepted claims or visibly recorded limitations.

## Where to find what

| Situation | Open or run |
|---|---|
| Lifecycle states, validation ladder, comparison/reuse rules | `references/state-and-validation.md` |
| Structure building and numerical checks | `tools/structure-prep/SKILL.md` |
| Surface/defect/adsorbate model review checklist | `procedures/research-orchestrator/references/model-structure-review.md` (checklist only; no orchestrator state) |
| Engine inputs, validation, parsing, and exact failure recovery | the selected engine's `SKILL.md`, `references/running.md`, `references/validation.md`, and `references/errors.md` |
| Local/SSH/scheduler submission and monitoring | `tools/hpc-submit/SKILL.md` |
| Literature-derived targets and method evidence | `procedures/literature-to-calculation/SKILL.md` |
| Reviewer-comment planning and response semantics | `procedures/review-response/SKILL.md` |
| Interim synthesis and final deliverables | `tools/report/SKILL.md` and `tools/report/references/validation.md` |
| Scientific interpretation | the relevant flat `knowledge/*.md` reference |

## Scientific anomaly handoff to SI

When major encounters an unexpected result that needs scientific judgment, do not dump
the raw project tree into SI and do not pre-bias the review with a preferred scientific
interpretation. Give SI enough detail to independently check the issue:

- what happened, in plain scientific language;
- the exact calculation directory;
- the exact source file(s) for the reported numbers or structures;
- the comparison/reference case and its path;
- what is unusual relative to the other cases or the approved roadmap;
- the single scientific question SI needs to decide.

major may recommend an **execution action** such as pausing dependent calculations,
preserving a directory, or continuing unaffected work. It does not recommend the
scientific answer. SI interprets the evidence. If SI proposes a change to the approved
scope, method, cost, or scientific roadmap, the user approves it before major rewrites
the executable workflow.

## Work results, SI stage handoff, and revisions

The output of each Work package has two levels:

- Human: major rewrites its compact result summary in `01_project_status.md`. Include
  finished cases, key numbers with units and paths, the narrow result supported by
  those facts, limitations, open SI decisions, and what happens next.
- Detailed: vice/major retain per-calculation entries in `docs/calculation_ledger.md`,
  including actual inputs/outputs, check verdicts, job IDs, and all recovery attempts.

At a stage boundary, major writes one compact stage brief in
`docs/instructions_and_reports/`. It summarizes work packages, key numerical evidence
with source paths, anomalies, new decisions, and up to three independent scientific
questions for SI. Before handing a new SI session a snapshot, prepare
`docs/instructions_and_reports/SI_handoff_latest.zip` with the story, current human
status, relevant recent change-log entries, locks/glossary/reviewer brief, latest
stage brief, and only small key result tables/structures/figures. It is a reading set,
not a raw calculation backup, and must not contain POTCAR or giant outputs.

When SI changes the interpretation or proposes a new roadmap, major records which
old result is superseded rather than failed, retains old directories and evidence,
and waits for user approval before implementing changes to already approved scope,
method, cost, or locked parameters. After approval, update current narrative/status
and pending execution steps; append the exact decision/reason/approval to
`docs/change_log.md`. Do not overwrite old science as if it never happened.

New projects use the `docs/` paths. Existing projects keep their original layout
until a user-approved migration, to avoid silently breaking running workflows.

## Default stop at the end of each Work

This fork defaults to **user-reviewed Work boundaries**, even when more work packages
were approved at the roadmap-planning stage. The currently approved Work may run
its own batch of cases to completion. Then vice records the results and stops
dispatching any *new Work package*; it does not cancel running jobs or a user-owned
interactive allocation. major rewrites the concise Work result in
`01_project_status.md` and gives the user the immediate choice to continue with
the named next Work, request further verification, or refer a scientific anomaly to
SI. Give concrete directories, result paths, and allocation status. The next Work
may be fully prepared but stays unsubmitted until the user explicitly releases it.

Only an explicit, advance approval that names the Work packages to chain may waive
an intervening pause; merely approving the scientific roadmap is not enough.
If the user-owned allocation idles while waiting for review, report that fact and
time remaining but never cancel or replace the allocation.

## Root archive versus live data

`archive/` at the project root collects old or unadopted whole result sets only
after the user agrees to retire them. Keep active, approved and pending-review
calculations in their normal `calculations/` paths. Pending review is not a
rejection; a location outside `archive/` does not by itself prove scientific
acceptance. Distinguish this project archive from each active calculation's
`archive/` of failed restart attempts.

Before a move, major checks running jobs, next-Work dependencies, and source-path
references. On approval, preserve the retired inputs/outputs, record why the
material was retired and old/new paths in `docs/change_log.md` and
`docs/calculation_ledger.md`, update affected references, or postpone the move if
it would break current work. No unattended archival or deletion by vice.

## Workflow handoff

At a pause or handoff, keep two views separate.

The **user view** is short: current roadmap item, each work package as done/running/not
started, the key result paths, any scientifically important anomaly, and the next user
decision if one is needed. This view belongs in `01_project_status.md`. Runtime information such as job IDs or nodes may be shown
below this summary when useful, but it must not bury the scientific status.

The **agent view** records the execution facts needed to resume safely: what was
generated or run, file paths, job IDs, parser/checker verdicts, assumptions, fixes, and
the next executable action. This belongs in `docs/calculation_ledger.md` and `docs/execution_sheet.md`.

Every user-facing handoff ends with `接下来：` and a concrete action. State who acts
next, what they receive or inspect, and what they should do. For example, major names
the exact calculation directories and project files vice should execute; vice names
the ledger/results it returns to major; SI names the roadmap section major should
compile next.

## Hard guardrails

- Never skip structure, engine-input, parser, or scientific validation gates merely
  because a scheduler or executable reports success.
- Keep `completed`, `validated`, and `accepted` distinct.
- Do not promote smoke tests, unrelaxed models, failed runs, or exploratory assumptions
  into production conclusions.
- A `contradicts` result is surfaced with its evidence; it is never softened or hidden.
- Preserve commands, inputs, outputs, logs, units, and provenance for every reported
  quantity.
