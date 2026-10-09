#!/usr/bin/env python3
"""Periodic VASP Multiwfn workflow tests: no licensed POTCAR, no Multiwfn required."""
from __future__ import annotations
import csv
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
PREP=ROOT/"tools/multiwfn/scripts/prepare_periodic_chgcar.py"
COLLECT=ROOT/"tools/multiwfn/scripts/collect_periodic_charges.py"


def case_fixture(root: Path):
    d=root/"charge"
    d.mkdir()
    (d/"CHGCAR").write_text(
        "Li2S static\n1.0\n5 0 0\n0 5 0\n0 0 5\nS Li\n1 2\nDirect\n"
        "0 0 0\n0.25 0.25 0.25\n0.75 0.75 0.75\n\n2 2 2\n1 2 3 4 5 6 7 8\n")
    (d/"POTCAR").write_text(
        "TITEL = PAW_PBE S 01Jan2025\nPOMASS = 32.06; ZVAL = 6.000\n"
        "SHA256 = fake\nCOPYR = fake\n"
        "TITEL = PAW_PBE Li_sv 01Jan2025\n"
        "POMASS = 6.941; ZVAL = 3.000\n")
    (d/"OUTCAR").write_text("energy = -8\n NELECT = 12.000 total number of electrons\n")
    return d


def atom_log(symbols, values):
    return ("Method introduction\nFinal atomic charges:\n"+
            "".join(f"Atom {i}({sym}): {q:+.8f}\n" for i,(sym,q) in enumerate(zip(symbols,values),1))+
            "End of calculation\n")


class PeriodicCharges(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.case=case_fixture(self.root)
        self.species=["S","Li","Li"]
        self.work=self.case/"postprocess"/"multiwfn"

    def call(self,command,*options):
        return subprocess.run([sys.executable,str(command),str(self.root),*options],
                              text=True,capture_output=True,check=False)

    def manifest(self,txt="charge"):
        p=self.root/"cases.txt";p.write_text(txt+"\n");return p

    def add_logs(self):
        self.work.mkdir(parents=True,exist_ok=True)
        (self.work/"hirshfeld.log").write_text(atom_log(self.species,[0.08786,-0.04393,-0.04393]))
        (self.work/"hirshfeld_i.log").write_text(atom_log(self.species,[-1.8,0.9,0.9]))
        (self.work/"cm5.log").write_text(
            "CM5 analysis:\n"+
            "".join(f"Atom: {i}{symbol} CM5 charge: {q:+.8f} Hirshfeld charge: 0.0\n"
                    for i,(symbol,q) in enumerate(zip(self.species,[-.2472,.1236,.1236]),1)))

    def test_li_sv_valence_is_three_not_one(self):
        r=self.call(PREP)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertIn("Nval S 6 Li 3",r.stdout)
        self.assertIn("valence sum 12",r.stdout)
        self.assertIn("expected q 0.0",r.stdout)
        self.assertFalse(self.work.exists())

    def test_stage_exact_copy_except_title(self):
        old=(self.case/"CHGCAR").read_bytes()
        r=self.call(PREP,"--prepare")
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        data=(self.work/"CHGCAR_Nval").read_bytes()
        self.assertEqual(data.split(b"\n",1)[0],b"Nval S 6 Li 3")
        self.assertEqual(data.split(b"\n",1)[1],old.split(b"\n",1)[1])
        self.assertEqual((self.case/"CHGCAR").read_bytes(),old)
        self.assertEqual(self.call(PREP,"--prepare").returncode,1)

    def test_potcar_order_mismatch_is_rejected(self):
        pot=self.case/"POTCAR"
        pot.write_text(pot.read_text().replace("PAW_PBE S", "PAW_PBE P"))
        r=self.call(PREP)
        self.assertEqual(r.returncode,1)
        self.assertIn("species mismatch",r.stdout)

    def test_wrong_net_charge_rejected(self):
        r=self.call(PREP,"--net-charge","1")
        self.assertEqual(r.returncode,1)
        self.assertIn("charge from OUTCAR",r.stdout)

    def test_no_guess_when_potcar_missing(self):
        (self.case/"POTCAR").unlink()
        r=self.call(PREP)
        self.assertEqual(r.returncode,1)
        self.assertIn("POTCAR",r.stdout)

    def test_manifest_cannot_escape_root(self):
        r=self.call(PREP,"--manifest",str(self.manifest("../")))
        self.assertEqual(r.returncode,2)
        self.assertIn("outside",r.stderr)

    def test_collect_all_three_methods_and_chargemol_ddec6(self):
        self.add_logs()
        d=self.case/"postprocess"/"chargemol"
        d.mkdir(parents=True)
        (d/"DDEC6_even_tempered_net_atomic_charges.xyz").write_text(
            "3\nDDEC6\nS 0 0 0 -1.382809\nLi 1 1 1 0.691414\nLi 2 2 2 0.691395\n")
        r=self.call(COLLECT,"--net-charge","0")
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        output=self.root/"postprocess_summary"
        with (output/"multiwfn_atoms.csv").open() as f:
            rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),3)
        self.assertAlmostEqual(float(rows[0]["multiwfn_hirshfeld_e"]),.08786)
        self.assertAlmostEqual(float(rows[0]["multiwfn_cm5_e"]),-.2472)
        self.assertAlmostEqual(float(rows[0]["multiwfn_hirshfeld_i_e"]),-1.8)
        self.assertAlmostEqual(float(rows[0]["chargemol_ddec6_e"]),-1.382809)
        with (output/"multiwfn_qc.csv").open() as f:
            quality=list(csv.DictReader(f))
        self.assertEqual({row["status"] for row in quality},{"OK"})
        self.assertIn("Hirshfeld-I", (output/"multiwfn_charge_comparison.md").read_text())
        human = (output / "multiwfn_report_cn.md").read_text(encoding="utf-8")
        self.assertIn("可以放进 PPT", human)
        self.assertIn("逐方法质量状态", human)

    def test_bad_atom_order_rejected_no_surrogate(self):
        self.add_logs()
        file=self.work/"hirshfeld_i.log"
        file.write_text(file.read_text().replace("Atom 1(S)", "Atom 1(Li)"))
        r=self.call(COLLECT,"--net-charge","0")
        self.assertEqual(r.returncode,1)
        with (self.root/"postprocess_summary/multiwfn_atoms.csv").open() as f:
            rows=list(csv.DictReader(f))
        self.assertEqual(rows[0]["multiwfn_hirshfeld_i_e"],"")
        self.assertTrue(rows[0]["multiwfn_hirshfeld_e"])

    def test_missing_log_reported_not_mislabeled_as_ddec6(self):
        self.add_logs()
        (self.work/"hirshfeld_i.log").unlink()
        r=self.call(COLLECT,"--net-charge","0")
        self.assertEqual(r.returncode,1)
        self.assertIn("2/3 Multiwfn methods read",r.stdout)
        with (self.root/"postprocess_summary/multiwfn_qc.csv").open() as f:
            q=list(csv.DictReader(f))
        self.assertIn("ERROR",{row["status"] for row in q})

    def test_charge_conservation(self):
        self.add_logs()
        (self.work/"hirshfeld_i.log").write_text(
            atom_log(self.species,[-1.8,0.9,0.5]))
        r=self.call(COLLECT,"--net-charge","0")
        self.assertEqual(r.returncode,1)
        with (self.root/"postprocess_summary/multiwfn_qc.csv").open() as f:
            q=list(csv.DictReader(f))
        self.assertTrue(any("charge sum" in x["detail"] for x in q))

    def test_plot_exports_if_matplotlib_available(self):
        try:
            import matplotlib
        except ImportError:
            self.skipTest("matplotlib optional")
        self.add_logs()
        r=self.call(COLLECT,"--net-charge","0")
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        pic=self.root/"postprocess_summary"/"ppt_figures"
        self.assertTrue(list(pic.glob("*.svg")))
        self.assertTrue(list(pic.glob("*.png")))


if __name__=="__main__":
    unittest.main()
