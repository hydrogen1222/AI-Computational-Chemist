# Multiwfn Troubleshooting

> Load this when: Multiwfn cannot read a file, outputs strange charges/orbitals, cube files look wrong, or spectra/plots do not match the intended state.

## Silent-success and file-format traps verified with ORCA 6.1.1 / Multiwfn 2026.10.1

- A Multiwfn batch analysis may return **exit code 0** after menu misalignment,
  even if an exported cube is zero bytes or not generated. Check the exact file,
  nonempty complete cube header, expected grid values and all menu/runtime messages;
  never use exit code alone as a success criterion.
- Option `22 -> 2` (global/condensed Fukui) needs a representation containing
  energies (`.wfx` worked; `.molden.input` was rejected). Option `22 -> 6`
  (orbital-weighted condensed Fukui) accepted Molden but rejected `.wfx`.
  Do not assume one conversion format works for every submenu.
- `Multiwfnpath` denotes the directory that contains `settings.ini`,
  not the executable. Set working directory explicitly; generated files are
  written to that directory.
- Hidden submenu prompts can consume what a batch script intended as the
  next menu number. Before automating a new version, capture a small manual
  transcript and recheck output names/content with a known example.

## Common symptoms

| Symptom | Likely cause | Fix |
|---|---|---|
| cannot read Gaussian `.chk` | binary checkpoint is version/platform dependent | convert with `formchk job.chk job.fchk` |
| orbitals missing or wrong count | input file lacks orbital coefficients or is not from final job | regenerate `.fchk` from the intended final checkpoint |
| charge results look absurd | Mulliken with large/diffuse basis, wrong file, or wrong state | use a more robust scheme; verify basis/state/provenance |
| spin density absent | closed-shell input or spin data unavailable | confirm unrestricted/open-shell calculation and use the correct file |
| TD/NTO state mismatch | wrong log/fchk pair or state index shifted | map state number to Gaussian output before analysis |
| cube is blank or tiny | isovalue too high, wrong orbital/state, or wrong scalar | lower isovalue; verify cube type and index |
| VMD colors/signs confusing | sign convention not recorded | explicitly define positive/negative colors and isosurface values |
| ORCA Molden file not read or orbitals look wrong | Molden written from a different or unvalidated `.gbw`, or a different ORCA version | regenerate with `orca_2mkl job -molden` from the validated run's `.gbw` |
| condensed Fukui values do not sum to 1 | N, N+1, N-1 files swapped, from different geometries, or from different levels | regenerate all three at one geometry and level; check file names against the manual |
| N+1 (anion) calculation fails or EA comes out negative | anion SCF hard; extra electron unbound in a small basis | converge with SlowConv and a diffuse basis; report a negative EA next to every f+ value |
| spectrum differs from expectation | missing conformers, wrong broadening, too few states, solvent mismatch | reproduce state list, weights, and broadening settings |

## Recovery rules

- Regenerate inputs from the validated upstream calculation rather than editing analysis files by hand.
- Do not change population scheme or isovalue until the file/state provenance is confirmed.
- For figures, inspect both positive and negative isosurfaces when signs matter.
- For spectra, keep a plain text record of all conformer log files and weights.
