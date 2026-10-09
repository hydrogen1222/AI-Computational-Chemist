#!/usr/bin/env python3
"""Real subprocess smoke tests with isolated fake Bader commands (no scientific binaries)."""
from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools/vasp/scripts/batch_bader.py"


def make_case(root: Path, name: str, complete=True) -> Path:
    folder = root / name
    folder.mkdir()
    (folder / "POSCAR").write_text(
        "Mock NaP structure\n1.0\n5 0 0\n0 5 0\n0 0 5\n"
        "Na P\n1 1\nDirect\n0 0 0\n0.5 0.5 0.5\n"
    )
    (folder / "POTCAR").write_text(
        "TITEL = fake Na; ZVAL = 1.000\nTITEL = fake P; ZVAL = 5.000\n"
    )
    (folder / "CHGCAR").write_text("fake density")
    (folder / "AECCAR0").write_text("fake core")
    if complete:
        (folder / "AECCAR2").write_text("fake valence")
    return folder


ACF = """# X Y Z CHARGE MIN DIST ATOMIC VOL
-------------------------------------------------
1 0.0 0.0 0.0 0.7 0.1 10.0
2 0.5 0.5 0.5 4.5 0.1 15.0
-------------------------------------------------
VACUUM CHARGE: 0.0
"""


class BatchBaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.good = make_case(self.root, "ok")
        self.bad = make_case(self.root, "missing", complete=False)

    def run_tool(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), str(self.root), *map(str, args)],
                              capture_output=True, text=True, check=False)

    def test_dry_run_is_read_only_and_reports_missing(self):
        result = self.run_tool()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("READY", result.stdout)
        self.assertIn("missing AECCAR2", result.stdout)
        self.assertFalse((self.good / "postprocess").exists())
        self.assertFalse((self.root / "postprocess_summary").exists())

    def test_collect_existing_and_element_values(self):
        (self.good / "ACF.dat").write_text(ACF)
        result = self.run_tool("--collect-only", "--manifest", self.root / "case-list.txt")
        self.assertEqual(result.returncode, 2)  # Missing manifest is an input error.
        (self.root / "case-list.txt").write_text("ok\n")
        result = self.run_tool("--collect-only", "--manifest", self.root / "case-list.txt")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        out = self.root / "postprocess_summary"
        with (out / "bader_atoms.csv").open() as fh:
            atoms = list(csv.DictReader(fh))
        self.assertEqual(len(atoms), 2)
        self.assertAlmostEqual(float(atoms[0]["net_charge_e"]), 0.3)
        self.assertAlmostEqual(float(atoms[1]["net_charge_e"]), 0.5)
        with (out / "bader_elements.csv").open() as fh:
            elems = list(csv.DictReader(fh))
        self.assertEqual([v["element"] for v in elems], ["Na", "P"])

    def test_execute_isolated_and_failures_do_not_block_others(self):
        bins = self.root / "bin"
        bins.mkdir()
        chgsum = bins / "chgsum.pl"
        chgsum.write_text("#!/bin/sh\nprintf 'fake all electron\\n' > CHGCAR_sum\n")
        bader = bins / "bader"
        bader.write_text("#!/bin/sh\ncat > ACF.dat <<'EOF'\n" + ACF + "EOF\n")
        chgsum.chmod(0o755)
        bader.chmod(0o755)
        result = self.run_tool("--execute", "--chgsum-bin", chgsum,
                               "--bader-bin", bader)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("OK     ok:", result.stdout)
        self.assertTrue((self.good / "postprocess/bader/ACF.dat").exists())
        self.assertTrue((self.good / "postprocess/bader/CHGCAR").is_symlink())
        self.assertFalse((self.bad / "postprocess/bader").exists())
        self.assertEqual((self.good / "CHGCAR").read_text(), "fake density")
        with (self.root / "postprocess_summary/bader_cases.csv").open() as fh:
            cases = {v["case"]: v for v in csv.DictReader(fh)}
        self.assertEqual(cases["ok"]["status"], "OK")
        self.assertEqual(cases["missing"]["status"], "ERROR")

    def test_invalid_atom_count_rejected(self):
        (self.root / "case-list.txt").write_text("ok\n")
        (self.good / "ACF.dat").write_text(ACF.split("2 0.5")[0])
        result = self.run_tool("--collect-only", "--manifest", self.root / "case-list.txt")
        self.assertEqual(result.returncode, 1)
        self.assertIn("ACF.dat has 1 atoms", result.stdout)

    def test_manifest_escape_refused(self):
        (self.root / "case-list.txt").write_text("../\n")
        result = self.run_tool("--manifest", self.root / "case-list.txt")
        self.assertEqual(result.returncode, 2)
        self.assertIn("inside root", result.stderr)


if __name__ == "__main__":
    unittest.main()
