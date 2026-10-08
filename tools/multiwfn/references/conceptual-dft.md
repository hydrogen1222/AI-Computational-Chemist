# Conceptual DFT in Multiwfn: Fukui functions, dual descriptor, global indices

> Load this when: computing Fukui functions, the dual descriptor, condensed (atomic) Fukui indices, or global reactivity indices (vertical IP and EA, electronegativity, hardness, electrophilicity, nucleophilicity) for a molecule or cluster.

Sources: Multiwfn manual of the installed version (conceptual DFT section) and Sobereva's guide
http://sobereva.com/484 (in Chinese). Menu numbers below are from that guide; check them against
the installed version before scripting them.

## What it can and cannot tell you

Conceptual DFT describes how the electron density and energy respond when one electron is added or
removed, by finite differences between three calculations. It ranks sites within one molecule or
cluster for attack by nucleophiles or electrophiles in frontier-controlled reactions. It gives no
barriers, no reaction energies, and no kinetics. For a cluster cut from a solid, the result describes
the cluster; say so when the claim is about the solid.

## Three calculations at one geometry

| State | Electrons | Typical charge, multiplicity for a closed-shell neutral N |
|---|---|---|
| N | N | 0, 1 |
| N+1 | N+1 | -1, 2 |
| N-1 | N-1 | +1, 2 |

Rules:

1. **One fixed geometry and external potential.** For an isolated molecule, optimize/validate the
   N reference if appropriate; Opt+Freq at a minimum can be useful, but is not a
   universal prerequisite for a vertical finite-difference calculation. For
   VASP-derived crystal geometries or embedded clusters, use the validated
   **periodic parent geometry**; do not demand isolated-molecule Opt+Freq or
   silently relax the cluster into a different species. N, N+1 and N-1 are
   single points at exactly the same QM geometry. For an embedded cluster,
   all MM point-charge positions **and values**, capping ECPs, boundary
   definitions and the external embedding field must also remain identical.
   A charge-responsive/reconverged embedding field across states violates this
   fixed-external-potential comparison and requires a separate, clearly
   labeled model/observable.
2. **One level.** Same functional, dispersion, basis, grid, RI settings and solvent model for all three.
3. **Diffuse-function and electron-binding test.** f+ comes from the N+1 state.
   Test suitable diffuse functions consistently across the three states, where
   supported for every element. Diffuse functions do not make an unbound anion
   physical: inspect EA sign, orbital and spin-density localization, the response
   to adding/removing diffuse functions, and artificial boundary accumulation.
   A negative gas-phase EA, unstable charge localization or a descriptor strongly
   changing with cluster/basis size must be reported as an unresolved model limitation.
4. **Charge and spin state.** The example (0,1), (-1,2), (+1,2)
   applies only to a neutral closed-shell molecular N reference. Charged QM clusters
   have a different baseline charge; adding an electron decreases that baseline
   charge by one. For open-shell cases, enumerate scientifically plausible spin
   states, validate their SCF solutions and `<S**2>`, and record the selected
   N/N+1/N-1 states. Do not silently accept a Multiwfn default or compare
   inconsistent electronic states.
5. **Validate each run** like any other calculation (`tools/orca/references/validation.md` or the
   Gaussian equivalent): normal termination, converged SCF (the N+1 SCF is the one that most often
   fails), `<S**2>` for the open-shell states.

## Applicability to crystalline Na3PS4

The common `PS4^3-` fragment in vacuum is multiply charged and missing its
Madelung environment. A mathematically computable `N+1` wavefunction does
not prove that an added electron is physically bound in the bulk solid.

A parent crystal VASP calculation, carefully selected surface/intermediate or
a converged ORCA ionic-crystal embedded cluster must supply the structural
environment. The ORCA embedded-cluster checklist is in
`tools/orca/references/running.md`. Before any comparison to sodium
reduction or hydration/hydrolysis, test at least two sensible cluster
sizes/embedding fields and inspect whether the extra electron/hole is on
the chemically relevant PS4 region rather than an artificial edge.

Bulk periodic electron addition is a different model: a charged periodic
supercell can involve compensating backgrounds, finite-size electrostatics,
state delocalization and localization/spin choices. Do not equate a periodic
charged-cell energy difference or VASP band-edge value with the charged
molecular/embedded cluster IP or EA without an explicit common definition
and alignment scheme. There is no direct automatic conversion of VASP
PAW/Bader charge differences into molecular Hirshfeld Fukui indices.

For a site reaction: `f+` flags the electronic response to accepting
electrons and may inform nucleophilic approach to that site; `f-` flags
electron removal and may inform electrophilic approach. It is not itself
proof of the pathway of Na-induced P-S reduction or water-driven
hydrolysis, and the ranking of two reaction channels requires
independent periodic reaction/transition-state energies.

## Running it

For the **version documented by Sobereva's older guide**, the conceptual-DFT
main function is **22**. The current installed Multiwfn manual and its
interactive prompts are the authority: confirm these choices on a validated
small test before unattended/menu-script execution. Do not hard-code these
numbers merely because they appeared in a previous installation.

- **-2**: choose the quantum chemistry program used to generate the wavefunctions; select ORCA
  instead of the Gaussian default. The paths to ORCA and `orca_2mkl` are set in Multiwfn's
  `settings.ini` (check the exact entry names in the installed version).
- **1**: write the three inputs (`N.inp`, `N+1.inp`, `N-1.inp` for ORCA) from a template, and run them
  if the program path is set. The built-in template level is B3LYP/6-31G*, which is not the project's
  level: edit the template, or write the three inputs yourself from the project's validated level.
- **2**: global and condensed indices printed as text.
- **3**: grid data (cube files) of f+, f-, f0 and the dual descriptor for plotting.

Recommended practice in this fork: create/version-control the three **approved**
ORCA inputs explicitly, rather than blindly accepting generated templates. If
Multiwfn generates starter inputs, inspect and fix their electronic states,
functional, basis, embedding field and filenames before using the normal route (`tools/orca/scripts/check_orca_input.py`, the machine's launcher,
`tools/orca/scripts/parse_orca.py`) so every run is checked. Automatic calling from inside Multiwfn
skips those checks. Then give Multiwfn the three wavefunction files under the names it expects
(the guide uses `N.wfn`, `N+1.wfn`, `N-1.wfn`; follow the installed manual).

## Definitions (finite differences, vertical)

With E(N), E(N+1), E(N-1) the three total energies and ρ the electron densities:

- vertical ionization potential IP = E(N-1) - E(N)
- vertical electron affinity EA = E(N) - E(N+1)
- Mulliken electronegativity χ = (IP + EA) / 2; chemical potential μ = -χ
- hardness η: the literature uses both η = IP - EA and η = (IP - EA) / 2. The electrophilicity index
  ω = μ² / (2η) changes by a factor of 2 between them. Copy the formula Multiwfn prints into the
  record and never mix values from different conventions.
- nucleophilicity index N = E_HOMO(molecule) - E_HOMO(tetracyanoethylene). Multiwfn's built-in TCE
  HOMO is a B3LYP/6-31G* value. At another level, compute TCE at the project level and use that.
- f+(r) = ρ(N+1) - ρ(N): where an added electron goes; large f+ marks sites attacked by nucleophiles.
- f-(r) = ρ(N) - ρ(N-1): where an electron is removed from; large f- marks sites attacked by electrophiles.
- f0 = (f+ + f-) / 2: radical attack.
- dual descriptor Δf = f+ - f-: positive where the site accepts electrons (nucleophilic attack),
  negative where it donates (electrophilic attack).

Condensed indices must state the population scheme and sign convention.
For electron populations `P_A`: `f_A+ = P_A(N+1)-P_A(N)`, and
`f_A- = P_A(N)-P_A(N-1)`. For net atomic charges `q_A`, the signs
reverse accordingly: `f_A+ = q_A(N)-q_A(N+1)` and
`f_A- = q_A(N-1)-q_A(N)`. Never silently subtract three charge
columns as though they were electron-population columns.

**Ordinary Hirshfeld** is the declared reference partition in this fork
(and is useful for reproducing the original Multiwfn tutorial).
Hirshfeld-I may be added as a **separate, labeled** sensitivity check
if the installed Multiwfn version and files support it; it does not
automatically make condensed Fukui values more physically correct.
Comparison among schemes tests robustness, not equality of values.
If only charge/spin density grids from VASP are available, do not call
Bader finite differences “Hirshfeld” indices.

## Checks before using the numbers

- For a **complete all-atom** partition of the QM region and a consistent
  electron count, each condensed `f+`, `f-`, and `f0` should sum to
  approximately 1 and the dual descriptor to approximately 0. This is
  bookkeeping, **not evidence of physical validity**: a mismatched sum
  warrants checking charge definitions, atom mapping, missing regions
  (including cECP/MM contributions), file/state order, and partition
  implementation.
- **EA sign and bound-state test.** For an isolated system, negative vertical
  EA is a warning that the added electron may be unbound; a finite Gaussian
  basis can nonetheless spuriously trap it. Embedding shifts energies and
  changes interpretation, so do not use the gas-phase EA sign alone as a
  universal solid-state bound-state criterion. Check charge/spin localization,
  boundary leakage, basis/embedding convergence and what energy reference
  was used before accepting `f+` or the dual descriptor.
- Small negative condensed Fukui values can occur; report them as computed, never drop or reset them.
- Compare sites within one molecule. Comparing absolute values across molecules needs the same
  level, basis and charge state for all.
- Records: level of theory, basis (with or without diffuse functions), charges and multiplicities of
  the three states, which state was chosen for open-shell ions and why, Multiwfn version, menu path,
  the hardness convention, and isovalues for every Fukui or Δf figure.
- Preserve upstream ORCA version, Multiwfn version/build and manual revision,
  converted file format/provenance, executable/menu choices, same-geometry
  proof (e.g. coordinate hashes), external embedding data and identity,
  full per-atom charge table, and any caveat about unbound/edge states.
