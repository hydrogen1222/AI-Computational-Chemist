#!/usr/bin/env python3
"""Repository consistency: every skill is well-formed, every explicit path
reference resolves, and removed components do not creep back in.

Run: python tests/repo_consistency_test.py
"""
from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REMOVED_PATHS = [
    "aicc", "benchmark", "STRUCTURE.md", "FORK_DISABLED_SKILLS.txt", "agent.md",
    "procedures/review-response/examples", "procedures/review-response/manifest.yaml",
    "tools/catmap", "tools/gromacs", "tools/report", "tools/plotting",
    "tools/chargemol", "tools/hpc-submit", "tools/rsess",
    "procedures/research-orchestrator", "procedures/comp-chem-workflow",
]
REMOVED_STRINGS = [
    "tools/catmap", "tools/gromacs", "tools/report", "tools/plotting",
    "tools/chargemol", "tools/vasp/scripts/batch_", "tools/vasp/scripts/charge_report",
    "FORK_DISABLED", "aicc doctor", "aicc skill", "hpc-submit", "rsess",
    "research-orchestrator", "comp-chem-workflow", "STRUCTURE.md",
    "ppt_figures", "_report_cn.md", "periodic_cdft/comparison",
    "this fork", "Fork rule", "docs/locked_parameters", "cluster guide",
]
TEXT_SUFFIXES = {".md", ".py", ".sh", ".yml", ".yaml", ".json", ".txt"}
REF_RE = re.compile(r"`((?:procedures|tools|knowledge)/[^`\s<>*]+\.(?:md|py))`")
FRONTMATTER_RE = re.compile(r"\A---\nname: ([^\n]+)\ndescription: ([^\n]+)\n", re.S)


def skill_files() -> list[Path]:
    return sorted((ROOT / "procedures").glob("*/SKILL.md")) + sorted((ROOT / "tools").glob("*/SKILL.md"))


def live_text_files() -> list[Path]:
    files = [ROOT / p for p in ("AGENTS.md", "README.md", "install.sh")]
    for folder in ("procedures", "tools", "knowledge", ".github"):
        files += [p for p in (ROOT / folder).rglob("*") if p.is_file() and p.suffix in TEXT_SUFFIXES]
    return files


class RepoConsistency(unittest.TestCase):
    def test_removed_paths_stay_removed(self):
        for rel in REMOVED_PATHS:
            with self.subTest(path=rel):
                self.assertFalse((ROOT / rel).exists(), f"removed path is back: {rel}")

    def test_no_text_mentions_removed_components(self):
        hits = []
        for path in live_text_files():
            for n, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                for term in REMOVED_STRINGS:
                    if term in line:
                        hits.append(f"{path.relative_to(ROOT)}:{n}: {term}")
        self.assertEqual([], hits, "\n".join(hits))

    def test_skill_frontmatter(self):
        for skill in skill_files():
            with self.subTest(skill=str(skill.relative_to(ROOT))):
                m = FRONTMATTER_RE.match(skill.read_text(encoding="utf-8"))
                self.assertIsNotNone(m, "SKILL.md must start with name/description frontmatter")
                self.assertEqual(m.group(1).strip(), skill.parent.name)
                self.assertLessEqual(len(m.group(2)), 1024)

    def test_explicit_references_resolve(self):
        broken = []
        for path in live_text_files():
            if path.suffix != ".md":
                continue
            for target in REF_RE.findall(path.read_text(encoding="utf-8", errors="replace")):
                if not (ROOT / target).exists():
                    broken.append(f"{path.relative_to(ROOT)} -> {target}")
        self.assertEqual([], broken, "\n".join(broken))

    def test_skill_relative_references_resolve(self):
        rel = re.compile(r"`((?:references|scripts)/[^`\s<>*]+\.(?:md|py))`")
        broken = []
        for skill in skill_files():
            for path in [skill, *skill.parent.glob("references/*.md")]:
                for target in rel.findall(path.read_text(encoding="utf-8", errors="replace")):
                    if not (skill.parent / target).exists():
                        broken.append(f"{path.relative_to(ROOT)} -> {target}")
        self.assertEqual([], broken, "\n".join(broken))

    def test_no_empty_placeholder_folders(self):
        lonely = [d for d in (ROOT / "tools").glob("*/examples")
                  if [p.name for p in d.iterdir()] == ["README.md"]]
        self.assertEqual([], lonely, "examples/ folders with only a README")

    def test_every_script_answers_help(self):
        failures = []
        for script in sorted((ROOT / "tools").glob("*/scripts/*.py")):
            if script.name in {"layout.py", "covalent_radii.py"}:
                continue  # import-only modules
            r = subprocess.run([sys.executable, str(script), "--help"], capture_output=True,
                               text=True, timeout=120, cwd=ROOT)
            if r.returncode != 0 or "Traceback" in r.stderr:
                failures.append(f"{script.relative_to(ROOT)}: rc={r.returncode} {r.stderr[-200:]}")
        self.assertEqual([], failures, "\n".join(failures))

    def test_researcher_owns_job_execution(self):
        doc = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("researcher submits, monitors, cancels and restarts", doc)


if __name__ == "__main__":
    unittest.main()
