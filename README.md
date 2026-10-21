# AI Computational Chemist (AICC)

Agent skills for computational materials and chemistry: turn a scientific question
into defensible atomistic models, prepare inputs for the codes, and batch-analyze
finished calculations. The researcher runs all production jobs.

Personal fork of [JCLiuGroup/AI-Computational-Chemist](https://github.com/JCLiuGroup/AI-Computational-Chemist),
trimmed to the codes I use. Upstream citation: [CITATION.cff](CITATION.cff); license: [LICENSE](LICENSE).

## Layout

| Path | What |
|---|---|
| `AGENTS.md` | Principles and routing, loaded every session |
| `procedures/` | Task workflows: `scientific-modeling` (main entry), `literature-to-calculation`, `batch-postprocessing`, `review-response` |
| `tools/` | One skill per code: `vasp`, `vaspkit`, `cp2k`, `orca`, `gaussian`, `multiwfn`, `lammps`, `ovito`, `lobster`, `phonopy`, `deepmd`, `mlp`; plus `structure-prep`, `charges`, `periodic-cdft` |
| `knowledge/` | Code-independent theory notes, read on demand |
| `tests/` | Script and repository-consistency tests |

Each skill is `SKILL.md` (trigger + route map), `references/` (load only what the task
needs) and `scripts/`.

Every analysis hands back **one `report.md`** (Chinese, figures embedded) with `figures/`
and `data/` beside it — e.g. all charge methods on a calculation root merge into
`ROOT/postprocess_summary/report.md`; periodic Fukui results go to
`postprocess/periodic_cdft/report.md`.

## Install

```bash
./install.sh                          # global, Claude Code + Codex
./install.sh --harness claude         # one harness only
./install.sh --project /path/to/proj  # project-local, also links CLAUDE.md / AGENTS.md
./install.sh --force                  # refresh after git pull
```

Figures come from [Stormy-drawing](https://github.com/hydrogen1222/Stormy-drawing),
installed separately. No scientific software, POTCARs or binaries are included.

## Tests

```bash
for t in tests/*_test.py; do python "$t"; done
```
