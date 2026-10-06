# ORCA error recovery

> Load this when: an ORCA run stopped with an error, SCF or optimization did not converge, or results look wrong.

Find the exact string in the output first; `parse_orca.py` prints the error lines. Change one thing
at a time. Rows marked *(seen)* happened on Stormy's machines; the others come from the ORCA 6.1
troubleshooting page.

## Input errors (stop within the first second)

| Output string | Cause | Fix |
|---|---|---|
| `INPUT ERROR` / `UNRECOGNIZED OR DUPLICATED KEYWORD(S) IN SIMPLE INPUT LINE` followed by the word, e.g. `D5` *(seen, ORCA 6.1.1)* | keyword does not exist in this version, is misspelled, or appears twice | check the word against the manual; for dispersion use `D3`/`D3BJ`/`D4` (there is no `D5`); remove duplicates |
| `Unknown identifier in <BLOCK> block` or `'END' was expected at the end of the <BLOCK> block` | a `%` block is not closed with `end`, or a keyword is misspelled inside it | close the block; check the keyword |
| `expect a '$', '!', '%', '*' or '[' in the input` | missing `!`/`%`/`*`, or an extra `end` | fix the line it names |
| `found a coordinate definition line (* ctyp charge mult) but could not read ctyp` | `*xyzfile` written with a closing `*`, or a typo in `xyz` | remove the trailing `*` for `xyzfile` |
| `CANNOT OPEN FILE` | xyz or gbw file path wrong | correct the path; no quotes in `* xyzfile` |
| `non-ASCII character(s) found` | input edited with a word processor or pasted from a web page | retype the line in a plain-text editor |
| `There are no main basis functions on atom number` | basis does not cover that element | choose a basis that does, or set one per element |
| `RI is on but the HF exchange must be handled somehow` | RI requested for a hybrid without an exchange scheme | use `RIJCOSX` (default for hybrids) or `RIJK` |

## Launch errors

| Output string | Cause | Fix |
|---|---|---|
| `For parallel runs ORCA has to be called with full pathname` | started as `orca job.inp` from `$PATH` | call `/full/path/to/orca job.inp > job.out` |
| `FATAL ERROR ENCOUNTERED` with `I/O OPERATION FAILED` | ORCA started under `mpirun` | start the ORCA driver without `mpirun` |
| MPI start-up errors (`mpirun`/`ORTE`/`PMIx`) | Open MPI version or `PATH`/`LD_LIBRARY_PATH` does not match the ORCA build | load the Open MPI version recorded in the machine guide |

## Resources

| Output string | Cause | Fix |
|---|---|---|
| `Please increase MaxCore` | a step needs more memory per core | raise `%maxcore`, keeping `maxcore × nprocs ≤ 0.75 × free memory`; lower `nprocs` if needed |
| `OUT OF MEMORY ERROR` | same, often with a segmentation fault | as above |
| `Failed to add ... to ...` (TMatrixContainers) | scratch disk full | free space or use a larger scratch directory |

## SCF

| Symptom | Cause | Fix, in this order |
|---|---|---|
| SCF not converged message; `Resetting DIIS` repeated | difficult electronic structure, bad geometry, or wrong charge/multiplicity | 1. re-check charge, multiplicity, geometry; 2. `! SlowConv` (or `VerySlowConv`); 3. converge a smaller basis and read it with `MORead`; ORCA 6 switches to TRAH automatically when DIIS stalls |
| `Your GBWFile is either corrupt or from a different ORCA version` | old `.gbw` | rerun without it, or try `!Rescue` |
| `Input geometry does not match current geometry` | AutoStart picked up an old `.gbw` | `!NoAutoStart` or a clean directory |
| `Potentially linear dependencies` / `Diagonalization failed with error code: -5` | diffuse basis on a compact cluster | smaller or less diffuse basis, or the manual's linear-dependence settings |

## Optimization and frequencies

| Symptom | Fix |
|---|---|
| `did not converge but reached the maximum number of optimization cycles` | inspect the last geometry; restart from `<job>.xyz` with `%geom MaxIter 300 end`; if it oscillates, try `! COPT` or a cheaper level first |
| small imaginary mode after Opt+Freq | `TightOpt` plus `DefGrid3`, recompute frequencies |
| large imaginary mode | not a minimum: displace along the mode and re-optimize |

## Wrong-looking results

Check, before changing anything else: charge and multiplicity, `<S**2>`, SCF convergence, whether
the structure is the intended one, and whether energies being compared share the same level.
