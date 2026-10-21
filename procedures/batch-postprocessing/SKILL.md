---
name: batch-postprocessing
description: Use when a researcher wants the same analysis run over many finished calculations (VASP, CP2K, ORCA, Gaussian, LAMMPS, Multiwfn, LOBSTER, VASPKIT, charges) without writing scripts or repeating commands by hand.
---

# Batch post-processing

The user names an **observable** and a data root. The agent does the rest; never ask
the user for shell loops, Python or menu sequences.

## Procedure

1. **Pin the observable and convention** — e.g. Bader net charge vs DDEC6 vs
   charge-density difference vs formal oxidation state. Record units and reference.
2. **Inventory** only the roots the user gave. Per case, record which inputs exist,
   software versions, and which tool skill applies.
3. **Preflight and preview.** Classify cases: ready, missing input, incomplete,
   incompatible settings, already processed, failed. Show the table before heavy work.
   Never compare incomparable calculations silently.
4. **Run deterministically.** Use the tool skill's batch script if one exists;
   otherwise write one small reusable helper on the program's headless interface.
   Sources stay read-only; outputs go to `<run>/postprocess/<method>/`; one failing
   case does not stop the others; nothing is silently overwritten.
5. **Validate and aggregate.** Check atom/species mapping, grids, references, return
   codes and the tool's own quality indicators. Tables (with each case's source path,
   status, units and convention) go to `data/`, previews to `figures/`.
6. **Report.** Write one Chinese `report.md` next to them: overview table, failed
   cases with reasons (once, up front), the key numbers with a PPT-ready sentence,
   figures embedded, long per-atom tables collapsed in `<details>`.
7. **Hand over** the `report.md` path, a one-line result, and the rerun command.
   Do not list folders or individual CSVs.

Output layout (charges and periodic Fukui already follow it; new helpers should too):

```text
ROOT/postprocess_summary/          or  postprocess/periodic_cdft/
  report.md   figures/   data/         report.md   data/   work/
```

## Where the batch tooling lives

| Observable | Skill |
|---|---|
| Bader, DDEC6/SBO/BO, Hirshfeld, CM5, Hirshfeld-I | `tools/charges/SKILL.md` (scripts + mandatory Chinese report) |
| Fukui f+/f−/f0, dual descriptor, condensed indices | `tools/periodic-cdft/SKILL.md` |
| DOS/bands, work function, AIMD MSD/diffusion via VASPKIT | `tools/vaspkit/SKILL.md` |
| COHP/COOP/ICOHP (check spilling first) | `tools/lobster/SKILL.md` |
| Molecular wavefunction analyses (check menu numbers on the installed version) | `tools/multiwfn/SKILL.md` |
| Energies, convergence, geometries from engine outputs | `tools/<engine>/SKILL.md` parsers |
| MD trajectories (keep time windows, temperatures, uncertainties) | `tools/lammps/SKILL.md`, `tools/ovito/SKILL.md`, `knowledge/molecular-dynamics.md` |

Charts written by batch scripts are previews; finished figures go through Stormy-drawing.

**Permission boundary:** reading, parsing and dry runs are ordinary. Ask before
expensive analyses, CPU/GPU-heavy runs, any new electronic-structure calculation, or
overwriting results. Post-processing is not permission to submit jobs.
