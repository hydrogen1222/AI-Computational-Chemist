# Rendering Volumetric Fields (charge density, Δρ, spin, ELF, orbitals)

> Covers: reproducible headless rendering of any 3D grid — isosurfaces with PyVista, 2D slices through atoms, choosing isovalues, image checks and what to record. How to *produce and read* the grid lives in the engine reference: `tools/vasp/references/volumetric-visualization.md` (CHGCAR-like files) or `tools/cp2k/references/volumetric-visualization.md` (cube files).

Use VESTA or VMD for interactive inspection; script with PyVista when the figure must be regenerated with exact parameters or batch-compared. Both engine references end with the same two objects: a 3D array `rho` and a 3×3 `lattice` (rows = cell vectors, Å).

```bash
uv venv .venv-vis
uv pip install --python .venv-vis/bin/python pymatgen ase pyvista vtk scipy matplotlib pillow
```

On headless machines VTK may warn about a missing `DISPLAY` (e.g. `bad X server connection`). That is only a warning if the PNG is written and passes the nonblank check below.

## Density difference and sign convention

```text
Δρ = ρ(combined) − ρ(fragment A in combined geometry) − ρ(fragment B in combined geometry)
```

Every component calculation keeps the combined cell, frozen coordinates, grid, functional, basis/PAW, k-mesh, smearing and spin policy. Do not relax fragments for a standard adsorption/interface rearrangement plot. State the sign convention in the caption (a VESTA-like default: yellow = accumulation, cyan = depletion) and use equal positive and negative isosurface magnitudes unless an asymmetry is documented.

## 3D isosurface with PyVista

```python
import numpy as np
import pyvista as pv

# rho: (nx, ny, nz) array; lattice: 3x3 cell matrix in Å (from the engine reference)
nx, ny, nz = rho.shape
ii, jj, kk = np.mgrid[0:nx, 0:ny, 0:nz]
frac = np.stack((ii / nx, jj / ny, kk / nz), axis=-1)
cart = frac @ lattice                                  # keeps skewed cells correct

grid = pv.StructuredGrid(cart[..., 0], cart[..., 1], cart[..., 2])
grid["rho"] = rho.ravel(order="F")

level = 0.003                                          # choose from the data, then record it
positive = grid.contour([level], scalars="rho")
negative = grid.contour([-level], scalars="rho")

plotter = pv.Plotter(off_screen=True, window_size=(1600, 1100))
plotter.set_background("white")
plotter.enable_parallel_projection()                   # orthographic: comparable sizes
style = dict(opacity=0.82, smooth_shading=True, ambient=0.55, diffuse=0.75,
             specular=0.35, specular_power=28.0, backface_culling=True)
plotter.add_mesh(positive, color="#ffff00", **style)   # accumulation
plotter.add_mesh(negative, color="#00ffff", **style)   # depletion
plotter.camera_position = "xz"                         # or "xy" / "yz"
plotter.camera.zoom(1.25)
plotter.show(screenshot="drho_level0p003_xz.png")
```

Appearance knobs: raise `opacity` or `ambient` if the surface looks washed out; moderate `specular` gives a gloss without a metallic look; `backface_culling` reduces muddy overlaps. Keep window size, camera and colors fixed across a comparison series. Use stable element colors and modest atom radii so atoms locate the structure without hiding lobes.

## Choosing the isovalue

The isovalue is a figure parameter and must be reported. Print the range first — values near cores or grid artifacts dominate the absolute min/max:

```python
print(rho.shape, float(rho.min()), float(rho.max()), np.percentile(abs(rho), [95, 99]))
```

- start near the 95th–99th percentile of `|Δρ|`, or a value conventional in related figures;
- raise it when weak haze hides the important lobes, lower it when only core artifacts remain;
- same magnitude for ± surfaces and across a comparison series unless a reason is stated.

## 2D slice through three atoms

Often clearer than an isosurface for a bond or interface. Use 1-based atom indices when talking to the user.

```python
import numpy as np
from scipy.ndimage import map_coordinates
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

points = positions[np.array([21, 25, 26]) - 1]        # Cartesian Å, 1-based indices
origin = points.mean(axis=0)
u = points[1] - points[0]; u /= np.linalg.norm(u)
v = points[2] - points[0]; v -= np.dot(v, u) * u; v /= np.linalg.norm(v)

x = np.linspace(-4.0, 4.0, 900); y = np.linspace(-4.0, 4.0, 900)
xx, yy = np.meshgrid(x, y)
frac = (origin + xx[..., None] * u + yy[..., None] * v) @ np.linalg.inv(lattice)
coords = [(frac[..., a] % 1.0) * rho.shape[a] for a in range(3)]
plane = map_coordinates(rho, coords, order=1, mode="wrap")   # linear: no ringing at cores

vmax = 8.0                                                   # disclosed display clip
cmap = LinearSegmentedColormap.from_list("diff", ["#00ffff", "#ffffff", "#ffff00"], N=256)
fig, ax = plt.subplots(figsize=(7.2, 7.2), dpi=250)
im = ax.imshow(plane, origin="lower", extent=(x[0], x[-1], y[0], y[-1]),
               cmap=cmap, vmin=-vmax, vmax=vmax, aspect="equal")
ax.contour(x, y, plane, levels=np.linspace(-vmax, vmax, 21), colors="#303030", linewidths=0.35, alpha=0.4)
fig.colorbar(im, ax=ax, shrink=0.82)
fig.savefig("drho_slice_21_25_26.png", facecolor="white")
```

When the plane passes through a heavy atom, core values dominate the range; clip the displayed scale to the bonding region and report the clip.

## Image check

```python
from PIL import Image, ImageStat
print(ImageStat.Stat(Image.open("drho_level0p003_xz.png").convert("RGB")).extrema)
```

All channels at `(255, 255)` means a blank image. A nonblank result still needs a look: framing, atom visibility, sign colors, and whether the visible feature supports the claim.

## Record for every figure

- source file, how it was produced (engine print section, VASPKIT task, Δρ fragments);
- field definition, units and sign convention;
- isovalue or slice color limit (and clip), colors;
- camera, projection, image size; atom indices defining a slice plane;
- script path and package versions; nonblank check passed.

An isosurface or clipped slice shows *where* density moves, not *how much*. Pair it with Bader/DDEC6 charges, PDOS, work-function shifts, spin moments or COHP, depending on the claim (`knowledge/electronic-structure.md`).
