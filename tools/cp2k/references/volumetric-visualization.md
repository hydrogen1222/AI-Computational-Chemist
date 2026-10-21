# Volumetric Data from CP2K (cube and Molden files)

> Load this when: generating or reading CP2K electron-density, spin-density, MO, ELF, Hartree-potential or charge-density-difference cubes, or Molden files for Multiwfn. Rendering, slices, isovalues and image checks: `knowledge/volumetric-rendering.md`.

## Tool choice

| Need | Path |
|---|---|
| quick cube inspection (sign, cell, images, isovalue) | VESTA or VMD |
| scripted 3D isosurface or 2D slice | read here with ASE, render with `knowledge/volumetric-rendering.md` |
| orbital/population/bonding analysis | Multiwfn from Molden (below) |
| density arithmetic, planar averages | cubecruncher, Multiwfn or a recorded script — identical grids and cells for all operands |
| trajectories, NEB images, movies | VMD or OVITO |

## Generating fields

Check the installed CP2K manual for exact print-section paths. Common patterns:

```text
&DFT
  &PRINT
    &E_DENSITY_CUBE
      STRIDE 1 1 1
    &END E_DENSITY_CUBE
    &V_HARTREE_CUBE
      STRIDE 1 1 1
    &END V_HARTREE_CUBE
    &MO_CUBES
      NHOMO 2
      NLUMO 2
      WRITE_CUBE T
    &END MO_CUBES
    &ELF_CUBE
      STRIDE 1 1 1
    &END ELF_CUBE
  &END PRINT
&END DFT
```

- Cube sections can be large: use `STRIDE` or a narrow MO window for exploration, full resolution only for the final figure.
- Orbitals have arbitrary phase; do not compare lobe colors across runs unless the phase was aligned.
- Spin density is usually `ρα − ρβ`; state it.
- For potential/work-function analysis keep the static run's cell, slab orientation, Poisson solver and dipole correction.

**Charge-density difference.** For slab + adsorbate, run three statics in the same slab cell with frozen coordinates: adsorbed slab; slab with adsorbate atoms removed; adsorbate alone in the adsorbed geometry. Same grid (CUTOFF/REL_CUTOFF), functional, basis/potential, k-policy, smearing and charge/spin. Then Δρ = combined − slab − adsorbate on identical grids.

## Reading a cube file

```python
from ase.io.cube import read_cube_data
import numpy as np

rho, atoms = read_cube_data("chgdiff.cube")    # values as written by CP2K (e/bohr^3 for densities)
lattice = atoms.cell.array                       # Å
positions = atoms.get_positions()
print(atoms.get_chemical_formula(), rho.shape, float(np.nanmin(rho)), float(np.nanmax(rho)))
```

State the units in the caption; multiply by 6.748 (1/0.52918³) to convert e/bohr³ to e/Å³ when comparing with VASP-derived grids.

## Molden / Multiwfn

CP2K `MO_MOLDEN` files suit Γ-only orbital and bonding analysis, but post-processors may need extra metadata:

- add `[Cell]` for periodic systems when the tool expects lattice vectors;
- make sure atom labels and pseudopotential valence counts are understood;
- keep the raw `.molden` and any edited copy separate;
- record every Multiwfn menu path or batch input (PDOS, ELF, LOL, AIM, IRI, Mayer, orbital composition).

CP2K `.wfn` restart files are not quantum-chemistry `.wfn` analysis files.

## Record

In addition to the general checklist in `knowledge/volumetric-rendering.md`: CP2K version, input/output/restart paths, the exact print section, the Δρ fragment folders, and the units of the cube values.
