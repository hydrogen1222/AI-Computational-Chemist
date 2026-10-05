# Computational Chemistry — Agent Instructions

> **Fork override (takes precedence over everything below).** In this fork, `research-orchestrator` is disabled.
> - Never create or update a `.research/` directory, and never use its task DAG, gates, leases, claims, or heartbeats.
> - The project's own files in the project root are the only record of project state: the project overview, the execution sheet, the calculation ledger, and the change log. Where any skill below says to use `research-orchestrator`, `.research/`, a gate, a lease, or a claim, record the same information in those files instead, in plain language.
> - The execution sheet opens with a section *Next actions for the operator* — the human who runs things by hand, for example on machines where no agent can be installed. At most 8 lines: only the actions the operator must do personally, in order, as copy-pasteable commands. Each line names the machine it runs on and says in a few words what it does; never hide an upload, a download, or an environment choice inside an unexplained script, and when a tool has per-backend environments, write the backend-specific launcher instead of a bare command. Cover the whole loop the operator owns: what to copy where, how to start, how to tell it has finished, how to stop it, and what to bring back. Rewrite this section each round instead of appending to it. Helper scripts the operator runs take their inputs (paths, launchers, model files, choices) from a config file kept in the project, never from interactive prompts: provide a `check` step that validates the file before anything is submitted (paths exist, a single file where a file is expected and a directory where a directory is expected, recorded hashes match), and fail with a clear message on a missing or empty value instead of falling back to a default. When you hand back to the user, your reply is this section verbatim; everything else in the execution sheet stays written for agents.
> - **Stop points end the round.** When a step ends in a review (by the user or another reviewer), the operator section lists only the actions up to the hand-off; do not list later steps or prepare the next round until the review is answered.
> - **Transfers copy an explicit allowlist of project data** (inputs, outputs, logs, records), never virtual environments, caches, installed code, or model weights unless asked. A transfer script prints what it will copy and the total size before copying.
> - **Nothing the project needs later may live only in a conversation.** Sessions get compacted or replaced, and a summary drops details. Record each decision from the user or a reviewer in the change log before acting on it: date, who decided, what, and why, keeping the decider's reason in one or two sentences rather than only the outcome. Record measured numbers, workarounds, and tool behaviour you had to discover in the ledger or the change log when they happen, not at the end of the session.
> - **The calculation ledger opens with a *Status* section**, rewritten at every stop point and at most one page: the current step of the roadmap; what is finished, each with the path to its result; what is waiting for review, and by whom; the open questions; what is running on which machine and what is switched off; and the pitfalls met so far, one line each with its fix. The change log says why; the Status section says where things stand.
> - **Starting a new session.** A new session — yours, another agent's, or a reviewer's — reads the project overview, the change log (newest first), the ledger's Status section, and the table under review, in that order, and opens the execution sheet or older ledger rows only when needed. Its first reply restates in a few lines the current step, what is under review, and the open questions, so the user can confirm before any work continues. When a session's context has been compacted or is getting long, finish the round and continue in a new session at the stop point, not mid-round.
> - A reviewer who works in a separate chat keeps its own brief (roles, machines, how decisions are handed over) as a file in the project root. Agents read it and the project overview but do not edit either.
> - `procedures/research-orchestrator/references/model-structure-review.md` may still be read as a checklist for reviewing structures; it creates no state.
> - Every figure (plots, maps, structure images) follows `tools/plotting`: one folder per figure under the project's `figures/`, with copied data, `plot.py` and a README recipe. Where `knowledge/scientific-visualization.md` or the `report` figure rules differ (font size, panel assembly, colors), `plotting` wins.
> - Everything else in this collection (engine skills, `knowledge/`, error tables, validation rules) applies unchanged.

These rules apply to every computational chemistry and materials science task in this environment, regardless of which skill is active.

## Routing

Match the request against procedure skills in `procedures/` and engine/tool skills in `tools/`. For nontrivial work (multi-stage, HPC, resumable, benchmark, reproduction, or literature-derived), start with `comp-chem-workflow`; quick single-step tasks may go directly to the tool skill. Use `research-orchestrator` when work needs durable coordination across tasks, agents, sessions, jobs, reviewers, or reports. Its skill and references are the canonical source for project state, gates, leases, jobs, and recovery.

The flat `knowledge/` library covers scientific formalism, interpretation, and practice. Consult and adapt it as useful; it is not a skill and is never binding.

| Request | Skill |
|---|---|
| Manuscript + reviewer comments -> computational response package | `review-response` |
| Durable project state, task DAG, gates, artifacts, decisions/events | `research-orchestrator` |
| Multi-stage, HPC, resume, benchmark, reproduction | `comp-chem-workflow` |
| Extract a calculation from a third-party paper / SI / report | `literature-to-calculation` |
| Build/convert structures, slabs, supercells, defects, adsorbates, conformers, SMILES | `structure-prep` |
| VASP: static, relax, DOS/bands/charge, adsorption, reaction, NEB | `vasp` |
| CP2K: Quickstep GPW/GAPW, opt/cell-opt, MD/PIMD, DOS/bands/Molden/Multiwfn, DFT+U, hybrid/HFX, NEB | `cp2k` |
| Molecular QC: SP, opt, freq, thermochemistry, TS, IRC, solvent | `gaussian` |
| Molecular wavefunction analysis: fchk/wfn/molden/cube, charges, spin density, MOs/NTOs, spectra, ESP/ELF/NCI/IRI | `multiwfn` |
| GROMACS: biomolecular MD, protein-ligand, nucleic acids, membranes, water/solution/liquid/interface MD, MARTINI/coarse-grained systems, GROMACS FEP/pulling/analysis | `gromacs` |
| Classical / reactive / MLP-driven MD | `lammps` |
| DeePMD-kit / DPMD: dpdata, input.json, training, inference, model deviation, DPLibrary | `deepmd` |
| MLP method choice and cross-program concepts; MACE/NequIP/GPUMD/LASP/GemNet-OC/EquiformerV2 until split into dedicated tools | `mlp` |
| Phonons, force constants, thermal properties | `phonopy` |
| VASPKIT: VASP helper inputs, KPOINTS/band paths, DOS/band/charge/work-function post-processing | `vaspkit` |
| LOBSTER: COHP/COOP/ICOHP bonding analysis from a VASP wavefunction (projection, spilling checks) | `lobster` (science: `knowledge/bonding-analysis.md`) |
| Microkinetic modeling, CatMAP, TOF/coverage maps, volcano plots | `catmap` |
| Plots and figures: DOS, band structures, NEB barriers, RDF/MSD/Arrhenius, 2D maps, bar charts, figure folders, redrawing a figure | `plotting` |
| OVITO: atomistic rendering, structure classification, coordination/RDF, defect and trajectory analysis | `ovito` |
| Drive a *remote* machine over a persistent shell (stateful commands, HPC interaction from another machine; not when the agent already runs on the target) | `rsess` |
| Submit / monitor / recover jobs (local, SSH, Slurm, PBS) | `hpc-submit` |
| Compile results into a near-submission `.docx` report / response package (the default final deliverable) | `report` |
| Parse outputs, check convergence | the engine skill that produced them (each carries its parser) |

## Durable coordination

`research-orchestrator` is the project control plane, not a replacement for `comp-chem-workflow` or the engine/tool that performs the science. Follow `procedures/research-orchestrator/SKILL.md` and its references rather than duplicating its state schema here.

- Keep state and handoffs durable and auditable. Expensive execution has one active owner; long or costly work requires the orchestrator's lease/heartbeat and accepted-plan protocol.
- Do not collapse workflow states. `completed` means work finished, `validated` means required checks passed, and `accepted` means a human or authorized reviewer accepted the claim for downstream reporting. `report` consumes accepted claims by default.

## Use what's shipped before improvising

Before writing a helper, builder, parser, figure, or fix, search `procedures/`, `tools/`, and `knowledge/`, then open the relevant `SKILL.md` and its “Where to find what” references. Re-consult them at the moment of need, especially on failure.

| Moment | Open first |
|---|---|
| a run crashes, warns, or won't converge | the engine's `references/errors.md` — match the exact stdout/log string before changing any input; one fix at a time |
| about to write engine input files | the engine's `references/running.md` + `references/validation.md`; engine-specific settings live there |
| about to submit or monitor a job | the engine's `references/validation.md` + `hpc-submit` — "job left the queue" is **not** "converged"; gate on the parser |
| a charge, oxidation-state, or bonding claim is in scope | `knowledge/electronic-structure.md` (+ `bonding-analysis.md`) at *planning* time, not after the run |
| an electrocatalytic step (OER/ORR/HER/CO₂RR/NRR) is the question | `knowledge/electrochemistry.md` — the decisive observable is usually the **CHE ΔG step diagram / limiting potential**, not a bare adsorption energy; compute the diagram |
| building a slab, supercell, defect, or adsorbate | `tools/structure-prep` + `procedures/research-orchestrator/references/model-structure-review.md` — use builders, then literature/geometry critic gates before engine handoff |
| making figures or writing final results | `tools/plotting` first (style, figure folders, checks), then `ovito`, `multiwfn`, or `report` as needed |

References are starting points to adapt. Source methods and established group conventions take precedence over repository defaults.

## Lifecycle

```text
intake -> scope & success criteria -> structure prep -> method selection
  -> input generation -> preflight validation -> execution/submission
  -> monitoring & recovery -> parsing -> scientific validation -> record
```

Do not skip preflight or validation. Propose the scientific answer strategy first; choose the executing code afterward based on availability and user/group convention. The tool does not determine the science.

## Global guardrails

- **Never invent**: structures, coordinates, lattice vectors, pseudopotentials, basis sets, force fields, charge/spin states, Hubbard U values, training data, reference states, or convergence evidence. If a parameter is assumed rather than given or verified, label it as an assumption in the output.
- **Never claim production-quality conclusions** from smoke tests, unrelaxed structures, failed runs, or unconverged calculations. Distinguish technical convergence from scientific validity.
- **Literature-derived models are exploratory** unless the original structures and complete method details are available. Do not call a calculation a "reproduction" without them.
- **Bound structure discovery.** Check only the current project root/current working directory and user-explicit input paths. Never scan `$HOME`, `/home`, `/opt`, `/`, shared software trees, or unrelated storage for hidden inputs. Missing original coordinates or direct precedent is not itself a stop condition: use `structure-prep` to build a documented designed/reconstructed model from declared evidence, label it exploratory and record assumptions, then follow `model-structure-review.md` and the orchestrator gates.
- **Preserve provenance**: keep input files, generated files, commands, job IDs, logs, and parsed outputs. Never report a numeric value without file provenance and units.
- **Units**: eV, Å, fs/ps, K, GPa by default. When an engine uses different conventions (LAMMPS unit styles, GROMACS kJ/mol and nm, Gaussian Hartree), state the unit explicitly with every value.
- **Licensed data**: never print full POTCAR or licensed force-field/potential file contents; reference them by path and version.
- **Secrets**: never print, echo, log, or write API keys, tokens, or passwords — not to the terminal, reports, workflow files, job scripts, or commit messages. Let client libraries read them from the environment (for example `MP_API_KEY` for `mp_api.client.MPRester`), and check presence without revealing the value (`[ -n "$MP_API_KEY" ] && echo set`). If a secret has appeared in any output, tell the user so they can rotate it.
- **Defaults are not endorsements**: numerical settings and templates in `tools/*/references/` are community starting points. Source settings or established group conventions win when reproducing or following them.

## Operation mode: semi-automatic by default, autonomous on request

**Default = semi-automatic.** Pause at the workflow's approval breakpoints (e.g. `review-response` Approval #1 plan / #2 package) and present a recommendation; a `contradicts` result halts and is surfaced to the user before any further commitment. These human gates are the point — do not skip them unless the operator opts out.

**Autonomous / unattended mode** applies only when the operator explicitly requests it (no interactive user — e.g. a batch run that must finish on its own). It changes *when you ask*, never *whether you're honest*:

- **Approval gates → documented defaults.** Where the workflow would pause for approval, instead make the most defensible choice from `knowledge/` + field convention, record it as a labeled assumption/decision in the workflow state, and continue. Prefer the smallest credible calculation.
- **`contradicts` → flag, don't block.** A result that undermines a manuscript claim is not a stop-and-wait: record it with full prominence as its own clearly flagged finding in the deliverable and run to completion. Never spin, soften, or bury it.
- **Everything else holds unchanged**: never invent parameters; label every assumption and exploratory result; preserve provenance; the deliverable is still a draft and nothing is sent anywhere.

## Site environment (clusters, servers, local conventions)

This collection is environment-agnostic: never assume a cluster, hostname, scheduler, partition, module, account, or path.

- If already on the target machine, work locally; read its MOTD and `~/.cluster-agents.md`.
- For a remote target, connection and transfer bootstrap facts live outside this repo. Never guess or reuse another user's details; ask if they are missing. After login, read the MOTD and then `~/.cluster-agents.md`.
- On conflict, the user's `~/.cluster-agents.md` wins over MOTD-linked generic guidance. Note consequential discrepancies.
- If the guide is absent, probe or ask for site facts, then offer `tools/hpc-submit/references/cluster-guide-template.md`. Keep durable connection facts in the local bootstrap and operating facts in the remote guide. Keep secrets out of both and out of the repository.
- Follow the site guide and each tool skill for interpreter, environment, dependency, cache, and mirror details; do not downgrade repository scripts for an old system interpreter.

## Approval breakpoints

Stop and ask the user before:

- submitting long or expensive HPC jobs (unless already approved for this batch)
- overwriting existing calculation directories or source data
- deleting files
- choosing among multiple scientifically plausible models, references, or methods
- promoting exploratory results into manuscript or reviewer-response conclusions

## When information is missing

If a required scientific choice cannot be inferred from files or source evidence, ask **one focused question** for the smallest missing input. Do not stack questions or guess silently.
