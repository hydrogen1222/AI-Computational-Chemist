#!/usr/bin/env python3
"""Fast, stdlib-only smoke checks for the modeling-first AICC CLI and routing."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "aicc" / "aicc.py"


class ModelingFirstSmokeTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )

    def test_minimal_cli(self) -> None:
        cmd = self.run_cli("--help")
        self.assertEqual(cmd.returncode, 0, cmd.stderr)
        self.assertIn("skill", cmd.stdout)
        self.assertIn("doctor", cmd.stdout)
        self.assertNotIn("task", cmd.stdout)
        self.assertNotIn("job", cmd.stdout)

    def test_doctor(self) -> None:
        cmd = self.run_cli("doctor", "--json")
        self.assertEqual(cmd.returncode, 0, cmd.stderr)
        doc = json.loads(cmd.stdout)
        self.assertTrue(doc["healthy"])
        self.assertIn("scientific-modeling", doc["skills"])
        self.assertIn("structure-prep", doc["skills"])
        self.assertNotIn("research-orchestrator", doc["skills"])

    def test_modeling_routing_no_project_state(self) -> None:
        for relative in (
            "AGENTS.md",
            "procedures/scientific-modeling/SKILL.md",
            "tools/structure-prep/SKILL.md",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("model", text.lower())
            self.assertNotIn("SI/Major/Vice team", text)
        self.assertFalse((ROOT / "procedures/research-orchestrator").exists())
        self.assertFalse((ROOT / "procedures/comp-chem-workflow").exists())

    def test_skill_help(self) -> None:
        cmd = self.run_cli("skill", "--help")
        self.assertEqual(cmd.returncode, 0, cmd.stderr)


if __name__ == "__main__":
    unittest.main()
