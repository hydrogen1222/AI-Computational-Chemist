"""Read-only collection diagnostics for `aicc doctor`."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from core.paths import collection_root


def discover_skills(root: Path) -> list[str]:
    names: list[str] = []
    for parent in ("procedures", "tools"):
        root_dir = root / parent
        if root_dir.is_dir():
            names.extend(p.name for p in root_dir.iterdir() if (p / "SKILL.md").is_file())
    return sorted(names)


def build_report() -> dict[str, Any]:
    root = collection_root()
    skills = discover_skills(root)
    checks = {
        "collection_root": root.is_dir(),
        "procedures": (root / "procedures").is_dir(),
        "tools": (root / "tools").is_dir(),
        "scientific_modeling": (root / "procedures/scientific-modeling/SKILL.md").is_file(),
        "structure_prep": (root / "tools/structure-prep/SKILL.md").is_file(),
        "python": sys.version_info >= (3, 11),
        "skills": bool(skills),
    }
    return {
        "schema_version": 2,
        "healthy": all(checks.values()),
        "collection_root": root.as_posix(),
        "uv": shutil.which("uv"),  # needed by launcher, but not by read-only skill access
        "python": sys.version.split()[0],
        "skill_count": len(skills),
        "skills": skills,
        "checks": checks,
    }


def register(subparsers: Any) -> None:
    parser = subparsers.add_parser("doctor", help="Check the local AICC skill collection")
    parser.add_argument("--json", action="store_true", help="Emit JSON diagnostics")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    report = build_report()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("AICC DOCTOR (modeling-first)")
        print(f"Collection  {report['collection_root']}")
        print(f"Python      {report['python']}")
        print(f"uv          {report['uv'] or '<not installed>'}")
        print(f"Skills      {report['skill_count']}")
        for name, passed in report["checks"].items():
            print(f"{'PASS' if passed else 'FAIL':<5}  {name}")
    return 0 if report["healthy"] else 1
