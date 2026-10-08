# Locked parameters (fork)

> Load this when: writing or changing a project's `docs/locked_parameters.md`, choosing between a convergence test and a cited value, or reading a `check_locked_params.py` failure.

The lock is the project's single list of settings that change the physics of every
energy: plane-wave cutoff, functional, smearing, k-point density, and POTCARs. The
user signs it; agents only read it. `scripts/check_locked_params.py` compares each run
directory against it before submission, so a changed setting stops the run instead of
relying on an agent to notice.

## File format

Plain markdown at `docs/locked_parameters.md` in new projects, readable in any markdown viewer (older projects may retain their original root-level path until deliberately migrated):

- `## <profile>` starts a profile; the first profile is the default.
- `- KEY = VALUE` inside a profile is a locked value. Every other line is free text for
  the reader: where the value came from, who signed, and when.
- `inherit = <profile>` copies another profile first, so a hybrid or DOS profile lists
  only what differs.
- Special keys: `KSPACING_MAX` (largest allowed k-point spacing in 1/Å, VASP
  `KSPACING` convention with 2π included; denser meshes pass), `KPOINTS_MODE`
  (`Gamma` or `Monkhorst`), `POTCAR` (one label per element), `POTCAR_FAMILY` (first
  word of the TITEL line, e.g. `PAW_PBE`).
- Every other key is an INCAR tag that must appear in the INCAR with the same value.
  Physics tags not locked by the chosen profile (functional, Hamiltonian, smearing,
  cutoff; the list is in the script) are not allowed in the INCAR at all.

## Example

```markdown
# 锁定参数

截断能和 k 点来自 001_convergence_test_Li6PS5Cl：每原子能量变化小于 1 meV。
Stormy 签字，T+2h10m。

## pbe
- ENCUT = 520
- PREC = Accurate
- GGA = PE
- ISMEAR = 0
- SIGMA = 0.05
- LASPH = .TRUE.
- KSPACING_MAX = 0.25
- KPOINTS_MODE = Gamma
- POTCAR = Li_sv P S Cl
- POTCAR_FAMILY = PAW_PBE

## hse06
- inherit = pbe
- LHFCALC = .TRUE.
- HFSCREEN = 0.2

## dos
- inherit = pbe
- ISMEAR = -5
- KSPACING_MAX = 0.15
```

The numbers above are an illustration of the format, not recommended values.

## Where the values come from

The user chooses one route at the start of the project and the lock says which:

1. **Convergence test, once per material.** Single-point energies only, on the
   conventional or primitive cell: ENCUT at five values in 50 eV steps (for example
   400 to 600 eV) at a dense k-mesh, then three or four k-point densities at the
   highest ENCUT. The converged value is the smallest one whose energy per atom is
   within 1 meV of the most accurate run; a script reads the energies, no judgment is
   needed. Later projects on the same material reuse the result and cite its directory.
2. **Cited value.** Take the settings from a paper or Materials Project and write the
   source next to them. No test is run.

Cell-shape relaxations need a higher cutoff than fixed-cell runs because of Pulay
stress; if the project relaxes cell shape, the lock should say whether a separate
`relax` profile uses a raised ENCUT (commonly 1.3 × the largest ENMAX).

## When the check fails

A failure lists each mismatch. Fix the input to match the lock. If the lock itself
looks wrong for this calculation (for example a band-structure path, which the script
does not check, or a method the lock has no profile for), stop and ask the user; only
the user edits the lock, and the change goes in the change log.
