#!/usr/bin/env python3
"""Prevent retired orchestration and scheduler automation from leaking back in.

Run: python aicc/tests/retired_components_test.py
Keeps historical benchmark research files outside the active agent surface.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RETIRED_FOLDERS = [
    "procedures/research-orchestrator",
    "procedures/comp-chem-workflow",
    "procedures/research-overview-storytelling",
    "tools/hpc-submit",
    "tools/rsess",
]
RETIRED_FILES = [
    "benchmark/RUN_ALL.md",
    "tools/deepmd/scripts/run_deepmd_chain.py",
    "procedures/review-response/examples/toy-vacancy-pt-vs-au/response-workflow.md",
    "procedures/review-response/examples/toy-contradicts-au-vs-cu/response-workflow.md",
]
RETIRED_STRINGS = [
    "research-orchestrator",
    "comp-chem-workflow",
    "research-overview-storytelling",
    "hpc-submit",
    "tools/rsess",
    "run_deepmd_chain.py",
    "wait_for_job.sh",
    ".research/",
]
DOCUMENT_SUFFIXES = {".md", ".py", ".sh", ".yml", ".yaml", ".json", ".txt"}
SCOPED_FOLDERS = ["aicc", "procedures", "tools", "knowledge"]
ROOT_DOCS = ["AGENTS.md", "README.md", "STRUCTURE.md", "install.sh"]
REFERENCE_RE = re.compile(r"\`((?:procedures|tools|knowledge)/[^\` ]+\.(?:md|py))\`")


class RetirementIntegrity(unittest.TestCase):
    def test_retired_files_really_removed(self):
        for rel in RETIRED_FOLDERS + RETIRED_FILES:
            with self.subTest(path=rel):
                self.assertFalse((ROOT / rel).exists(), f"retired path remains: {rel}")

    def test_no_live_text_refers_to_retired_components(self):
        paths = [ROOT / p for p in ROOT_DOCS]
        for folder in SCOPED_FOLDERS:
            paths += [
                p for p in (ROOT / folder).rglob("*")
                if p.is_file() and p.suffix in DOCUMENT_SUFFIXES
                and "tests" not in p.relative_to(ROOT).parts
            ]
        violations = []
        for path in paths:
            data = path.read_text(encoding="utf-8", errors="replace")
            for line_no, line in enumerate(data.splitlines(), 1):
                for term in RETIRED_STRINGS:
                    if term.lower() in line.lower():
                        violations.append(f"{path.relative_to(ROOT)}:{line_no}: {term}")
        self.assertEqual([], violations, "retired paths or protocols referenced:\n" + "\n".join(violations))

    def test_skill_explicit_references_exist(self):
        errors = []
        for parent in ("procedures", "tools"):
            for skill in (ROOT / parent).glob("*/SKILL.md"):
                text = skill.read_text(encoding="utf-8", errors="replace")
                for target in REFERENCE_RE.findall(text):
                    if "<" in target or ">" in target:
                        continue
                    if not (ROOT / target).is_file():
                        errors.append(f"{skill.relative_to(ROOT)} -> {target}")
        self.assertEqual([], errors, "broken skill links:\n" + "\n".join(errors))

    def test_user_owns_execution(self):
        doc = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("The researcher submits, monitors, cancels", doc)
        self.assertIn("manual job scripts", doc)
        self.assertTrue((ROOT / "procedures/scientific-modeling/SKILL.md").is_file())
        self.assertTrue((ROOT / "procedures/batch-postprocessing/SKILL.md").is_file())
        self.assertTrue((ROOT / "tools/vasp/scripts/batch_bader.py").is_file())


if __name__ == "__main__":
    unittest.main()
