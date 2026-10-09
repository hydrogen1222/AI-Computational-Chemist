#!/usr/bin/env python3
"""Fukui Chinese comparison report must distinguish unrun and passing methods."""
from __future__ import annotations
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
SCRIPT=ROOT/"tools/periodic-cdft/scripts/report.py"

class FukuiReportTests(unittest.TestCase):
    def setUp(self):
        td=tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root=Path(td.name)
        self.pre=self.root/"preflight.json"
        self.pre.write_text(json.dumps({
            "status":"INPUT_GRID_PASS_SCF_MANUAL_CHECK",
            "reference":"N","n_atoms":3,"grid":[2,2,2],
            "states":[
                dict(label="N",delta_electrons=0,NELECT=6,integrated_electrons=6,SCF_EDIFF_marker=True),
                dict(label="p",delta_electrons=.1,NELECT=6.1,integrated_electrons=6.1,SCF_EDIFF_marker=True),
                dict(label="m",delta_electrons=-.1,NELECT=5.9,integrated_electrons=5.9,SCF_EDIFF_marker=False)],
            "warnings":["minus SCF needs verification"]}))
        self.out=self.root/"periodic_cdft_report.md"
    def command(self,*args):
        return subprocess.run([sys.executable,str(SCRIPT),
                               "--preflight",str(self.pre),"--out",str(self.out),*map(str,args)],
                              capture_output=True,text=True,check=False)
    def test_unrun_methods_not_claimed_as_finished(self):
        r=self.command()
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        content=self.out.read_text()
        self.assertIn("未提供已验收结果",content)
        self.assertIn("尚未取得完整",content)
        self.assertIn("minus SCF needs verification",content)
        self.assertNotIn("已经通过电子数归一化及所提供的跨程序空间算术检查",content)
    def test_refuses_invalid_qc(self):
        self.pre.write_text(self.pre.read_text().replace(
            "INPUT_GRID_PASS_SCF_MANUAL_CHECK","ERROR"))
        r=self.command()
        self.assertEqual(r.returncode,1)
        self.assertFalse(self.out.exists())
    def test_grid_audit_and_condensed_table(self):
        grid=self.root/"grid.json"
        grid.write_text(json.dumps({
            "status":"PASS_GRID_ARITHMETIC_ONLY_NOT_PBC_PHYSICS",
            "fields":{
                "critic2:fplus":{"integral":1,"min":-.1,"max":.9},
                "critic2:fminus":{"integral":1,"min":0,"max":.8},
                "multiwfn:fplus":{"integral":1.00001,"min":-.1,"max":.9},
                "multiwfn:fminus":{"integral":.99999,"min":0,"max":.8}
            },
            "engine_comparisons":[{
                "reference":"critic2","other":"multiwfn","field":"fplus",
                "rmse":.00001,"max_abs":.00003,"status":"PASS"}],
            "warnings":["Interpolation separate"]
        }))
        charges=self.root/"condensed_bader.csv"
        with charges.open("w",newline="") as fh:
            w=csv.DictWriter(fh,fieldnames=[
                "atom_index","element","f_plus","f_minus","f_zero","dual"])
            w.writeheader()
            w.writerows([dict(atom_index=1,element="S",f_plus=0,f_minus=0,f_zero=0,dual=0),
                         dict(atom_index=2,element="Li",f_plus=.5,f_minus=.5,f_zero=.5,dual=0),
                         dict(atom_index=3,element="Li",f_plus=.5,f_minus=.5,f_zero=.5,dual=0)])
        charges.with_suffix(".md").write_text("# Condensed QC\n\n**质量检查：** PASS\n")
        r=self.command("--grid-audit",grid,"--condensed",charges)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        content=self.out.read_text()
        for word in ("已通过网格检查","RMSE","multiwfn vs critic2",
                     "凝聚 Fukui 指数","condensed_bader.csv","+0.500000"):
            self.assertIn(word,content)
        self.assertEqual(self.command("--grid-audit",grid).returncode,1)
        self.assertIn("电子结构",content)
    def test_rejects_bad_grid_status(self):
        grid=self.root/"grid.json"
        grid.write_text('{"status":"FAIL"}')
        r=self.command("--grid-audit",grid)
        self.assertEqual(r.returncode,1)
        self.assertIn("not passed",r.stderr)

if __name__=="__main__":
    unittest.main()
