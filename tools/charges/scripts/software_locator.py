#!/usr/bin/env python3
"""Conservative discovery of local computational chemistry executables.

Discovery does not execute binaries or contact remote services. Resolution:
explicit path -> environment override -> PATH -> bounded known install roots.
If multiple non-PATH candidates exist, report ambiguity instead of guessing.
Other engine skills may reuse find_executable() with their own candidate names.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
from typing import Iterable

EXE_NAMES = {
    "chargemol": ("chargemol", "Chargemol_09_26_2017_linux_parallel",
                  "Chargemol_09_26_2017_linux_serial"),
    "bader": ("bader", "bader_linux", "bader.exe"),
    "chgsum": ("chgsum.pl",),
}
ENV_NAMES = {
    "chargemol": ("AICC_CHARGEMOL_BIN", "CHARGEMOL_BIN", "CHARGEMOL_EXE"),
    "bader": ("AICC_BADER_BIN", "BADER_BIN"),
    "chgsum": ("AICC_CHGSUM_BIN", "CHGSUM_BIN"),
}
SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".cache",
    "share", "doc", "docs", "include", "man", "lib", "lib64", "site-packages",
    "src", "source", "sources", "build", "test", "tests", "benchmark", "benchmarks",
}
MAX_DEPTH = 5
MAX_VISITED_DIRS = 3500


class DiscoveryError(ValueError):
    """Not found, ambiguous, or explicitly misconfigured executable/library."""


def roots() -> list[Path]:
    home = Path.home()
    bases = [
        home / "apps", Path("/opt/apps"), Path("/opt/chargemol"),
        home / ".local" / "bin", home / "bin",
        Path("/usr/local/bin"), Path("/usr/local/apps"),
    ]
    custom = os.getenv("AICC_SOFTWARE_ROOTS", "")
    bases.extend(Path(x).expanduser() for x in custom.split(os.pathsep) if x.strip())
    return list(dict.fromkeys(x.resolve() for x in bases if x.is_dir()))


def walk_bounded(base: Path) -> Iterable[Path]:
    """Search only within known installation roots; never scan whole / or $HOME."""
    visited = 0
    for here, subdirs, names in os.walk(base, followlinks=False):
        visited += 1
        if visited > MAX_VISITED_DIRS:
            return
        p = Path(here)
        depth = len(p.relative_to(base).parts)
        if depth >= MAX_DEPTH:
            subdirs[:] = []
        else:
            subdirs[:] = sorted(x for x in subdirs if x not in SKIP_DIRS and not x.startswith("."))
        for filename in sorted(names):
            yield p / filename


def is_executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def match_name(tool: str, name: str) -> bool:
    if name in EXE_NAMES[tool]:
        return True
    if tool == "chargemol":
        return bool(re.fullmatch(r"Chargemol_[0-9_]+_linux_(parallel|serial)", name, flags=re.I))
    return False


def find_executable(tool: str, explicit: str | None = None) -> Path:
    """Resolve one executable; all failures are actionable, not silent fallback."""
    if tool not in EXE_NAMES:
        raise DiscoveryError(f"unknown software: {tool}")
    if explicit:
        candidate = Path(explicit).expanduser()
        if candidate.is_file():
            if not is_executable(candidate):
                raise DiscoveryError(f"{tool} binary exists but is not executable: {candidate}")
            return candidate.resolve()
        looked_up = shutil.which(explicit)
        if looked_up:
            return Path(looked_up).resolve()
        raise DiscoveryError(f"{tool} binary specified but not found: {explicit}")

    for variable in ENV_NAMES[tool]:
        value = os.getenv(variable)
        if value:
            # A misconfigured explicit environment variable should not be
            # silently superseded by a different installation.
            return find_executable(tool, value)

    for name in EXE_NAMES[tool]:
        resolved = shutil.which(name)
        if resolved:
            return Path(resolved).resolve()

    hits = set()
    for base in roots():
        for candidate in walk_bounded(base):
            if match_name(tool, candidate.name) and is_executable(candidate):
                hits.add(candidate.resolve())
    if len(hits) == 1:
        return next(iter(hits))
    if len(hits) > 1:
        paths = "\n  ".join(str(x) for x in sorted(hits))
        raise DiscoveryError(
            f"multiple {tool} executables found; select one with --binary or "
            f"{ENV_NAMES[tool][0]}:\n  {paths}"
        )
    raise DiscoveryError(
        f"{tool} executable not found in PATH or common application directories "
        f"(~/apps, /opt/apps, ~/.local/bin, etc.). Set {ENV_NAMES[tool][0]} "
        "or provide an explicit path; you can add custom search roots with "
        "AICC_SOFTWARE_ROOTS."
    )


def valid_density_dir(path: Path) -> bool:
    # Actual Chargemol atomic density files are normally c2_*.txt.
    return (path.is_dir() and
            any(path.glob("c2_*.txt")))


def find_chargemol_densities(
    explicit: Path | None = None, executable: Path | None = None
) -> Path:
    if explicit is not None:
        p = explicit.expanduser().resolve()
        if not valid_density_dir(p):
            raise DiscoveryError(f"not a valid Chargemol atomic density library (c2_*.txt missing): {p}")
        return p
    for env in ("DDEC6_ATOMIC_DENSITIES_DIR", "AICC_CHARGEMOL_DENSITIES"):
        if os.getenv(env):
            return find_chargemol_densities(Path(os.environ[env]), executable)

    # Prefer a matching library beside the selected executable, not a
    # different installation's density set found elsewhere under ~/apps.
    if executable is not None:
        exe = executable.resolve()
        nearby = [exe.parent / "atomic_densities",
                  exe.parent.parent / "atomic_densities"]
        direct = sorted(set(p.resolve() for p in nearby if valid_density_dir(p)))
        if len(direct) == 1:
            return direct[0]
        if len(direct) > 1:
            raise DiscoveryError(
                "more than one reference library adjacent to this Chargemol executable; "
                "specify DDEC6_ATOMIC_DENSITIES_DIR or --atomic-densities"
            )

    candidate_roots = list(roots())
    seen = set()
    hits = set()
    for base in candidate_roots:
        if not base.is_dir():
            continue
        if base in seen:
            continue
        seen.add(base)
        if base.name == "atomic_densities" and valid_density_dir(base):
            hits.add(base.resolve())
        for candidate in [base / "atomic_densities",
                          base.parent / "atomic_densities"]:
            if valid_density_dir(candidate):
                hits.add(candidate.resolve())
        for folder in walk_bounded_dirs(base):
            if folder.name == "atomic_densities" and valid_density_dir(folder):
                hits.add(folder.resolve())
    if len(hits) == 1:
        return next(iter(hits))
    if len(hits) > 1:
        opts = "\n  ".join(str(x) for x in sorted(hits))
        raise DiscoveryError(
            "multiple Chargemol atomic density libraries found; select "
            f"--atomic-densities or DDEC6_ATOMIC_DENSITIES_DIR:\n  {opts}"
        )
    raise DiscoveryError(
        "Chargemol atomic_densities not found or c2_*.txt files missing; "
        "set DDEC6_ATOMIC_DENSITIES_DIR or use --atomic-densities."
    )


def walk_bounded_dirs(base: Path) -> Iterable[Path]:
    visited = 0
    for here, subdirs, _ in os.walk(base, followlinks=False):
        visited += 1
        if visited > MAX_VISITED_DIRS:
            return
        p = Path(here)
        if p.name == "atomic_densities":
            yield p
            subdirs[:] = []
            continue
        depth = len(p.relative_to(base).parts)
        if depth >= MAX_DEPTH:
            subdirs[:] = []
        else:
            subdirs[:] = sorted(x for x in subdirs if x not in SKIP_DIRS and not x.startswith("."))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tool", choices=sorted(EXE_NAMES))
    parser.add_argument("--binary")
    args = parser.parse_args()
    try:
        path = find_executable(args.tool, args.binary)
        print(f"{args.tool}: {path}")
        if args.tool == "chargemol":
            print(f"atomic densities: {find_chargemol_densities(executable=path)}")
    except DiscoveryError as exc:
        parser.exit(1, str(exc) + "\n")
