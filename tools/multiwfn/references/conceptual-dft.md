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

1. **One geometry.** Optimize and validate the N state (Opt+Freq, no imaginary modes). N+1 and N-1
   are single points at exactly that geometry (vertical). Never re-optimize the ions.
2. **One level.** Same functional, dispersion, basis, grid, RI settings and solvent model for all three.
3. **Diffuse functions for the anion.** f+ comes from the N+1 state. Without diffuse functions the
   added electron is squeezed into the valence space. Use a diffuse basis (e.g. def2-TZVPD or
   ma-def2-TZVP) for all three calculations when f+, EA, or the dual descriptor matter.
4. **Open-shell N.** Multiwfn's default charges and multiplicities assume a closed-shell neutral
   molecule (0 1, -1 2, 1 2). For a radical (for example a neutral doublet), N+1 and N-1 have an even
   electron count and may be singlet or triplet: compute both, use the lower-energy state, and record
   the choice. Enter the charges and multiplicities explicitly when Multiwfn asks; never accept the
   closed-shell default for an open-shell system.
5. **Validate each run** like any other calculation (`tools/orca/references/validation.md` or the
   Gaussian equivalent): normal termination, converged SCF (the N+1 SCF is the one that most often
   fails), `<S**2>` for the open-shell states.

## Running it

Multiwfn main function **22** (conceptual DFT):

- **-2**: choose the quantum chemistry program used to generate the wavefunctions; select ORCA
  instead of the Gaussian default. The paths to ORCA and `orca_2mkl` are set in Multiwfn's
  `settings.ini` (check the exact entry names in the installed version).
- **1**: write the three inputs (`N.inp`, `N+1.inp`, `N-1.inp` for ORCA) from a template, and run them
  if the program path is set. The built-in template level is B3LYP/6-31G*, which is not the project's
  level: edit the template, or write the three inputs yourself from the project's validated level.
- **2**: global and condensed indices printed as text.
- **3**: grid data (cube files) of f+, f-, f0 and the dual descriptor for plotting.

Recommended practice in this fork: let Multiwfn write the inputs, but run the three jobs through the
normal route (`tools/orca/scripts/check_orca_input.py`, the machine's launcher,
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

Condensed (atomic) values use **Hirshfeld** charges, as recommended by the Multiwfn author.
Do not switch to Mulliken or NPA for condensed Fukui indices.

## Checks before using the numbers

- Each condensed Fukui function (f+, f-, f0) sums to 1 over all atoms, and the condensed dual
  descriptor sums to 0, within rounding. A different sum means the wrong files or the wrong order.
- **EA sign.** If EA < 0 (E(N+1) above E(N)), the extra electron is not bound in reality; f+ and Δf
  then depend on the basis. Report this next to every f+ or Δf value.
- Small negative condensed Fukui values can occur; report them as computed, never drop or reset them.
- Compare sites within one molecule. Comparing absolute values across molecules needs the same
  level, basis and charge state for all.
- Records: level of theory, basis (with or without diffuse functions), charges and multiplicities of
  the three states, which state was chosen for open-shell ions and why, Multiwfn version, menu path,
  the hardness convention, and isovalues for every Fukui or Δf figure.
