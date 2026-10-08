# Validating ORCA calculations

> Load this when: checking an ORCA input before submission, or judging whether a finished ORCA run is usable.

## Before submission

Run `uv run scripts/check_orca_input.py JOB.inp [--mem-gb <free GB>]`. It fails on:

- a multiplicity whose parity does not match the electron count (a neutral molecule with an odd
  number of electrons cannot be a singlet), or a multiplicity larger than electrons + 1;
- dispersion keywords ORCA does not have (`D5`) or dispersion added to a functional that already
  contains it (`-V`, `-3c`);
- PAL keywords ORCA does not accept, a `%` block without `end`, a coordinate block without its closing `*`;
- `%maxcore × nprocs` above 75 % of the memory given with `--mem-gb`.

It warns when charge and multiplicity have no stated origin in a comment, and when `NoAutoStart`
is missing (a stale `.gbw` of the same name would be read).

The script cannot know every ORCA keyword. A typo in a method or basis name is caught by ORCA
itself in the first second (`INPUT ERROR`); read the output immediately after starting a job.

## After the run

Run `uv run scripts/parse_orca.py JOB.out`. Exit 0 = clean, 1 = finished with issues, 2 = error
termination or incomplete. What it reads and what each check means:

- **Termination**: `ORCA TERMINATED NORMALLY` must be present. Otherwise the script prints the
  error lines (`INPUT ERROR`, `error termination`, `ABORTING`) to look up in `errors.md`.
- **SCF**: any "not converged" message makes the run unusable for energies, gradients, frequencies,
  or Multiwfn, even if ORCA continued.
- **Optimization**: `THE OPTIMIZATION HAS CONVERGED` for an `Opt` job. "did not converge but reached
  the maximum number of optimization cycles" means restart from `<job>.xyz` (see `running.md`).
- **Mode count**: after removing the six (linear: five) zero translation and rotation entries, the
  number of vibrational modes must be 3N-6 (linear: 3N-5). Any other count is reported.
- **Imaginary modes**: frequencies printed as negative values. A minimum has none. A small one
  (below about 50 cm-1 in magnitude) on a floppy cluster is usually numerical: tighten the
  optimization (`TightOpt`) and the grid (`DefGrid3`), then recompute. A large one means the structure
  is not a minimum; displace along the mode and re-optimize.
- **Spin contamination** (unrestricted runs): `<S**2>` should be within about 10 % of s(s+1),
  e.g. 0.75 for a doublet. A larger value is reported, not ignored.
- **Energies**: `FINAL SINGLE POINT ENERGY` (electronic energy, Eh) and, after a frequency run,
  the zero-point energy, total enthalpy and final Gibbs free energy. The script prints the lines it found,
  together with the conditions H and G depend on: temperature, pressure, quasi-RRHO on or off, and
  the point group with its symmetry number. A symmetric molecule run without symmetry shows C1 and
  symmetry number 1, which overstates its rotational entropy by R ln σ. ORCA prints the rotational
  entropy for symmetry numbers 1 to 12 in the same section; correct G with the right value or rerun
  with the right symmetry number, and record which was done.

## Embedded-crystal and conceptual-DFT special validation

A parsed ORCA `* pdbfile`/IC-QM/MM job may terminate normally even though the
chosen QM cluster, effective QM electron count, boundary cECP, or MM charges
do not represent the intended solid. Before treating it as science:

- Verify atom identities and selected QM region from actual ORCA input/output,
  not merely the source PDB atom count or formal-charge bookkeeping.
- Validate initial charges and the embedded charge distribution/neutrality,
  point-charge-shell and QM-region convergence, and absence of electron leakage
  toward the QM boundary.
- For vertical CDFT: prove unchanged QM nuclei, point-charge field, ECP boundary
  and electronic method for N/N+1/N-1; check each state converged to the
  intended spin solution. A normal ORCA exit and the preflight script alone
  do not establish this.
- If added/removed electrons live on an artificial boundary, or the anion is
  physically unbound/basis dependent, label `f+` and dual-descriptor
  results unvalidated; report this before presenting any derived trend.
- Any claim about bulk reduction/hydrolysis must still be anchored by periodic
  VASP reaction energies, competing phases and/or appropriately selected
  reaction barriers. Do not treat a Fukui isosurface as a kinetic mechanism.

## Energy discipline

- Name the quantity: E, E+ZPE, H, or G, and the temperature for H and G.
- Compared species share functional, dispersion, basis, auxiliary basis and RI scheme, grid, solvent model.
- Units: 1 Eh = 27.211386 eV = 627.5095 kcal/mol = 2625.50 kJ/mol.
- Relative energies, not bare totals, carry conclusions.

## Keep

`.inp`, `.out`, `.gbw`, final `.xyz`, `.hess` (if any), and the ORCA version from the output header.
