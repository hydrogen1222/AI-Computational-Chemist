#!/usr/bin/env python3
"""Synthetic cube-grid integrity and cross-engine Fukui comparison tests."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/"tools/periodic-cdft/scripts/grid_audit.py"

def cube(path,values,origin="0 0 0",atoms="1 1.0 0 0 0"):
    # 2*1*1 bohr grid; volume per sample 0.5 bohr^3.
    head=("Cube first line\nCube second line\n1 "+origin+
          "\n2 0.5 0 0\n1 0 1 0\n1 0 0 1\n"+atoms+"\n")
    path.write_text(head+" ".join(str(x) for x in values)+"\n")

class GridQC(unittest.TestCase):
    def setUp(self):
        td=tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root=Path(td.name)
        self.data={
            "fplus":[1.,1.],"fminus":[0.,2.],
            "fzero":[.5,1.5],"dual":[1.,-1.]
        }
    def add(self,engine,field,values=None,origin="0 0 0"):
        path=self.root/f"{engine}_{field}.cube"
        cube(path,self.data[field] if values is None else values,origin)
        return f"{engine}:{field}:{path}"
    def run_audit(self,selections):
        args=[sys.executable,str(AUDIT),"--out",str(self.root/"check.json")]
        for selection in selections:args.extend(["--cube",selection])
        return subprocess.run(args,capture_output=True,text=True,check=False)
    def basic(self,engines=("critic2","multiwfn")):
        return [self.add(e,f) for e in engines for f in self.data]
    def test_complete_same_grid_passes(self):
        sels=self.basic()
        r=self.run_audit(sels)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        j=json.loads((self.root/"check.json").read_text())
        self.assertEqual(j["status"],"PASS_GRID_ARITHMETIC_ONLY_NOT_PBC_PHYSICS")
        self.assertEqual(len(j["engine_comparisons"]),2)
        self.assertAlmostEqual(j["fields"]["critic2:dual"]["integral"],0)
        self.assertIn("中文", (self.root/"check.md").read_text())
    def test_fukuigrid_interpolation_different_does_not_flag_a_code_bug(self):
        sels=self.basic(("critic2",))
        sels.extend([self.add("fukuigrid-interp","fplus",[.8,1.2]),
                     self.add("fukuigrid-interp","fminus",[.4,1.6])])
        r=self.run_audit(sels)
        self.assertEqual(r.returncode,0,r.stderr)
        j=json.loads((self.root/"check.json").read_text())
        self.assertTrue(any("different electron-number" in x for x in j["warnings"]))
    def test_same_fd_engines_disagree_fails(self):
        sels=self.basic(("critic2",))
        sels.extend([self.add("fukuigrid-fd","fplus",[.5,1.5]),
                     self.add("fukuigrid-fd","fminus",[0,2])])
        r=self.run_audit(sels)
        self.assertEqual(r.returncode,1)
        self.assertIn("max diff",r.stderr)
        self.assertFalse((self.root/"check.json").exists())
    def test_missing_grid_point_zeros_not_discarded(self):
        sels=self.basic(("critic2",))
        # Omitting actual zero destroys grid validity; reject.
        bad=self.root/"critic2_fminus.cube"
        bad.write_text(bad.read_text().replace("0.0 2.0","2.0"))
        r=self.run_audit(sels)
        self.assertEqual(r.returncode,1)
        self.assertIn("cube missing data",r.stderr)
    def test_wrong_fzero_identity_rejected(self):
        sels=self.basic(("critic2",))
        bad=self.root/"critic2_fzero.cube"
        bad.write_text(bad.read_text().replace("0.5 1.5","0.7 1.3"))
        r=self.run_audit(sels)
        self.assertEqual(r.returncode,1)
        self.assertIn("identity inconsistent",r.stderr)
    def test_wrong_grid_origin_rejected(self):
        sels=self.basic(("critic2",))
        bad=self.root/"critic2_fminus.cube"
        bad.write_text(bad.read_text().replace("1 0 0 0\n2","1 0.1 0 0\n2"))
        r=self.run_audit(sels)
        self.assertEqual(r.returncode,1)
        self.assertIn("cube origins",r.stderr)
    def test_wrong_normalization_rejected(self):
        sels=[self.add("critic2","fplus",[.5,.5]),
              self.add("critic2","fminus")]
        r=self.run_audit(sels)
        self.assertEqual(r.returncode,1)
        self.assertIn("integral",r.stderr)
    def test_no_clipping_negative_lobes(self):
        sels=self.basic(("critic2",))
        r=self.run_audit(sels)
        self.assertEqual(r.returncode,0,r.stderr)
        j=json.loads((self.root/"check.json").read_text())
        self.assertAlmostEqual(j["fields"]["critic2:dual"]["negative_integral"],-.5)
        self.assertAlmostEqual(j["fields"]["critic2:dual"]["positive_integral"],.5)

if __name__=="__main__":
    unittest.main()
