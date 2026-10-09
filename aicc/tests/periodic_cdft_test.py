#!/usr/bin/env python3
"""Periodic Fukui: synthetic VASP-format, licensed-file-free tests."""
from __future__ import annotations
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"tools/periodic-cdft/scripts/preflight.py"
COND=ROOT/"tools/periodic-cdft/scripts/condensed.py"

def make_vasp(path,nelect,*,grid=(2,2,2),scale=1,shift=0,
              potcar="POTCAR mock",positions=("0 0 0","0.5 0.5 0.5","0.25 0.25 0.25")):
    path.mkdir()
    (path/"INCAR").write_text("ENCUT=520\nISMEAR=0\nSIGMA=0.05\nNSW=0\nISPIN=1\n")
    (path/"KPOINTS").write_text("Kpoints\n0\nGamma\n1 1 1\n0 0 0\n")
    (path/"POTCAR").write_text(potcar)
    density=nelect
    header=(f"Li2S mock\n{scale}\n5 0 0\n0 5 0\n0 0 5\n"
            "S Li\n1 2\nDirect\n"+ "\n".join(positions)+"\n\n"+
            " ".join(map(str,grid))+"\n")
    (path/"CHGCAR").write_text(header+" ".join(str(density) for _ in range(
        grid[0]*grid[1]*grid[2]))+"\n")
    (path/"OUTCAR").write_text(f" NELECT = {nelect:.9f} total number of electrons\n"
                                " aborting loop because EDIFF is reached\n")

def atomic_file(path,charges,method="bader",case="."):
    spec={
        "bader":("atom_index","net_charge_e"),
        "ddec6":("atom_index_1based","ddec6_net_charge_e"),
        "chargemol-h":("atom_index_1based","hirshfeld_net_charge_e"),
        "chargemol-cm5":("atom_index_1based","cm5_net_charge_e"),
        "multiwfn-h":("atom_1based","multiwfn_hirshfeld_e"),
        "multiwfn-cm5":("atom_1based","multiwfn_cm5_e"),
    }
    number,value=spec[method]
    with path.open("w",newline="") as fh:
        writer=csv.DictWriter(fh,fieldnames=["case",number,"element",value])
        writer.writeheader()
        for i,(element,q) in enumerate(zip(["S","Li","Li"],charges),1):
            writer.writerow(dict(case=case,**{number:i,"element":element,value:q}))

class PeriodicCDFTTests(unittest.TestCase):
    def setUp(self):
        td=tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root=Path(td.name)
        make_vasp(self.root/"N",6)
        make_vasp(self.root/"plus",6.1)
        make_vasp(self.root/"minus",5.9)
        self.manifest=self.root/"states.json"
        self.make_manifest()
        self.preflight=self.root/"preflight.json"
    def make_manifest(self):
        self.manifest.write_text(json.dumps({"states":[
            {"label":"N","directory":"N","delta_electrons":0},
            {"label":"p","directory":"plus","delta_electrons":.1},
            {"label":"m","directory":"minus","delta_electrons":-.1}]}))
    def call(self,tool,*args):
        return subprocess.run([sys.executable,str(tool),*map(str,args)],
                              text=True,capture_output=True,check=False)
    def pre(self,*args):
        return self.call(PRE,"--root",self.root,"--manifest",self.manifest,*args)
    def make_preflight(self):
        r=self.pre("--write",self.preflight)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        return json.loads(self.preflight.read_text())

    def test_preflight_read_only_and_normalization(self):
        r=self.pre()
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertFalse(self.preflight.exists())
        data=json.loads(r.stdout)
        self.assertEqual(data["n_atoms"],3)
        self.assertEqual(data["grid"],[2,2,2])
        self.assertEqual(data["plus_states"],1)
        self.assertEqual(data["minus_states"],1)
        self.assertEqual([round(x["integrated_electrons"],3) for x in data["states"]],[6,6.1,5.9])
    def test_density_integral_inconsistent_fail(self):
        p=self.root/"plus/CHGCAR"
        p.write_text(p.read_text().replace("6.1 6.1 6.1","6.0 6.0 6.0"))
        r=self.pre()
        self.assertEqual(r.returncode,1)
        self.assertIn("integrates",r.stderr)
    def test_changed_lattice_grid_atom_mapping_and_potcar_fail(self):
        for mutation in ("lattice","grid","sites","potcar"):
            with self.subTest(mutation=mutation):
                p=self.root/"plus"
                old={x:(p/x).read_text() for x in ("CHGCAR","POTCAR")}
                if mutation=="lattice":
                    (p/"CHGCAR").write_text(old["CHGCAR"].replace("5 0 0","5.01 0 0"))
                elif mutation=="grid":
                    (p/"CHGCAR").write_text(old["CHGCAR"].replace("2 2 2\n","1 2 4\n"))
                elif mutation=="sites":
                    (p/"CHGCAR").write_text(old["CHGCAR"].replace("0.25 0.25 0.25","0.26 0.25 0.25"))
                else:
                    (p/"POTCAR").write_text("DIFFERENT")
                r=self.pre()
                self.assertEqual(r.returncode,1,r.stdout+r.stderr)
                (p/"CHGCAR").write_text(old["CHGCAR"])
                (p/"POTCAR").write_text(old["POTCAR"])
    def test_wrong_delta_and_unilateral_fail(self):
        d=json.loads(self.manifest.read_text())
        d["states"][1]["delta_electrons"]=.2
        self.manifest.write_text(json.dumps(d))
        self.assertIn("claimed delta",self.pre().stderr)
        d["states"][1]["delta_electrons"]=.1
        d["states"].pop()
        self.manifest.write_text(json.dumps(d))
        self.assertIn("at least one state on each side",self.pre().stderr)
    def test_preflight_refuses_overwrite(self):
        self.make_preflight()
        self.assertEqual(self.pre("--write",self.preflight).returncode,1)

    def run_condensed(self,method="bader",plus=None,minus=None,delta=".1"):
        self.make_preflight()
        plus=plus or [-1.2,.55,.55]
        minus=minus or [-1.2,.65,.65]
        neutral=[-1.2,.6,.6]
        paths=[self.root/"q0.csv",self.root/"qp.csv",self.root/"qm.csv"]
        for path,charges in zip(paths,[neutral,plus,minus]):
            atomic_file(path,charges,method)
        args=["--method",method,"--preflight",str(self.preflight),
              "--neutral",str(paths[0]),"--plus",str(paths[1]),
              "--minus",str(paths[2]),"--delta-plus",delta,
              "--delta-minus",delta,"--output",str(self.root/"result.csv")]
        return self.call(COND,*args)
    def test_condensed_bader_complete_and_conserved(self):
        r=self.run_condensed()
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        text=(self.root/"result.md").read_text()
        self.assertIn("中文汇报",text)
        self.assertIn("Σf+",text)
        with (self.root/"result.csv").open() as file:atoms=list(csv.DictReader(file))
        self.assertEqual(len(atoms),3)
        self.assertAlmostEqual(float(atoms[1]["f_plus"]),.5)
        self.assertAlmostEqual(float(atoms[2]["f_minus"]),.5)
        self.assertAlmostEqual(sum(float(x["dual"]) for x in atoms),0)
    def test_condensed_ddec6(self):
        r=self.run_condensed(method="ddec6")
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
    def test_condensed_multiwfn_cm5(self):
        r=self.run_condensed(method="multiwfn-cm5")
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
    def test_condensed_rejects_nonconservation(self):
        r=self.run_condensed(plus=[-1.2,.6,.6])
        self.assertEqual(r.returncode,1)
        self.assertIn("sums failed",r.stderr)
        self.assertFalse((self.root/"result.csv").exists())
    def test_condensed_rejects_delta_mismatch(self):
        r=self.run_condensed(delta=".2")
        self.assertEqual(r.returncode,1)
        self.assertIn("delta absent",r.stderr)
    def test_condensed_rejects_wrong_atom(self):
        self.make_preflight()
        for s,qs in [("q0",[-1.2,.6,.6]),("qp",[-1.2,.55,.55]),("qm",[-1.2,.65,.65])]:
            atomic_file(self.root/(s+".csv"),qs)
        p=self.root/"qp.csv"
        p.write_text(p.read_text().replace("Li,0.55","P,0.55",1))
        r=self.call(COND,"--preflight",self.preflight,"--method","bader",
             "--neutral",self.root/"q0.csv","--plus",self.root/"qp.csv",
             "--minus",self.root/"qm.csv","--delta-plus",".1","--delta-minus",".1",
             "--output",self.root/"result.csv")
        self.assertEqual(r.returncode,1)
        self.assertIn("element/order mismatch",r.stderr)

if __name__=="__main__":
    unittest.main()
