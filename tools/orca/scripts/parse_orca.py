#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
"""Summarize an ORCA output file (stdlib only).

Usage: parse_orca.py JOB.out

Reports: ORCA version, normal or error termination (with the error lines), SCF
convergence messages, optimization status, final single point energy, imaginary
frequencies, thermochemistry lines, and <S**2> for unrestricted runs.

Exit code: 0 = clean, 1 = finished with issues (unconverged SCF or optimization,
imaginary modes, spin contamination), 2 = error termination or incomplete run.
"""
import re
import sys

HARTREE_EV = 27.211386

ERROR_PATTERNS = [
    r"INPUT ERROR", r"UNRECOGNIZED OR DUPLICATED KEYWORD", r"error termination",
    r"ABORTING", r"FATAL ERROR", r"Please increase MaxCore", r"OUT OF MEMORY",
    r"has to be called with full pathname", r"Unknown identifier", r"CANNOT OPEN FILE",
    r"There are no main basis functions", r"corrupt or from a different ORCA version",
    r"Input geometry does not match",
]


def main():
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(2)
    try:
        text = open(sys.argv[1], errors="replace").read()
    except OSError as exc:
        sys.exit(f"parse_orca: cannot read {sys.argv[1]}: {exc}")
    lines = text.splitlines()
    issues, fatal = [], False

    m = re.search(r"Program Version\s+(\S+)", text)
    print(f"File: {sys.argv[1]}")
    print(f"ORCA version: {m.group(1) if m else 'not found'}")

    # The echoed input: "|  1> ! B3LYP ..." lines
    echoed = [re.sub(r"^\|\s*\d+>\s?", "", l) for l in lines if re.match(r"^\|\s*\d+>", l)]
    simple = " ".join(l.split("#")[0][1:] for l in echoed if l.strip().startswith("!")).upper().split()
    is_opt = any(k in simple for k in ("OPT", "TIGHTOPT", "LOOSEOPT", "VERYTIGHTOPT", "NORMALOPT",
                                       "COPT", "OPTTS", "SLOPPYOPT"))
    is_freq = any(k in simple for k in ("FREQ", "NUMFREQ", "ANFREQ"))
    mult = None
    for l in echoed:
        mm = re.match(r"\s*\*\s*(?:xyz|xyzfile|int|gzmt)\w*\s+(-?\d+)\s+(\d+)", l, re.I)
        if mm:
            mult = int(mm.group(2))
            break
    if simple:
        print(f"Keywords: {' '.join(simple)}")

    normal = "ORCA TERMINATED NORMALLY" in text
    err_lines, used = [], set()
    for n, l in enumerate(lines):
        if n in used or not any(re.search(p, l, re.I) for p in ERROR_PATTERNS):
            continue
        block = [l.strip()]
        for k in range(n + 1, min(n + 3, len(lines))):
            x = lines[k].strip()
            if x and not x.startswith("!!!"):
                block.append(x)
                used.add(k)
        err_lines.append(" | ".join(block))
    if normal:
        print("Termination: ORCA TERMINATED NORMALLY")
    else:
        fatal = True
        print("Termination: NOT NORMAL (no 'ORCA TERMINATED NORMALLY')")
    for e in dict.fromkeys(err_lines):
        print(f"  error line: {e}")

    scf_ok = len(re.findall(r"SCF CONVERGED AFTER", text, re.I))
    scf_bad = [l.strip() for l in lines
               if re.search(r"not converged", l, re.I) and re.search(r"SCF|wavefunction", l, re.I)]
    print(f"SCF: {scf_ok} converged cycle(s) reported")
    if scf_bad:
        issues.append("SCF not converged at least once: " + scf_bad[-1])

    if is_opt:
        if "THE OPTIMIZATION HAS CONVERGED" in text:
            print("Optimization: converged")
        elif re.search(r"did not converge but reached the\s+maximum number of optimization", text, re.I):
            issues.append("optimization hit the cycle limit; restart from <job>.xyz")
        else:
            issues.append("optimization requested but no convergence message found")

    energies = re.findall(r"FINAL SINGLE POINT ENERGY\s+(-?\d+\.\d+)", text)
    if energies:
        e = float(energies[-1])
        print(f"Final single point energy: {e:.8f} Eh ({e * HARTREE_EV:.6f} eV)  [last of {len(energies)}]")
    elif normal:
        issues.append("no FINAL SINGLE POINT ENERGY line")

    if is_freq or "VIBRATIONAL FREQUENCIES" in text:
        idx = text.rfind("VIBRATIONAL FREQUENCIES")
        freqs = []
        if idx >= 0:
            for l in text[idx:].splitlines()[1:]:
                mf = re.match(r"\s*\d+:\s+(-?\d+\.\d+)\s+cm\*\*-1", l)
                if mf:
                    freqs.append(float(mf.group(1)))
                elif freqs and not l.strip():
                    break
        imag = [f for f in freqs if f < 0]
        print(f"Frequencies: {len(freqs)} printed, {len(imag)} imaginary"
              + (f" ({', '.join(f'{f:.1f}' for f in imag)} cm-1)" if imag else ""))
        if not freqs:
            issues.append("frequency job but no frequencies found")
        elif imag:
            issues.append(f"{len(imag)} imaginary mode(s); a minimum has none")
        for label in ("Zero point energy", "Total thermal energy", "Total enthalpy",
                      "Final Gibbs free energy"):
            found = [l.strip() for l in lines if l.strip().lower().startswith(label.lower())]
            if found:
                print(f"  {found[-1]}")

    s2 = re.findall(r"Expectation value of <S\*\*2>\s*:\s*(-?\d+\.\d+)", text)
    if s2 and mult and mult > 1:
        s = (mult - 1) / 2
        ideal = s * (s + 1)
        val = float(s2[-1])
        dev = 100 * (val - ideal) / ideal
        print(f"<S**2>: {val:.4f} (ideal {ideal:.4f} for multiplicity {mult}, {dev:+.1f}%)")
        if abs(dev) > 10:
            issues.append(f"spin contamination: <S**2> {val:.4f} vs ideal {ideal:.4f}")

    if fatal:
        print("RESULT: FAILED - error termination or incomplete; see errors.md")
        for x in issues:
            print(f"  ISSUE: {x}")
        sys.exit(2)
    if issues:
        print("RESULT: FINISHED WITH ISSUES - do not use the results yet")
        for x in issues:
            print(f"  ISSUE: {x}")
        sys.exit(1)
    print("RESULT: OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
