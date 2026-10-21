# Disorder, Defect Supercells and Amorphous Phases

> Load this when: the structure has partial occupancies (e.g. Li₆PS₅Cl S/Cl site exchange, half-occupied Li sites, mixed dopant sites); when building vacancy, dopant or aliovalent-substitution supercells; or when a glass/amorphous phase is part of the model.

A calculation needs one ordered structure per configuration. Turning an average structure into ordered ones is a sampling problem, and the choice of supercell and configurations is part of the scientific result.

## 1. Partial occupancy → ordered configurations

**Tool: [xtalkit](https://github.com/hydrogen1222/xtalkit)** (separate install: `git clone`, `uv sync`; enumeration needs enumlib or SHRY, Ewald ranking needs pymatgen — see its README). It is not bundled here. Pipeline:

```bash
# refinement table (JSON) -> disordered CIF; check Wyckoff labels and formula against the paper
uv run xtalkit build --spec LPSC_refinement.json -o LPSC
# small/medium counts: enumlib (cell size = multiple of the PRIMITIVE cell)
uv run xtalkit enumerate LPSC.cif --min-cell-size 1 --max-cell-size 1 --max-structures 50 --output-dir LPSC_enum
# huge counts: SHRY in reviewed stages
uv run xtalkit shry prepare LPSC.cif --out ready.cif --parent-spacegroup 216 --target-formula Li6PS5Cl --scaling-matrix 1 1 1
uv run xtalkit shry count ready.cif --scaling-matrix 1 1 1 --out count.json
uv run xtalkit shry enum ready.cif --scaling-matrix 1 1 1 --expect-count <COUNT> --target-formula Li6PS5Cl --write-poscar --out SHRY_run
uv run xtalkit shry verify SHRY_run --target-formula Li6PS5Cl
# electrostatic pre-screen (same composition and atom count only; must be neutral)
uv run xtalkit ewald LPSC_enum/ --charges Li:1 P:5 S:-2 Cl:-1 --top-n 20 --group --group-dir ewald_results
```

Without xtalkit, small cases can use pymatgen `OrderDisorderedStructureTransformation` (Ewald-ranked) or `EnumerateStructureTransformation` (enumlib).

Rules:

- **Physical filters after enumeration.** Enumerators know symmetry, not chemistry. In argyrodites the 48h Li sites come in pairs < 1 Å apart that cannot both be occupied: drop configurations where both sites of such a pair are filled (shortest Li–Li far below any real Li–Li contact; `check_distances.py` per file shows it) before ranking. State the cutoff you used.
- **Ewald energy is a screen, not a selection.** Take the lowest few (5–10) *and* a few random ones to DFT or a validated MLP; report the spread. If the spread is larger than the effect you want to resolve, one configuration cannot carry the conclusion.
- **Supercell sets the accessible disorder.** A 1×1×1 cell can only represent a few site-exchange fractions (e.g. 0, 25, 50 % for four 4a/4d pairs). State which fraction each cell represents and whether it matches the experimental one.
- **Keep the manifest.** Record the source CIF, occupancies, cell size/scaling matrix, enumerator and version, filters applied, total count, and which configurations were computed and why (xtalkit writes `manifest.json` for SHRY runs).
- **Random alloys** with no short-range-order information: an SQS (e.g. icet, ATAT `mcsqs`) is an alternative to enumeration; say which correlation functions were matched.

## 2. Defect and dopant supercells

**Size.** Make the supercell large enough that a defect does not feel its images: start from defect–image distances ≳ 10 Å, then test two sizes for the quantity you report (formation energy, local relaxation, migration barrier). Compute the pristine reference in the *same* supercell with the same settings.

**Sites.** Enumerate symmetry-inequivalent sites (`SpacegroupAnalyzer(...).get_symmetrized_structure().equivalent_indices`) and compute all that are chemically plausible, or justify the subset. `dope_structure.py` performs one explicit edit per call; the site choice is yours.

**Charge compensation.** For aliovalent substitution (e.g. F⁻ on S²⁻ in Na₃PS₄, Ca²⁺ on Na⁺) decide the mechanism explicitly — cation vacancy, anion interstitial, electronic (polaron/delocalised) — and build it. For dopant + vacancy pairs, enumerate distinct pair distances/orientations (nearest, intermediate, far) instead of picking one; the binding energy between them is often the result.

**Neutral or charged cell.** A neutral supercell with an explicit compensating defect and a charged supercell (`NELECT` changed, background charge) answer different questions. Charged defects need a finite-size correction (Freysoldt/FNV or Kumagai–Oba; `pymatgen-analysis-defects` or `doped` implement them), a defined Fermi level and band-edge reference, and chemical potentials of exchanged atoms — `knowledge/periodic-electrostatics.md` ("Charged cells and defects"). Do not compare raw charged-cell total energies.

**Formation energy bookkeeping.** `E_f = E_defect − E_pristine − Σ n_i μ_i (+ q(E_F + E_VBM) + E_corr)` with μ_i from a stated reservoir (elemental phases, or bounds from the phase diagram). Every term uses the same functional, POTCARs, ENCUT and k-density.

## 3. Amorphous and glass phases

There is no single glass structure; a model is one sample of an ensemble.

- Generate by melt–quench: AIMD (`tools/vasp/references/aimd.md`, `tools/cp2k/references/aimd.md`) for small cells, or a validated MLP (`tools/deepmd`, `tools/mlp`, `tools/lammps`) for larger cells and slower quenches. Record melt temperature, quench rate, final anneal and ensemble.
- Fix the density from experiment where available; otherwise equilibrate in NPT and report the result.
- Build several independent quenches (different seeds or starting configurations) and report the spread of the property.
- Validate against experiment: RDF/structure factor, and for thiophosphates the population of PS₄³⁻, P₂S₇⁴⁻, P₂S₆⁴⁻ units (Raman/NMR), before using the model for transport or interfaces.
- Cell size: large enough that the property is converged (≥ ~200–300 atoms for local structure; more for transport).

**Crystal | glass interfaces.** There is no lattice match: cut the glass to the crystal slab's in-plane cell, place it at a reasonable gap, and anneal the combined cell (MLP-MD) before relaxing; do several glass samples. Report which side was annealed and for how long.

## Hand-over

In `models/model.md`: the configuration manifest or defect-site table, supercell size and image distances, compensation mechanism, the subset computed and why, and what the sampled set can and cannot represent (fraction of site exchange, concentration, temperature).
