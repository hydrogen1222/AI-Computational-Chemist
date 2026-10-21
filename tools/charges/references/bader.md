# Bader / AIM net charges from VASP

## Inputs

`CHGCAR`, `AECCAR0`, `AECCAR2` and `POTCAR` from the same converged static
(`LCHARG=.TRUE.`, `LAECHG=.TRUE.`). These cannot be recreated by a parser; if
missing, a new VASP run needs the researcher's approval.

Partition on the all-electron reference:

```bash
chgsum.pl AECCAR0 AECCAR2
bader CHGCAR -ref CHGCAR_sum
```

Report `q = ZVAL − N_Bader` (e). It is a relative, model-dependent number, not a
formal oxidation state. Preserve `ACF.dat`, `BCF.dat`, `AVF.dat`, `CHGCAR_sum`,
the POTCAR ZVAL counts and the static structure.

## Single run

```bash
python tools/charges/scripts/bader_summary.py RUNDIR   # or --zval "Na:7,P:5,S:6"
```

Reports per-element mean q with the **per-atom spread**. When the spread exceeds
the difference between the structures being compared, Bader charge is a weak
discriminator (`knowledge/electronic-structure.md`).

## Batch

```bash
python tools/charges/scripts/batch_bader.py ROOT                 # read-only preflight
python tools/charges/scripts/batch_bader.py ROOT --execute       # after approval: chgsum.pl + bader
python tools/charges/scripts/batch_bader.py ROOT --collect-only  # ACF.dat already exists
```

- Finds runs recursively; `--manifest` for an explicit shortlist.
- Without POTCAR metadata, pass **verified** valence counts via `--zval`; never guess.
- `--net-charge` only when the cell charge is verified; otherwise conservation is
  `NOT_CHECKED`, never PASS.
- Working files go to `<run>/postprocess/bader/`; the Bader section of
  `ROOT/postprocess_summary/report.md` and its tables in `data/` are written
  for you. Originals are never touched; `--force` overwrites generated Bader
  outputs only.
- `bader`/`chgsum.pl` are found via `scripts/software_locator.py`;
  `--bader-bin` / `--chgsum-bin` are fallbacks.
