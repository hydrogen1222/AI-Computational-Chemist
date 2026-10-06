# Running ORCA 6

> Load this when: writing an ORCA input, choosing cores and memory, restarting a job, or producing wavefunction files for Multiwfn.

Method choice (functional, basis, dispersion, solvent) is science, not syntax: decide it with
`knowledge/molecular-qc-practical-rules.md` or the source paper. This file covers how to write it
for ORCA 6. Statements below were checked against the ORCA 6.1 manual
(https://www.faccts.de/docs/orca/6.1/manual/); anything marked "check" was not.

## Input layout

```text
! <method> <dispersion> <basis> [<aux basis>] <job keywords>      # simple input lines start with !
%maxcore 3000                                                      # MB per core
%pal nprocs 16 end                                                 # every % block ends with "end"
* xyz <charge> <multiplicity>
C   0.000000   0.000000   0.000000
...
*
```

- Several `!` lines are allowed; keywords are case-insensitive. An unknown or repeated keyword stops
  the run before any calculation (`INPUT ERROR ... UNRECOGNIZED OR DUPLICATED KEYWORD(S)`).
- Coordinates can come from a file: `* xyzfile 0 1 start.xyz` (no closing `*` in that form).
- Comments start with `#`.

## ORCA 6 defaults worth knowing

- **RI.** Hybrid DFT uses RIJCOSX by default; non-hybrid DFT uses RI-J; both use the `def2/J`
  auxiliary basis by default. Writing `def2/J RIJCOSX` explicitly is harmless and makes the
  input self-explaining. `!NOCOSX` turns COSX off.
- **Open shell.** A multiplicity above 1 runs unrestricted (UKS/UHF). Check `<S**2>` afterwards
  (`references/validation.md`).
- **Dispersion keywords** (6.1 manual): `D3` (same as `D3BJ`), `D3ZERO`, `D4`, `NL`, `SCNL`, `NOVDW`.
  **There is no `D5`.** Functionals ending in `-V` (e.g. `wB97X-V`) already contain non-local
  dispersion and must not get a D correction; composite `-3c` methods already include theirs.
- **AutoStart.** If a `.gbw` file with the job's base name exists, ORCA reads its orbitals as the
  starting guess. Use `!NoAutoStart` when a directory is reused for a different geometry or charge,
  or start in a clean directory.

## Cores, memory, launching

- Cores: `%pal nprocs N end` (any N) or `!PAL4` style keywords (only PAL2 to PAL8, PAL16, PAL32, PAL64).
- Memory: `%maxcore M` is **MB per core**. Keep `M × N ≤ 0.75 × free memory` of the machine
  (manual recommendation). The input check script tests this when given `--mem-gb`.
- Launch with the **full path** of the ORCA executable and redirect the output:
  `/full/path/to/orca job.inp > job.out 2>&1`. Never start ORCA under `mpirun`; ORCA starts its own
  parallel modules. Parallel runs need the Open MPI version the ORCA build expects; the machine guide
  records which one is loaded.
- Run in a local scratch directory, not on a network disk, and copy results back. The machine guide
  says where scratch is.

## Templates

Replace everything in `<...>`. These are layouts, not recommended levels of theory.

**Optimization + frequencies (minimum).**

```text
! <FUNCTIONAL> <DISPERSION> <BASIS> Opt Freq TightSCF
%maxcore <MB per core>
%pal nprocs <N> end
* xyz <charge> <mult>
...
*
```

Opt and Freq at the same level. Add `TightOpt` when frequencies will be used for thermochemistry of a
floppy cluster, and a finer grid (`DefGrid3`) if small spurious imaginary modes appear.

**Single point at a higher level on an optimized geometry.**

```text
! <FUNCTIONAL> <DISPERSION> <BASIS> TightSCF
%maxcore <MB per core>
%pal nprocs <N> end
* xyzfile <charge> <mult> <optimized>.xyz
```

Report it as `SP-level // opt-level`; thermal corrections stay from the opt level and must be named.

**Restart an optimization that ran out of cycles.** Start a new job (new base name or clean
directory) from the last geometry ORCA wrote, `<job>.xyz`: `* xyzfile <charge> <mult> <job>.xyz`.
Raise the limit with `%geom MaxIter 300 end` (default is max(3 × atoms, 50)). Read old orbitals with
`! MORead` and `%moinp "old.gbw"`.

## Files ORCA writes

| File | Content |
|---|---|
| `<job>.out` | the output you redirected; the record of the run |
| `<job>.gbw` | binary orbitals and basis; needed for restarts and wavefunction export |
| `<job>.xyz` | last geometry of an optimization |
| `<job>_trj.xyz` | all optimization steps |
| `<job>.hess` | Hessian from a frequency run |

`.gbw` files are tied to the ORCA version that wrote them.

## Wavefunction files for Multiwfn

1. Validate the run first (`references/validation.md`).
2. Convert the binary `.gbw` to a Molden file: `orca_2mkl <job> -molden` gives
   `<job>.molden.input`. Multiwfn reads this file. (`orca_2aim` writes `.wfn`/`.wfx` when an
   analysis needs that format.)
3. def2 basis sets are all-electron up to Kr. From Rb on they use effective core potentials; before
   a density-based analysis (charges, ESP, AIM, Fukui) of such atoms, check in the Multiwfn manual
   of the installed version how it handles ECPs from Molden files.
4. Record which `.gbw` the Molden file came from; never analyse a Molden file whose `.out` you have
   not validated.

Conceptual DFT (Fukui functions, dual descriptor) needs three single points (N, N+1, N-1 electrons)
at one geometry: follow `tools/multiwfn/references/conceptual-dft.md`.
