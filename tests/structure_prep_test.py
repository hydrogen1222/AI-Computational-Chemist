#!/usr/bin/env python3
"""Structure-prep builders and the geometry audit on rock-salt NaCl.

Needs pymatgen (installed in CI); skipped where it is missing.
Run: python tests/structure_prep_test.py
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "tools/structure-prep/scripts"
HAVE_PMG = importlib.util.find_spec("pymatgen") is not None

NACL = """NaCl rock salt (conventional)
1.0
5.64 0 0
0 5.64 0
0 0 5.64
Na Cl
4 4
Direct
0.0 0.0 0.0
0.0 0.5 0.5
0.5 0.0 0.5
0.5 0.5 0.0
0.5 0.0 0.0
0.0 0.5 0.0
0.0 0.0 0.5
0.5 0.5 0.5
"""


def run(script, *args, cwd=None):
    return subprocess.run([sys.executable, str(S / script), *map(str, args)],
                          capture_output=True, text=True, cwd=cwd, check=False, timeout=300)


def poscar_counts(path):
    lines = Path(path).read_text().splitlines()
    # VASP5: line 6 = species, line 7 = counts
    return dict(zip(lines[5].split(), map(int, lines[6].split())))


@unittest.skipUnless(HAVE_PMG, "pymatgen not installed")
class StructurePrep(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        self.bulk = self.d / "POSCAR_bulk"
        self.bulk.write_text(NACL)

    def test_convert_to_primitive(self):
        out = self.d / "POSCAR_prim"
        r = run("convert_structure.py", self.bulk, out, "--primitive")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(poscar_counts(out), {"Na": 1, "Cl": 1})

    def test_vacancy_and_substitution(self):
        vac = self.d / "POSCAR_vac"
        r = run("dope_structure.py", self.bulk, "--vacancy", "1", "--out", vac)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(poscar_counts(vac), {"Na": 3, "Cl": 4})
        sub = self.d / "POSCAR_sub"
        r = run("dope_structure.py", self.bulk, "--substitute", "1:K", "--out", sub)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(sum(poscar_counts(sub).values()), 8)
        self.assertIn("K", poscar_counts(sub))

    def test_slab_has_vacuum_and_frozen_bottom(self):
        slab = self.d / "POSCAR_slab"
        r = run("make_slab.py", self.bulk, 1, 0, 0, "--min-slab", 8, "--min-vacuum", 12,
                "--out", slab)
        if r.returncode != 0 and "--termination" in (r.stdout + r.stderr):
            r = run("make_slab.py", self.bulk, 1, 0, 0, "--min-slab", 8, "--min-vacuum", 12,
                    "--termination", 0, "--out", slab)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        text = slab.read_text()
        self.assertIn("Selective", text)
        flags = [line.split()[-3:] for line in text.splitlines() if len(line.split()) >= 6]
        self.assertIn(["F", "F", "F"], flags)    # bottom layers frozen
        self.assertIn(["T", "T", "T"], flags)    # top layers free
        audit = self.d / "audit.json"
        r = run("audit_structure.py", slab, "--json", audit)
        self.assertIn(r.returncode, (0, 1), r.stdout + r.stderr)   # 2 = could not read
        self.assertIsInstance(json.loads(audit.read_text()), dict)

    def test_audit_fails_overlapping_atoms(self):
        bad = self.d / "POSCAR_bad"
        bad.write_text(NACL.replace("0.5 0.5 0.5\n", "0.02 0.0 0.0\n"))   # Cl almost on Na
        r = run("audit_structure.py", bad)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
