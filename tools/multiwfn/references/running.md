# Running Multiwfn: Compact Workflow Notes

> Load this when: choosing a Multiwfn analysis, preparing `.fchk`/`.wfn`/`.molden` input, exporting cube files, or post-processing Gaussian TD-DFT outputs.

Keep this operational. The science of what a charge/orbital/bonding claim means lives in `knowledge/electronic-structure.md`, `knowledge/bonding-analysis.md`, and `knowledge/molecular-qc-practical-rules.md`.

## Verified current-version integration facts (narrow smoke test)

An operator-supplied **ORCA 6.1.1 / Multiwfn 2026.10.1** p-benzoquinone
three-charge-state example has been inspected using its real inputs, ORCA
outputs, converted wavefunctions and Multiwfn commands/logs. It is a
**tool-chain smoke test only** (the deliberately inexpensive B97-3c + def2-SVP
setup lacks the diffuse-basis/electron-binding validation required for
publication-quality f+). This is *not* a verified solid-state embedded-cluster
or periodized crystal method. For a newer installed build, reconfirm these
menu/format behaviors with a small test rather than assuming compatibility.

| Multiwfn function in tested version | Acceptable demonstrated input | Do not blindly substitute |
|---|---|---|
| `22 -> 2` global quantities + condensed Hirshfeld Fukui | `.wfx` / `.wfn` (also lists `.fch`, `.mwfn`) from ORCA `orca_2aim` | `.molden.input` lacks the energies this option requires |
| `22 -> 3` finite-difference Fukui and dual descriptor cube grids | `.wfx` observed (menu may accept Molden; do not assume this covers every property) | a filename prompt after missing `N.wfn` does **not** itself mean other formats are rejected |
| `22 -> 6` orbital-weighted condensed Fukui/dual descriptor | `.molden.input` from `orca_2mkl` (menu lists `.mwfn`, `.fch`, `.gms`) | `.wfx` rejected for this option |
| `18` excited-state hole/electron and NTO analysis | ORCA `.out` for excitations plus matching `.molden.input` orbitals | requires all prompts, not just the visible top-level menu |

For ORCA conversion, use the **matching version's** `orca_2aim` to produce
`.wfx`/`.wfn`, and `orca_2mkl <job> -molden` to produce
`.molden.input`. A Molden conversion alone is not a universal replacement
for an energy-containing wavefunction representation.

**Batch-mode reliability:** `Multiwfnpath` points to the **directory
containing `settings.ini`**, not the executable. Set the desired
`OMP_NUM_THREADS`. Run with a separate analysis working directory because
outputs are written to the process current working directory, and retain
the input file, `commands.txt`, captured stdout/stderr and result files.
First examine the installed version's prompts interactively; a batch
command sequence is not guaranteed stable across versions. A hidden
sub-question (e.g., whether a hole-density cube is total/local/cross)
can shift every later answer and even create a zero-byte output while
Multiwfn returns **exit code 0**. Therefore **exit code 0, an apparent
“Done!”, and existence of a filename are not sufficient**: assert
non-zero plausible size, readable complete cube header/grid/values or
tabular row count, the exact requested output basename, expected
scientific normalization, and absence of menu/runtime error messages.
Do not turn a genuine error into an accepted result because the
Fortran process exited successfully.

## Input preparation

Gaussian checkpoint handoff:

```bash
formchk job.chk job.fchk
Multiwfn job.fchk
```

ORCA handoff (validate the ORCA run first with `tools/orca/scripts/parse_orca.py`):

```bash
orca_2mkl job -molden        # job.gbw -> job.molden.input
Multiwfn job.molden.input
```

Use `.fchk` when possible: it carries basis and orbital coefficients in a portable text form. `.wfn`, `.wfx`, `.molden`, and cube/grid files are also acceptable when they contain the data required by the target analysis.

## Analysis routing

| Target | Multiwfn use | Notes |
|---|---|---|
| molecular orbital isosurface | load `.fchk`, choose orbital/grid/cube or built-in render path | record orbital index, occupation, isovalue |
| spin density | spin-density grid/cube analysis | for radicals, broken-symmetry singlets, open-shell localization |
| atomic charges | population-analysis menu | prefer NPA/Hirshfeld/ADCH-style schemes over Mulliken for claims |
| TD-DFT state assignment | NTO / hole-electron / transition-density analyses | use when Gaussian transition list is mixed |
| Fukui function, dual descriptor, condensed Fukui, global reactivity indices | main function 22 (conceptual DFT) | three single points N, N+1, N-1 at one geometry; follow `references/conceptual-dft.md` |
| UV/ECD spectrum plotting | load TD log(s) or weighted list if supported | record broadening and conformer weights |
| ESP/ELF/LOL/NCI/IRI/AIM | scalar-field or topology analysis | record function, grid, isovalue/cutoff, color convention |
| VMD rendering | export cube files and VMD script/path | record isovalue, sign convention, and state/orbital |

## Minimal records

Every Multiwfn-derived result should preserve:

- input file path and upstream calculation log;
- method, basis, charge/multiplicity, solvent, state/orbital index;
- Multiwfn version and menu path/options;
- grid spacing, isovalue, cutoff, broadening, or population scheme as applicable;
- output files: cube, image, table, spectrum, or text excerpt.

## Common Gaussian handoffs

- Orbital / spin-density / ESP / NTO analysis: `.chk` -> `.fchk` first.
- TD-DFT spectrum or ECD: keep Gaussian `.log` plus conformer weights if averaging.
- Density-difference or cube rendering: export named cube files and record whether the cube is MO, density, spin density, ESP, ELF, NCI/IRI, etc.
