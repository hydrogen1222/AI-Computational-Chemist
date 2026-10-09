#!/usr/bin/env python3
"""Deterministic DDEC6 tests, no real VASP or licensed Chargemol needed."""
from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools/vasp/scripts/batch_ddec6.py"
PLOT = ROOT / "tools/vasp/scripts/plot_ddec6.py"


def bond_line(anchor_partner: int, element: str, bo: float, shift=(0, 0, 0)):
    tok = ["Bonded", "to", "the", "(", f"{shift[0]},", f"{shift[1]},", f"{shift[2]})",
           "and", "the", "atom", "number", "is", str(anchor_partner), "element",
           element, "x", "x", "x", "x", "bond_order", str(bo), "spin=0"]
    return " ".join(tok)


def fixtures(case: Path, element_mismatch=False, reverse_bo=0.3, write_density=True):
    case.mkdir(parents=True)
    (case / "CHGCAR").write_text("NaS test\n1\n6 0 0\n0 6 0\n0 0 6\nNa S\n1 1\nDirect\n0 0 0\n0.5 0.5 0.5\n")
    if write_density:
        for n in ("AECCAR0", "AECCAR2"):
            (case / n).write_text("fake numerical density\n")
    (case / "POTCAR").write_text("fake reference, do not redistribute\n")
    out = case / "postprocess" / "chargemol"
    out.mkdir(parents=True)
    charge = "2\nmock charge\nNa 0 0 0 0.7\n" + ("P" if element_mismatch else "S") + " 3 3 3 -0.7\n"
    pair = "2\nmock SBO\nNa 0 0 0 0.3\nS 3 3 3 0.3\n\n"
    pair += "Printing BOs for the atom 1 of Na\n" + bond_line(2,"S",0.3) + "\nThe sum of bond orders for this atom is 0.3\n"
    pair += "Printing BOs for the atom 2 of S\n" + bond_line(1,"Na",reverse_bo) + "\nThe sum of bond orders for this atom is 0.3\n"
    (out / "DDEC6_even_tempered_net_atomic_charges.xyz").write_text(charge)
    (out / "DDEC6_even_tempered_bond_orders.xyz").write_text(pair)
    return out


class DDEC6Tests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.root = Path(self.td.name)
        self.one = self.root / "a"
        fixtures(self.one)
        self.two = self.root / "bad"
        fixtures(self.two, element_mismatch=True)

    def run_batch(self, *argv):
        return subprocess.run([sys.executable, str(SCRIPT), str(self.root), *map(str, argv)],
                              text=True, capture_output=True, check=False)

    def test_default_dry_run_does_not_modify_data(self):
        old = (self.one / "CHGCAR").read_text()
        r = self.run_batch()
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertIn("READY", r.stdout)
        self.assertFalse((self.root / "postprocess_summary").exists())
        self.assertEqual((self.one / "CHGCAR").read_text(), old)

    def test_collect_charge_and_periodic_bonds(self):
        r = self.run_batch("--collect-only", "--net-charge", "0")
        self.assertEqual(r.returncode, 1, r.stderr + r.stdout)
        self.assertIn("element/order mismatch", r.stdout)
        out = self.root / "postprocess_summary"
        with (out / "ddec6_atoms.csv").open() as fh:
            atoms = list(csv.DictReader(fh))
        self.assertEqual(len(atoms), 2)
        self.assertEqual([float(a["ddec6_net_charge_e"]) for a in atoms], [0.7, -0.7])
        self.assertEqual([float(a["sum_bond_orders"]) for a in atoms], [0.3, 0.3])
        with (out / "ddec6_bonds.csv").open() as fh:
            bonds = list(csv.DictReader(fh))
        self.assertEqual(len(bonds), 1)  # reverse bonds de-duplicated
        self.assertEqual(bonds[0]["element_i"], "Na")
        self.assertEqual(bonds[0]["element_j"], "S")
        self.assertEqual(bonds[0]["translation_a"], "0")
        self.assertAlmostEqual(float(bonds[0]["ddec6_bond_order"]), 0.3)
        self.assertIn("Charge sum check: enabled", (out / "ddec6_summary.md").read_text())
        self.assertEqual((self.one / "CHGCAR").read_text().splitlines()[0], "NaS test")

    def test_no_fake_charge_balance_on_unspecified_q(self):
        self.two.joinpath("postprocess/chargemol/DDEC6_even_tempered_net_atomic_charges.xyz").write_text(
            "2\nmock\nNa 0 0 0 0.7\nS 3 3 3 -0.7\n")
        r = self.run_batch("--collect-only")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        with (self.root / "postprocess_summary/ddec6_cases.csv").open() as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual({x["charge_balance_error_e"] for x in rows}, {"NOT_CHECKED"})

    def test_nonreciprocal_pair_rejected(self):
        d = self.one / "postprocess/chargemol"
        b = d / "DDEC6_even_tempered_bond_orders.xyz"
        b.write_text(b.read_text().replace("bond_order 0.3 spin=0", "bond_order 0.31 spin=0", 1))
        r = self.run_batch("--collect-only", "--manifest", self.manifest("a"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("nonreciprocal BO", r.stdout)

    def manifest(self, content):
        p = self.root / "cases.txt"
        p.write_text(content + "\n")
        return p

    def test_chargemol_execute_requires_explicit_net_charge(self):
        r = self.run_batch("--execute")
        self.assertEqual(r.returncode, 2)
        self.assertIn("requires explicit --net-charge", r.stderr)

    def test_manifest_directory_escape_rejected(self):
        r = self.run_batch("--manifest", self.manifest("../"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("outside root", r.stderr)

    def test_missing_input_is_per_case_error(self):
        (self.two / "AECCAR2").unlink()
        r = self.run_batch()
        self.assertEqual(r.returncode, 1)
        self.assertIn("missing AECCAR2", r.stdout)
        self.assertIn("READY", r.stdout)

    def test_actual_launch_in_isolated_workdir_with_stub_executable(self):
        # Do not run/alter mock VASP densities or a real Chargemol binary.
        fresh = self.root / "new"
        fresh.mkdir()
        for f in ("CHGCAR", "AECCAR0", "AECCAR2", "POTCAR"):
            (fresh / f).write_text((self.one / f).read_text())
        density = self.root / "atomic_densities"
        density.mkdir()
        (density / "test_density").write_text("mock\n")
        binary = self.root / "chargemol_stub.sh"
        expected = self.one / "postprocess/chargemol"
        binary.write_text("#!/bin/sh\n"
                          "test -L CHGCAR && test -L POTCAR || exit 5\n"
                          "grep -q '<compute BOs>' job_control.txt || exit 6\n"
                          f"cp '{expected / 'DDEC6_even_tempered_net_atomic_charges.xyz'}' .\n"
                          f"cp '{expected / 'DDEC6_even_tempered_bond_orders.xyz'}' .\n")
        binary.chmod(0o755)
        r = self.run_batch("--execute", "--manifest", self.manifest("new"),
                           "--net-charge", "0", "--binary", binary, "--atomic-densities", density)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("OK", r.stdout)
        self.assertTrue((fresh / "postprocess/chargemol/CHGCAR").is_symlink())
        self.assertTrue((fresh / "postprocess/chargemol/job_control.txt").is_file())
        self.assertEqual((fresh / "CHGCAR").read_text(), (self.one / "CHGCAR").read_text())
        # Refuse to overwrite even if an output directory exists.
        r2 = self.run_batch("--execute", "--manifest", self.manifest("new"),
                            "--net-charge", "0", "--binary", binary, "--atomic-densities", density)
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
        self.assertIn("reused pre-existing outputs", r2.stdout)

    def test_upstream_chargemol_format_with_periodic_self_bonds(self):
        # Representative lines from pymatgen-core v2026.9.23's 2017 NaCl fixture.
        d = self.root / 'upstream_fixture'
        d.mkdir()
        (d / 'CHGCAR').write_text('NaCl\n1\n0 2.829447 2.829447\n2.829447 0 2.829447\n2.829447 2.829447 0\nNa Cl\n1 1\nDirect\n0 0 0\n0.5 0.5 0.5\n')
        out = d / 'postprocess/chargemol'
        out.mkdir(parents=True)
        (out / 'DDEC6_even_tempered_net_atomic_charges.xyz').write_text('2\ncell\nNa 0 0 0 0.843200\nCl 2.829447 2.829447 2.829447 -0.843200\n')
        head = '2\ncell\nNa 0 0 0 0.539920\nCl 2.829447 2.829447 2.829447 0.901058\n\n'
        def bond(shift, idx, elem, bo):
            return f'Bonded to the ( {shift}) translated image of atom number {idx} ( {elem} ) with bond order = {bo} The average spin polarization of this bonding = 0.0000\n'
        head += 'Printing BOs for ATOM # 1 ( Na ) in the reference unit cell.\n'
        head += bond('-1, 0, 0', 2, 'Cl', '0.0882')
        head += 'The sum of bond orders for this atom is SBO = 0.539920\n'
        head += 'Printing BOs for ATOM # 2 ( Cl ) in the reference unit cell.\n'
        head += bond('1, 0, 0', 1, 'Na', '0.0882')
        head += bond('0, 0, 1', 2, 'Cl', '0.0306')
        head += bond('0, 0, -1', 2, 'Cl', '0.0306')
        head += 'The sum of bond orders for this atom is SBO = 0.901058\n'
        (out / 'DDEC6_even_tempered_bond_orders.xyz').write_text(head)
        r = self.run_batch('--collect-only', '--net-charge', '0',
                           '--manifest', self.manifest('upstream_fixture'))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        with (self.root / 'postprocess_summary/ddec6_bonds.csv').open() as fh:
            bonds = list(csv.DictReader(fh))
        self.assertEqual(len(bonds), 2)  # Na-Cl and periodic Cl-Cl, no mirrored duplicates
        self.assertEqual({(b['element_i'], b['element_j']) for b in bonds},
                         {('Na', 'Cl'), ('Cl', 'Cl')})
        with (self.root / 'postprocess_summary/ddec6_atoms.csv').open() as fh:
            atoms = list(csv.DictReader(fh))
        self.assertAlmostEqual(float(atoms[0]['ddec6_net_charge_e']), 0.8432)
        self.assertAlmostEqual(float(atoms[1]['sum_bond_orders']), 0.901058)
    def test_slide_figures_if_matplotlib_available(self):
        try:
            import matplotlib  # noqa: F401
        except ImportError:
            self.skipTest("matplotlib optional, not installed")
        self.two.joinpath("postprocess/chargemol/DDEC6_even_tempered_net_atomic_charges.xyz").write_text(
            "2\nmock\nNa 0 0 0 0.7\nS 3 3 3 -0.7\n")
        r = self.run_batch("--collect-only", "--net-charge", "0")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        out = self.root / "postprocess_summary/ppt_figures"
        self.assertTrue((out / "a_charges.svg").is_file())
        self.assertTrue((out / "a_bond_orders.png").is_file())
        self.assertGreater((out / "a_charges.png").stat().st_size, 10000)


if __name__ == "__main__":
    unittest.main()
