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
Every supported **atomic-charge** batch now exports an actual
human-readable Chinese report, not just CSV values: a concise
PPT-quotable sentence, full element/site data, QC results and
scientific interpretation limits. The shared stdlib reporter can also
refresh those reports without re-running Bader, Chargemol or Multiwfn:
`python tools/vasp/scripts/charge_report.py CALC_ROOT/postprocess_summary --only-present`.
It does not silently claim charge conservation if the expected
cell net charge was not specified, and does not treat nonconverged
Hirshfeld-I charges as valid.

**Periodic conceptual DFT:** `tools/periodic-cdft/SKILL.md`
covers f+, f-, f0, dual Fukui response and conditional condensed indices
from the existing VASP/Bader/Chargemol/Multiwfn outputs. Three independently
installed grid engines (Multiwfn, Critic2, FukuiGrid) can be compared on
matching VASP states; FukuiGrid's fractional-electron interpolation is
a separately labeled approximation. AICC includes reproducible Critic2 input generation,
a signed Gaussian-cube cross-engine grid auditor, and per-site
condensed response reports. AICC provides read-only CHGCAR/
NELECT/geometry preflight and condensed charge-table checks; actual
third-party computation, output integrity checks and any charged-cell
physical correction must be locally validated. No external binaries,
licensed PAWs or third-party source are included.

**Figures:** AICC includes the Stormy-drawing plotting Skill (source
[Stormy-drawing](https://github.com/hydrogen1222/Stormy-drawing), snapshot
`900add75a2978597640484d0b805a3d760a9da1b`). For publication figures,
`tools/plotting/SKILL.md` supersedes the older report-oriented style.
Use `tools/plotting/scripts/init_figure.py` to create a self-contained
`figures/001_.../` with its own copied data, plot.py, source recipe, stable
color registry and style QA. Temporary/PPT-ready charts produced by analysis
scripts are exploratory previews until regenerated and reviewed under the
plotting Skill. Arial is required for final output; the upstream Skill
documents setup and a stand-in font strictly for drafts and tests. The
standard requires local matplotlib/numpy/Pillow dependencies, not a
bundled licensed font.

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
| `tools/vasp/scripts/collect_hirshfeld.py` | Extract ordinary Hirshfeld/CM5 charges already computed by Chargemol; generate comparison CSV/PPT figures |
| `tools/periodic-cdft/` | Periodic Fukui preflight, local Multiwfn/Critic2/FukuiGrid (finite-difference vs interpolation), condensed indices from charge CSVs, and scientific QC; no external binaries vendored |
| `tools/chargemol/` | DDEC6 charges, SBO, all printed periodic bond types, and paginated PPT-ready plots |
| `tools/vasp/scripts/charge_report.py` | Chinese presentation-ready, source-traceable reports for Bader, DDEC6, Chargemol Hirshfeld/CM5 and Multiwfn; no scientific recalculation |
| `tools/plotting/` | Stormy-drawing publication figure Skill, reusable `pubstyle.py`, figure-folder builder, templates and QA |
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
