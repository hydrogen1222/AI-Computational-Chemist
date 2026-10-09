#!/usr/bin/env python3
"""Zero-network filesystem discovery tests (fake binaries, no VASP/Chargemol)."""
from __future__ import annotations

import csv
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
LOCATOR = ROOT / "tools/vasp/scripts/software_locator.py"
DDEC = ROOT / "tools/vasp/scripts/batch_ddec6.py"
PLOT = ROOT / "tools/vasp/scripts/plot_ddec6.py"


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.apps = self.root / "apps"
        self.apps.mkdir()
        self.env = os.environ.copy()
        self.env.update({"AICC_SOFTWARE_ROOTS": str(self.apps)})
        for var in ("AICC_CHARGEMOL_BIN", "CHARGEMOL_BIN", "CHARGEMOL_EXE",
                    "AICC_BADER_BIN", "BADER_BIN", "AICC_CHGSUM_BIN",
                    "CHGSUM_BIN", "DDEC6_ATOMIC_DENSITIES_DIR",
                    "AICC_CHARGEMOL_DENSITIES"):
            self.env.pop(var, None)

    def call_locator(self, tool: str, *argv):
        return subprocess.run([sys.executable, str(LOCATOR), tool, *argv],
                              env=self.env, capture_output=True, text=True)

    def test_find_chargemol_without_paths(self):
        install = self.apps / "chargemol_09_26_2017"
        binary = install / "Chargemol_09_26_2017_linux_serial"
        install.mkdir()
        binary.write_text("#!/bin/sh\nexit 0\n")
        binary.chmod(0o755)
        lib = install / "atomic_densities"
        lib.mkdir()
        (lib / "c2_011_011_011_500_100.txt").write_text("mock")
        r = self.call_locator("chargemol")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(str(binary), r.stdout)
        self.assertIn(str(lib), r.stdout)

    def test_misconfigured_environment_not_silently_overridden(self):
        folder = self.apps / "bader"
        folder.write_text("#!/bin/sh\nexit 0\n")
        folder.chmod(0o755)
        self.env["AICC_BADER_BIN"] = str(self.root / "missing")
        r = self.call_locator("bader")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("specified but not found", r.stderr)

    def test_ambiguity_detected(self):
        for sub in ("releaseA", "releaseB"):
            dest = self.apps / sub
            dest.mkdir()
            exe = dest / "Chargemol_09_26_2017_linux_serial"
            exe.write_text("#!/bin/sh\nexit 0\n")
            exe.chmod(0o755)
        r = self.call_locator("chargemol")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("multiple chargemol executables", r.stderr)

    def test_missing_reference_densities_does_not_pass(self):
        dest = self.apps / "chargemol"
        dest.write_text("#!/bin/sh\nexit 0\n")
        dest.chmod(0o755)
        (self.apps / "atomic_densities").mkdir()
        (self.apps / "atomic_densities" / "NOT_A_DENSITY").write_text("fake")
        r = self.call_locator("chargemol")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("c2_*.txt", r.stderr)

    def test_bader_and_chgsum_discovered_independently(self):
        d = self.apps / "bin"
        d.mkdir()
        for name in ("bader", "chgsum.pl"):
            p = d / name
            p.write_text("#!/bin/sh\nexit 0\n")
            p.chmod(0o755)
            r = self.call_locator("bader" if name=="bader" else "chgsum")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn(str(p), r.stdout)

    def test_plot_paginates_all_bond_classes_without_top_n_filter(self):
        try:
            import matplotlib  # noqa: F401
        except ImportError:
            self.skipTest("matplotlib is optional")
        out = self.root / "postprocess_summary"
        out.mkdir()
        with (out / "ddec6_elements.csv").open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=["case", "element", "n_atoms",
                "mean_charge_e", "min_charge_e", "max_charge_e", "mean_sbo",
                "min_sbo", "max_sbo"])
            writer.writeheader()
            writer.writerow({"case":"demo", "element":"Na", "n_atoms":"2",
                "mean_charge_e":"0.6", "min_charge_e":"0.3", "max_charge_e":"0.9",
                "mean_sbo":"0.1", "min_sbo":"0.08", "max_sbo":"0.12"})
        all_types = ["Na-S", "Na-P", "F-S", "P-S", "Cl-S", "Na-F"]
        with (out / "ddec6_bond_types.csv").open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=["case", "element_pair",
                "n_periodic_bonds", "mean_bond_order", "min_bond_order",
                "max_bond_order"])
            writer.writeheader()
            for i, typ in enumerate(all_types):
                writer.writerow({"case":"demo", "element_pair":typ, "n_periodic_bonds":i+1,
                    "mean_bond_order":0.1+i/10, "min_bond_order":0.05+i/10,
                    "max_bond_order":0.15+i/10})
        r = subprocess.run([sys.executable,str(PLOT),str(out),
                           "--items-per-figure","2"],
                           capture_output=True,text=True,check=False)
        self.assertEqual(r.returncode, 0, r.stderr+r.stdout)
        dest = out/"ppt_figures"
        for stem in ("demo_charges", "demo_bond_orders",
                     "demo_bond_orders_part02", "demo_bond_orders_part03"):
            self.assertTrue((dest/(stem+".png")).is_file(),stem)
            self.assertTrue((dest/(stem+".svg")).is_file(),stem)
        self.assertEqual(len(list(dest.glob("demo_bond_orders*.png"))),3)
        # Editable text labels for ALL bond classes, including the last class.
        labels = "\n".join(f.read_text() for f in dest.glob("demo_bond_orders*.svg"))
        for typ in all_types:
            self.assertIn(typ, labels)


if __name__ == "__main__":
    unittest.main()
