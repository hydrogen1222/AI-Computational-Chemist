---
name: charges
description: Atomic charges and bond orders from periodic VASP densities — Bader/AIM, DDEC6 charges + SBO + pair bond orders (Chargemol), ordinary Hirshfeld and CM5, and iterative Hirshfeld-I (Multiwfn). Single runs or batches over many finished calculations, with a Chinese human-readable report.
---

# Atomic charges from VASP densities

One skill for every charge-partitioning route. Pick the method, read its
reference, run its script. The agent does the batch work; the user never writes
loops or menu sequences.

## Which method, which engine

| Observable | Engine | Reference | Script |
|---|---|---|---|
| Bader / AIM net charge `q = ZVAL − N_Bader` | `bader` + `chgsum.pl` | `references/bader.md` | `scripts/batch_bader.py`, `scripts/bader_summary.py` |
| DDEC6 q, SBO, periodic pair BO | Chargemol | `references/ddec6-chargemol.md` | `scripts/batch_ddec6.py`, `scripts/plot_ddec6.py` |
| Ordinary Hirshfeld + CM5 already in a Chargemol log | none (parse only) | `references/ddec6-chargemol.md` | `scripts/collect_hirshfeld.py` |
| Hirshfeld, CM5, **true iterative Hirshfeld-I** | Multiwfn | `references/periodic-stockholder.md` | `scripts/prepare_periodic_chgcar.py`, `scripts/collect_periodic_charges.py` |

All routes need one converged VASP static. Bader and DDEC6 need `CHGCAR`,
`AECCAR0`, `AECCAR2`, `POTCAR` (`LCHARG` + `LAECHG`); Multiwfn uses the valence
`CHGCAR` plus matching POTCAR valence counts. Missing density files mean a new
VASP run, which needs the researcher's approval.

Executables (`bader`, `chgsum.pl`, `chargemol`, its `atomic_densities/`) are
auto-discovered by `scripts/software_locator.py` (PATH, `~/apps`, `/opt/apps`,
`~/.local/bin`, `AICC_SOFTWARE_ROOTS`). Ask for a path only when discovery
fails or finds several candidates.

## Rules that apply to every method

- **Not oxidation states.** Report signed charges in e with the method name;
  never relabel one partition as another (Chargemol's first Hirshfeld step is
  not Hirshfeld-I; Multiwfn bond indices are not DDEC6 BO).
- **Unconverged is unusable.** A Hirshfeld-I run that did not converge has no
  charge, even if a last-iteration value was printed.
- **Charge conservation** is checked only when the real cell charge is passed
  via `--net-charge`; otherwise it is reported as `NOT_CHECKED`, never PASS.
- **Compare like with like:** same functional, PAW set, grid and convergence.
  Keep atom/element mapping to the original CHGCAR.
- **Read-only by default.** Every batch script previews first; `--execute`
  (running bader/Chargemol) needs explicit approval. Original files are never
  modified; outputs go to `<run>/postprocess/<method>/` and
  `ROOT/postprocess_summary/`.
- **Never CSV-only.** Every batch ends with a short Chinese report
  (`*_report_cn.md` / `bader_summary.md`): one PPT-quotable paragraph, full
  element and site tables, sign/units, QC status, provenance, and what the
  numbers cannot prove. Regenerate reports from existing CSVs without
  recomputing:

```bash
python tools/charges/scripts/charge_report.py ROOT/postprocess_summary --only-present
```

Charts written by these scripts are quick previews. Finished figures go through
the Stormy-drawing plotting skill.

## Related

- Interpretation and evidence chains: `knowledge/electronic-structure.md`
- Fukui functions / condensed indices built on these charges: `tools/periodic-cdft/SKILL.md`
- Molecular (non-periodic) population analysis: `tools/multiwfn/SKILL.md`
