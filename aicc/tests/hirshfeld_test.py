#!/usr/bin/env python3
"""Hirshfeld/CM5 extraction from an authentic-format Chargemol log excerpt."""
from __future__ import annotations
import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools/vasp/scripts/collect_hirshfeld.py"
LOG = """Chargemol version 3.5
Information for noniterative Hirshfeld method will be printed now.

Multipole analysis for each of the expansion sites.
XYZ coordinates, net charges, and multipoles are in atomic units.
center number, atomic number, x, y, z, net_charge, dipole_x, dipole_y, dipole_z, dipole_mag, Qxy
    1    11  0.000000  0.000000  0.000000   0.204737  0.000000 0.000000 0.000000 0.000000 0
    2    17  5.346879  5.346879  5.346879  -0.204737  0.000000 0.000000 0.000000 0.000000 0
Finished local_multipole_moment_analysis
Information for noniterative CM5 method will be printed now.
The computed CM5 net atomic charges are:
    0.420172    -0.420172
Hirshfeld and CM5 analysis finished, calculation of iterative AIM will proceed.
iter = 1
Net atomic charges for the current iteration:
    0.204737   -0.204737
iter = 2
Net atomic charges for the current iteration:
    0.556479   -0.556479
iter = 7
Net atomic charges for the current iteration:
    0.843200   -0.843200
"""


def make_run(root: Path, name: str="nacl"):
    p = root / name
    work = p / "postprocess" / "chargemol"
    work.mkdir(parents=True)
    (p / "CHGCAR").write_text(
        "NaCl\n1.0\n0 2.8 2.8\n2.8 0 2.8\n2.8 2.8 0\n"
        "Na Cl\n1 1\nDirect\n0 0 0\n0.5 0.5 0.5\n")
    (work / "VASP_DDEC_analysis.output").write_text(LOG)
    (work / "DDEC6_even_tempered_net_atomic_charges.xyz").write_text(
        "2\nunitcell\nNa 0 0 0 0.843200\nCl 2.8 2.8 2.8 -0.843200\n")
    return p


class HirshfeldExtractionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run = make_run(self.root)

    def cmd(self, *argv):
        return subprocess.run([sys.executable, str(SCRIPT), str(self.root),
                               *map(str, argv)], capture_output=True,
                              text=True, check=False)

    def test_preflight_only_is_read_only(self):
        result = self.cmd()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("READY", result.stdout)
        self.assertFalse((self.root / "postprocess_summary").exists())

    def test_extract_first_partition_not_final_ddec(self):
        result = self.cmd("--collect-only", "--net-charge", "0")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        out = self.root / "postprocess_summary"
        with (out / "hirshfeld_atoms.csv").open() as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(len(rows), 2)
        self.assertAlmostEqual(float(rows[0]["hirshfeld_net_charge_e"]), 0.204737)
        self.assertAlmostEqual(float(rows[0]["cm5_net_charge_e"]), 0.420172)
        self.assertAlmostEqual(float(rows[0]["ddec6_net_charge_e"]), 0.843200)
        self.assertAlmostEqual(float(rows[1]["hirshfeld_net_charge_e"]), -0.204737)
        self.assertIn("not Hirshfeld-I", (out / "hirshfeld_summary.md").read_text())
        human = (out / "hirshfeld_report_cn.md").read_text(encoding="utf-8")
        self.assertIn("可以放进 PPT", human)
        self.assertIn("普通 Hirshfeld", human)
        self.assertIn("不包含 Hirshfeld-I", human)

    def test_unrecognized_log_does_not_report_hirshfeld(self):
        p = self.run / "postprocess/chargemol/VASP_DDEC_analysis.output"
        p.write_text("Chargemol finished but no partition marker\n")
        r = self.cmd("--collect-only")
        self.assertEqual(r.returncode, 1)
        self.assertIn("noniterative Hirshfeld block absent", r.stdout)
        with (self.root / "postprocess_summary/hirshfeld_cases.csv").open() as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(rows[0]["status"], "ERROR")

    def test_bad_element_mapping_is_rejected(self):
        p = self.run / "postprocess/chargemol/VASP_DDEC_analysis.output"
        p.write_text(LOG.replace("    2    17  ", "    2    16  "))
        r = self.cmd("--collect-only")
        self.assertEqual(r.returncode, 1)
        self.assertIn("element mismatch", r.stdout)

    def test_optional_cm5_absent_still_yields_hirshfeld(self):
        p = self.run / "postprocess/chargemol/VASP_DDEC_analysis.output"
        p.write_text(LOG.replace("The computed CM5 net atomic charges are:\n    0.420172    -0.420172\n",""))
        r = self.cmd("--collect-only")
        self.assertEqual(r.returncode, 0, r.stdout+r.stderr)
        with (self.root / "postprocess_summary/hirshfeld_atoms.csv").open() as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(rows[0]["cm5_net_charge_e"], "")

    def test_charge_balance_fails_when_wrong_cell_charge_is_supplied(self):
        r = self.cmd("--collect-only", "--net-charge", "2")
        self.assertEqual(r.returncode, 1)
        self.assertIn("charge sum", r.stdout)

    def test_png_svg_if_matplotlib_available(self):
        try:
            import matplotlib  # noqa: F401
        except ImportError:
            self.skipTest("matplotlib optional")
        r = self.cmd("--collect-only", "--net-charge", "0")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        dest = self.root / "postprocess_summary/ppt_figures"
        self.assertTrue(list(dest.glob("*_charge_methods.svg")))
        self.assertTrue(list(dest.glob("*_charge_methods.png")))

    def test_case_isolation(self):
        second = make_run(self.root, "bad")
        (second / "postprocess/chargemol/VASP_DDEC_analysis.output").write_text("broken\n")
        r = self.cmd("--collect-only", "--net-charge", "0")
        self.assertEqual(r.returncode, 1)
        self.assertIn("OK nacl", r.stdout)
        self.assertIn("ERROR bad", r.stdout)
        with (self.root / "postprocess_summary/hirshfeld_elements.csv").open() as fh:
            els = list(csv.DictReader(fh))
        self.assertEqual({x["case"] for x in els}, {"nacl"})


if __name__ == "__main__":
    unittest.main()
