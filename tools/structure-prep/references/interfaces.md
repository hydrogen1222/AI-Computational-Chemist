# Building Interfaces (metal | electrolyte, crystal | crystal)

> Load this when: building an explicit interface between two crystals — e.g. Li or Na metal on a sulfide electrolyte, an electrolyte against a cathode or interphase phase, or a crystal | crystal grain boundary between different phases.

An explicit interface is the model to choose when the question is about the interface itself (interphase formation, charge transfer across it, local structure, adhesion). If the question is only "is Li₆PS₅Cl reduced by Li?", bulk reaction thermodynamics or a defect/insertion model may answer it more cheaply — decide this in `procedures/scientific-modeling` first.

## Choices to make, in order

1. **Phases and source structures** for both sides (`running.md`, "Sourcing database structures"), each relaxed with the project settings (`locked_parameters.md`). Building from unrelaxed or differently-relaxed bulks bakes a fake strain into the model.
2. **Facets.** For a metal, its lowest-energy facets (bcc Li/Na: (100), (110)). For the electrolyte, facets with experimental or computed precedent; if none, a few low-index candidates labeled exploratory.
3. **Terminations** of both sides — a scientific choice, as for slabs. Check electrolyte terminations by coordination signature with `make_slab.py` first; for argyrodite, whether the surface exposes PS₄ units intact, S²⁻/Cl⁻ anions or Li changes the reactivity.
4. **Which side is strained.** The builder strains the *film* onto the *substrate*. Make the softer phase the film (alkali metal on a ceramic electrolyte), and report the strain. Typical targets: |strain| ≲ 2–3 % on the soft side; above ~5 % the strain energy can dominate the interfacial energy you want to compute.
5. **Area vs strain.** Smaller strain needs a larger lateral cell. Pick the smallest match whose strain is acceptable, not the smallest strain overall.
6. **Thickness.** Enough layers on each side for the middle to look like bulk (check layer-resolved charges or forces after relaxation); 3–5 unit planes per side is a starting point, not a rule.
7. **One or two interfaces.** With vacuum over the film you get one interface plus two free surfaces (surface artefacts, dipole across the vacuum). With `--vacuum 0` you get a periodic sandwich with two interfaces and no vacuum — cleaner bulk regions, but the two interfaces must be equivalent or the energy is an average.
8. **Initial gap and registry.** The default 2.0 Å gap is a starting guess. For energies, scan the gap (and in-plane registry for small cells) or relax from several starts; a single relaxation from one registry is a guess, not a minimum.

## Build

```bash
# 1. list terminations and lattice matches (writes nothing)
uv run scripts/build_interface.py LPSC_relaxed.vasp Li_relaxed.vasp \
    --sub-miller 1 0 0 --film-miller 1 0 0 --max-area 300
# 2. write the chosen candidates
uv run scripts/build_interface.py LPSC_relaxed.vasp Li_relaxed.vasp \
    --sub-miller 1 0 0 --film-miller 1 0 0 --termination 1 --match 3 --match 7 \
    --sub-layers 4 --film-layers 5 --gap 2.2 --vacuum 15 --out models/candidates/iface
# 3. audit every candidate
uv run scripts/audit_structure.py models/candidates/iface/t1_m3/POSCAR --json models/candidates/iface/t1_m3/audit.json
```

`interface_summary.json` records sources, Miller indices, termination labels, the match vectors, strain, area and atoms per side. Copy the decisive numbers (strain on the film, area, atom count, gap, vacuum) into `models/model.md`.

If no match appears, raise `--max-area` before loosening `--max-length-tol`; a looser tolerance just hides strain. If every acceptable match exceeds ~400 atoms, consider a smaller-cell model that answers a narrower question (e.g. a thin Li film, fewer electrolyte layers, or a bulk reaction model), and say so.

## Checks specific to interfaces

- Strain is reported for the film and is small enough for the claim; the substrate lattice is the relaxed bulk value.
- Both terminations are stated, with their stoichiometry and whether the electrolyte slab is charge-balanced and non-polar on its own.
- No contacts across the interface below the audit threshold at build time; no atom of one phase inside the other.
- With vacuum: dipole across the cell considered (`knowledge/periodic-electrostatics.md`); with a sandwich: both interfaces equivalent or the difference stated.
- After relaxation: `check_distances.py CONTCAR --reference <bulk>` to see whether interfacial chemistry changed (S–Li short contacts are expected at a reactive Li|sulfide interface; S–S bonds forming are a result to report, not an error).
- Energies use references computed with identical settings and the same strain treatment:
  - sandwich (two equivalent interfaces): `γ_int = (E_iface − n_A·E_A − n_B·E_B) / (2·Area)` with strained-bulk references;
  - one interface with vacuum: work of adhesion `W_ad = (E_slabA + E_slabB − E_iface) / Area`, each slab computed alone in the same cell.

## What an interface model cannot show by itself

A 0 K relaxed interface shows a local minimum of one registry at one composition. It does not show interphase growth kinetics, the composition of an SEI formed under cycling, or Li transport rates; those need sampling (AIMD/MLP-MD), several compositions, or explicit interphase phases. Say which of these the model does and does not address.
