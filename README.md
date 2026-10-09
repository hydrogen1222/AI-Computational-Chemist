# AI Computational Chemist (AICC)

**From scientific questions to defensible atomistic models.**

AICC is a **single-agent, modeling-first** collection of skills for computational
chemistry and materials science. It helps a researcher who has a scientific question
but may not know which physical model to use, or how to program ASE/pymatgen, turn
the question into real, reproducible atomistic structures.

AICC also provides **batch post-processing** for previously calculated datasets:
identify the requested observable, invoke the relevant program/skill on many run
folders, check missing or invalid cases, and produce comparable tabular results.
The user should not need to write shell loops, Python scripts, or hunt
down installed Chargemol/Bader executables by hand. AICC searches the
current PATH and common user/application directories first and asks
for a path only if discovery is impossible or ambiguous.

The researcher decides what to calculate and manually submits, monitors and
restarts production jobs. AICC prepares inspectable inputs and optional manual
job scripts but does not operate schedulers or remote job sessions.

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
| `procedures/batch-postprocessing/` | Batch analysis of existing calculations without manual scripts |
| `tools/chargemol/` | DDEC6 charges, SBO, all printed periodic bond types, and paginated PPT-ready plots |
| `tools/vasp/scripts/batch_bader.py` | Batch VASP Bader/AIM charges, per-atom and per-element CSV |
| `procedures/review-response/` | Optional manuscript reviewer-response workflow |
| `tools/structure-prep/` | ASE/pymatgen/RDKit structure building, enumeration, audits |
| `tools/vasp/`, `tools/cp2k/`, `tools/orca/`, etc. | Per-code methods, preflight, parsers, troubleshooting |
| Code-specific running guides | Manual submission templates and environment notes for the researcher |
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

The CLI provides only `aicc skill` and `aicc doctor`. Old remote-session and
scheduler-control skills were removed. When updating an installed copy,
inspect and explicitly remove stale AICC-owned links, preserving foreign
skills. **Existing project calculations are never automatically migrated.**

## Design principles

- **One agent, multiple on-demand skills.** The researcher owns all production
  simulation execution.
- **Physical model before input syntax.** Different scientific questions require
  different representations; one good POSCAR cannot prove the chosen physics.
- **Actual model files, not only advice.** Keep sources and transformations so
  another person can regenerate candidate structures.
- **Scientific skepticism.** Check both geometry and whether the chosen system
  can test the stated mechanism; describe competing models and confounders.
- **Automated post-processing.** The agent runs existing software tools on many
  cases, isolates failures and generates source-traceable summary tables.
- **Manual job execution.** The agent prepares inputs and analyzes outputs; it
  never submits, monitors, cancels or restarts production jobs.

For directory and reference conventions see [STRUCTURE.md](STRUCTURE.md).
For license and citation see [LICENSE](LICENSE) and [CITATION.cff](CITATION.cff).
