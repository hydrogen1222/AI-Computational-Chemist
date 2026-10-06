#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
"""Check a VASP run directory against the project's locked parameters (stdlib only).

Usage: check_locked_params.py RUNDIR --lock LOCKFILE [--profile NAME]

The lock file is the project's `locked_parameters.md`, signed off by the user. It is
plain markdown: each `## <profile>` heading starts a profile (the first one is the
default), and each line of the form `- KEY = VALUE` inside it is a locked value.
Every other line is free text for the human reader (the reason, the convergence
test it came from). Special keys:

  inherit       = <profile>     take all values of another profile first
  KSPACING_MAX  = 0.25          largest allowed k-point spacing, in 1/Angstrom with
                                VASP's KSPACING convention (2*pi included); denser
                                meshes always pass
  KPOINTS_MODE  = Gamma         required automatic-mesh mode (Gamma or Monkhorst)
  POTCAR        = Li_sv P S Cl  required POTCAR label for each element; elements
                                not listed fail
  POTCAR_FAMILY = PAW_PBE       required first word of every TITEL line

Every other key is an INCAR tag. It must appear explicitly in the run's INCAR with the
same value (numbers compared numerically, logicals as true/false, text ignoring
case). Tags that change the physics (functional, Hamiltonian, smearing, cutoff; see
PHYSICS_TAGS) may only appear in the INCAR if the chosen profile locks them.

Explicit k-point lists and line-mode KPOINTS (band structures) are not checked
against KSPACING_MAX; the script says so.

Exit code: 0 = matches the lock, 1 = mismatch (do not submit), 2 = usage or read error.
"""
import math
import os
import re
import sys

SPECIAL_KEYS = {"INHERIT", "KSPACING_MAX", "KPOINTS_MODE", "POTCAR", "POTCAR_FAMILY"}

# Tags that change the physics of the energy surface. If present in the INCAR they
# must be locked by the profile, so a hybrid or +U run cannot slip in under a PBE lock.
PHYSICS_TAGS = {
    "GGA", "METAGGA", "XC", "LHFCALC", "HFSCREEN", "AEXX", "AGGAX", "AGGAC", "ALDAC",
    "IVDW", "LDAU", "LDAUTYPE", "LDAUL", "LDAUU", "LDAUJ", "LUSE_VDW", "LSORBIT",
    "ISMEAR", "SIGMA", "ENCUT", "PREC",
}


def die(msg):
    print(f"check_locked_params: {msg}", file=sys.stderr)
    sys.exit(2)


def parse_lock(path):
    if not os.path.isfile(path):
        die(f"lock file not found: {path}")
    profiles, order, current = {}, [], None
    for raw in open(path, encoding="utf-8"):
        line = raw.strip()
        m = re.match(r"^##\s+(\S+)", line)
        if m:
            current = m.group(1).lower()
            profiles.setdefault(current, {})
            order.append(current)
            continue
        m = re.match(r"^[-*]\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)\s*$", line)
        if m and current is not None:
            value = m.group(2).split("#")[0].strip()
            profiles[current][m.group(1).upper()] = value
    if not order:
        die(f"no '## <profile>' section found in {path}")
    return profiles, order


def resolve(profiles, name, seen=()):
    if name not in profiles:
        die(f"profile '{name}' not in lock file (have: {', '.join(profiles)})")
    if name in seen:
        die(f"inherit loop through profile '{name}'")
    own = profiles[name]
    out = {}
    if "INHERIT" in own:
        out.update(resolve(profiles, own["INHERIT"].lower(), seen + (name,)))
    out.update({k: v for k, v in own.items() if k != "INHERIT"})
    return out


def parse_incar(path):
    tags = {}
    for line in open(path, errors="ignore"):
        line = line.split("#")[0].split("!")[0]
        for part in line.split(";"):
            if "=" in part:
                k, v = part.split("=", 1)
                tags[k.strip().upper()] = v.strip()
    return tags


def norm_logical(v):
    t = v.strip().strip(".").upper()
    if t in ("TRUE", "T"):
        return True
    if t in ("FALSE", "F"):
        return False
    return None


def same_value(locked, actual):
    a, b = norm_logical(locked), norm_logical(actual)
    if a is not None or b is not None:
        return a == b
    lt, at = locked.split(), actual.split()
    if len(lt) == len(at):
        try:
            return all(math.isclose(float(x), float(y), rel_tol=1e-6, abs_tol=1e-12)
                       for x, y in zip(lt, at))
        except ValueError:
            pass
    return " ".join(lt).upper() == " ".join(at).upper()


def read_poscar(path):
    lines = [l.rstrip("\n") for l in open(path, errors="ignore")]
    scale = float(lines[1].split()[0])
    raw = [[float(x) for x in lines[i].split()[:3]] for i in (2, 3, 4)]
    if scale < 0:  # a negative scale is the target cell volume
        scale = (abs(scale) / abs(det(raw))) ** (1 / 3)
    return [[x * scale for x in row] for row in raw]


def det(m):
    return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def recip_lengths(lat):
    """|b_i| including the 2*pi factor, in 1/Angstrom."""
    v = det(lat)
    out = []
    for i in range(3):
        c = cross(lat[(i + 1) % 3], lat[(i + 2) % 3])
        out.append(2 * math.pi * math.sqrt(sum(x * x for x in c)) / abs(v))
    return out


def read_kpoints(path):
    lines = [l.strip() for l in open(path, errors="ignore") if l.strip()]
    if len(lines) < 3:
        return {"mode": "unreadable"}
    try:
        n = int(float(lines[1].split()[0]))
    except (IndexError, ValueError):
        return {"mode": "unreadable"}
    head = lines[2][:1].lower()
    if n != 0:
        return {"mode": "line" if head == "l" else "explicit"}
    if head == "g":
        mode = "gamma"
    elif head == "m":
        mode = "monkhorst"
    else:
        return {"mode": "auto-length"}
    try:
        mesh = [int(float(x)) for x in lines[3].split()[:3]]
    except (IndexError, ValueError):
        return {"mode": "unreadable"}
    return {"mode": mode, "mesh": mesh}


def potcar_titels(path):
    out = []
    for line in open(path, errors="ignore"):
        if "TITEL" in line:
            out.append(line.split("=", 1)[1].split())
    return out


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if args else 2)
    rundir, lock, profile = None, None, None
    i = 0
    while i < len(args):
        if args[i] == "--lock" and i + 1 < len(args):
            lock = args[i + 1]
            i += 2
        elif args[i] == "--profile" and i + 1 < len(args):
            profile = args[i + 1].lower()
            i += 2
        elif rundir is None:
            rundir = args[i]
            i += 1
        else:
            die(f"unexpected argument {args[i]}")
    if rundir is None or lock is None:
        die("usage: check_locked_params.py RUNDIR --lock LOCKFILE [--profile NAME]")

    profiles, order = parse_lock(lock)
    profile = profile or order[0]
    locked = resolve(profiles, profile)
    fails, notes = [], []

    incar_path = os.path.join(rundir, "INCAR")
    if not os.path.isfile(incar_path):
        die(f"no INCAR in {rundir}")
    incar = parse_incar(incar_path)

    for key, value in locked.items():
        if key in SPECIAL_KEYS:
            continue
        if key not in incar:
            fails.append(f"{key}: locked to {value}, but not set in INCAR (set it explicitly)")
        elif not same_value(value, incar[key]):
            fails.append(f"{key}: INCAR has {incar[key]}, lock says {value}")
    for key in sorted(PHYSICS_TAGS & set(incar) - set(locked)):
        fails.append(f"{key} = {incar[key]} is set in INCAR but not locked in profile "
                     f"'{profile}'; it changes the physics, so it needs a locked profile")

    kmax = locked.get("KSPACING_MAX")
    kmode = locked.get("KPOINTS_MODE")
    if kmax is not None or kmode is not None:
        poscar = os.path.join(rundir, "POSCAR")
        kpoints = os.path.join(rundir, "KPOINTS")
        if "KSPACING" in incar and not os.path.isfile(kpoints):
            if kmax is not None and float(incar["KSPACING"].split()[0]) > float(kmax) + 1e-9:
                fails.append(f"KSPACING = {incar['KSPACING']} is coarser than KSPACING_MAX = {kmax}")
            if kmode is not None:
                gamma = norm_logical(incar.get("KGAMMA", "TRUE"))
                if (kmode.lower().startswith("g")) != bool(gamma):
                    fails.append(f"KGAMMA = {incar.get('KGAMMA', '.TRUE. (default)')} "
                                 f"does not give KPOINTS_MODE = {kmode}")
        elif os.path.isfile(kpoints):
            kp = read_kpoints(kpoints)
            if kp["mode"] in ("gamma", "monkhorst"):
                if kmode is not None and not kp["mode"].startswith(kmode.lower()[:1]):
                    fails.append(f"KPOINTS mode is {kp['mode']}, lock says {kmode}")
                if kmax is not None:
                    if not os.path.isfile(poscar):
                        die(f"no POSCAR in {rundir}; needed to check the k-point spacing")
                    b = recip_lengths(read_poscar(poscar))
                    spacing = [bi / n for bi, n in zip(b, kp["mesh"])]
                    worst = max(spacing)
                    line = (f"k-point spacing per direction "
                            f"{', '.join(f'{s:.3f}' for s in spacing)} 1/A "
                            f"(mesh {'x'.join(map(str, kp['mesh']))})")
                    if worst > float(kmax) + 1e-6:
                        fails.append(f"{line}; coarsest {worst:.3f} > KSPACING_MAX {kmax}")
                    else:
                        notes.append(line)
            elif kp["mode"] in ("line", "explicit"):
                notes.append(f"KPOINTS is an {kp['mode']} list (band path or similar); "
                             "spacing not checked against the lock")
            else:
                fails.append(f"KPOINTS mode '{kp['mode']}' cannot be checked; use a Gamma or "
                             "Monkhorst mesh or KSPACING")
        else:
            fails.append("neither KPOINTS nor KSPACING present")

    if "POTCAR" in locked or "POTCAR_FAMILY" in locked:
        potcar = os.path.join(rundir, "POTCAR")
        if not os.path.isfile(potcar):
            fails.append("no POTCAR in the run directory; the lock checks POTCAR labels")
        else:
            want = {}
            for label in locked.get("POTCAR", "").split():
                want[label.split("_")[0]] = label
            family = locked.get("POTCAR_FAMILY")
            for titel in potcar_titels(potcar):
                if len(titel) < 2:
                    fails.append(f"unreadable TITEL line: {' '.join(titel)}")
                    continue
                fam, label = titel[0], titel[1]
                elem = label.split("_")[0]
                if family and fam.upper() != family.upper():
                    fails.append(f"POTCAR {label}: family {fam}, lock says {family}")
                if "POTCAR" in locked:
                    if elem not in want:
                        fails.append(f"POTCAR element {elem} ({label}) is not in the lock")
                    elif want[elem] != label:
                        fails.append(f"POTCAR for {elem} is {label}, lock says {want[elem]}")

    print(f"Lock: {lock}  profile: {profile}  run: {rundir}")
    for n in notes:
        print(f"  note: {n}")
    if fails:
        print("RESULT: MISMATCH - do not submit; fix the input or ask the user to change the lock")
        for f in fails:
            print(f"  FAIL: {f}")
        sys.exit(1)
    print("RESULT: OK - matches the lock")
    sys.exit(0)


if __name__ == "__main__":
    main()
