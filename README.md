# AI Computational Chemist (AICC)

**From scientific questions to defensible atomistic models.**

AICC is a **single-agent, modeling-first** collection of skills for computational
chemistry and materials science. It helps a researcher who has a scientific question
but may not know which physical model to use, or how to program ASE/pymatgen, turn
the question into real, reproducible atomistic structures.

The user owns scientific approval and decides whether or when to run expensive
calculations. This collection **does not** launch a built-in SI/Major/Vice team,
operate a task DAG, or run HPC jobs by default.

## Typical use

1. **Reason** about the question, mechanism and target observable; distinguish
   physical assumptions from choices of geometry and numerical method.
2. **Compare** plausible models and literature evidence; flag exploratory assumptions
   rather than silently promoting them to reproduction.
3. **Build** structures by writing and running ASE/pymatgen/RDKit scripts. Users
   do not need to supply Python code.
4. **Critique** source provenance, charge/stoichiometry, cell/surface/termination,
   strain, finite-size effects, unintended contacts, and observable validity.
5. **Deliver** original source structures, candidate CIF/POSCAR/XYZ files,
   reproducible scripts and a concise scientific model review. Submission is optional.

For example: "I want to understand Na-metal reduction of tetragonal Na3PS4.
Compare bulk insertion and explicit metal-interface models, explain their
limitations, then build and audit the candidate structures. Do not submit VASP."

## Layout

| Path | Purpose |
|---|---|
| `AGENTS.md` | Short, harness-neutral single-agent contract |
| `procedures/scientific-modeling/` | Main modeling workflow |
| `procedures/literature-to-calculation/` | Extract evidence and model choices from publications |
| `procedures/review-response/` | Optional manuscript reviewer-response workflow |
| `tools/structure-prep/` | ASE/pymatgen/RDKit structure building, enumeration, audits |
| `tools/vasp/`, `tools/cp2k/`, `tools/orca/`, etc. | Per-code methods, preflight, parsers, troubleshooting |
| `tools/hpc-submit/`, `tools/rsess/` | Optional, explicitly authorized execution support |
| `knowledge/` | Tool-agnostic science and methods; loaded selectively |
| `benchmark/` | Separate historical benchmark/evaluation materials |
| `aicc/` | Optional installation/skill-discovery CLI; no task or job manager |

Structure checks are deterministic where possible; scientific adequacy still
requires reasoning. Model selection is not a magic algorithm or a substitute
for evidence from experiments and literature.

## Installation

From this checkout:

```bash
./install.sh --target ~/.codex/skills
# Or:
./install.sh --target ~/.claude/skills --harness claude --project /path/to/project
```

See `./install.sh --help` for supported harnesses, local installation and
`--force` refreshes. AICC installs instructions and scripts, **not** VASP,
CP2K, RDKit, ASE, pymatgen, scheduler environments or licensed files. Helpers
with PEP 723 metadata use `uv run path/to/script.py ...` when dependencies are
needed.

Optional CLI:

```bash
aicc skill --help
aicc doctor
```

The obsolete `aicc status/task/job` and `.research/` orchestration features
were removed. If updating an existing installation, old skill links may
remain; inspect and remove retired AICC-owned links or use the CLI's explicit
stale-link cleanup option, without touching foreign skills. **Existing projects
are not automatically migrated or deleted.**

## Design principles

- **One agent, multiple on-demand skills.** Use a capable interactive or coding
  model; no mandatory subagents, leases, approval gates or role-specific sessions.
- **Physical model before input syntax.** Different scientific questions require
  different representations; one good POSCAR cannot prove the chosen physics.
- **Actual model files, not only advice.** Keep sources and transformations so
  another person can regenerate candidate structures.
- **Scientific skepticism.** Check both geometry and whether the chosen system
  can test the stated mechanism; describe competing models and confounders.
- **User-controlled execution.** Running simulations or changing approved
  methods/resources requires authorization; creating and auditing structures
  does not imply approval to submit.

For directory and reference conventions see [STRUCTURE.md](STRUCTURE.md).
For license and citation see [LICENSE](LICENSE) and [CITATION.cff](CITATION.cff).
