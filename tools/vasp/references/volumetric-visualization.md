# Volumetric Data from VASP (CHGCAR-like files)

> Load this when: preparing `CHGCAR`, `CHGDIFF`, `PARCHG`, `ELFCAR`, spin-density or VASPKIT-generated CHGCAR-like files for a figure. Rendering, slices, isovalues and image checks: `knowledge/volumetric-rendering.md`.

## Tool choice

| Need | Path |
|---|---|
| quick manual inspection | VESTA — record isovalue, colors, cell choice and view if the figure is used |
| scripted 3D isosurface or 2D slice | read here with pymatgen, render with `knowledge/volumetric-rendering.md` |
| density subtraction, planar averages, real-space wavefunctions, spin density | VASPKIT (`tools/vaspkit/references/electronic-analysis.md`), then render the CHGCAR-like result |
| structure-only figures | `tools/ovito/references/structure-rendering.md` |

Δρ fragment calculations follow `references/electronic-analysis.md` (same cell, frozen coordinates, same grid and settings).

## Reading a CHGCAR-like file

`pymatgen.io.vasp.outputs.Chgcar` reads native `CHGCAR`/`PARCHG`/`ELFCAR` and most VASPKIT outputs (511 `WFN_REAL_Bxxxx_Kxxxx.vasp`, 312 spin density, 314 `CHGDIFF.vasp`):

```python
from pymatgen.io.vasp.outputs import Chgcar
import numpy as np

chg = Chgcar.from_file("CHGDIFF.vasp")
lattice = chg.structure.lattice.matrix
positions = chg.structure.cart_coords
rho = np.asarray(chg.data["total"], dtype=float) / chg.structure.volume   # e/Å^3
print(chg.structure.composition.reduced_formula, rho.shape,
      float(rho.min()), float(rho.max()))
```

**Units:** CHGCAR stores ρ × V_cell, so `chg.data["total"]` is in e, not e/Å³. Divide by the cell volume (as above) before comparing isovalues with cube files or published values; if you keep the raw values, say so in the caption.

Check that the structure and grid match the intended calculation before rendering. For spin, `chg.data["diff"]` holds ρ↑ − ρ↓ (also × V_cell).

## Record

In addition to the general checklist in `knowledge/volumetric-rendering.md`: the VASP source run, whether the grid came from `CHGCAR`, `AECCAR0+AECCAR2`, `PARCHG` (band/k-point/energy window) or VASPKIT (task ID, menu input, log), and whether values were divided by the cell volume.

Interpretation of what the field proves: `knowledge/electronic-structure.md`.
