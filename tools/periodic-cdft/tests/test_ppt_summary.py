"""Small synthetic tests for optional one-page Chinese cDFT reports."""
import csv
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from ppt_summary import evidence_summary

PRE = {
    "status":"INPUT_GRID_PASS_SCF_MANUAL_CHECK",
    "reference":"N","n_atoms":3,"grid":[2,2,2],
    "states":[
        {"label":"N","delta_electrons":0,"NELECT":12,
         "integrated_electrons":12,"SCF_EDIFF_marker":True},
        {"label":"p010","delta_electrons":0.1,"NELECT":12.1,
         "integrated_electrons":12.1,"SCF_EDIFF_marker":True},
        {"label":"m010","delta_electrons":-0.1,"NELECT":11.9,
         "integrated_electrons":11.9,"SCF_EDIFF_marker":True},
    ]
}


class TestPPTSummary(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p=Path(self.tmp.name)

    def make_table(self, method, splus, sminus):
        p=self.p/("condensed_"+method+".csv")
        vals=[("S",splus,sminus),("Li",(1-splus)/2,(1-sminus)/2),
              ("Li",(1-splus)/2,(1-sminus)/2)]
        with p.open("w",newline="") as fh:
            w=csv.writer(fh)
            w.writerow(("atom_index","element","f_plus","f_minus","f_zero","dual"))
            for i,(elem,plus,minus) in enumerate(vals,1):
                w.writerow((i,elem,plus,minus,(plus+minus)/2,plus-minus))
        p.with_suffix(".md").write_text("**质量检查：** PASS",encoding="utf-8")
        return p

    def passed_grid(self):
        fields={f"{engine}:{field}":{"integral":0 if field=="dual" else 1}
                for engine in ("multiwfn","critic2","fukuigrid-fd")
                for field in ("fplus","fminus","fzero","dual")}
        return {
            "status":"PASS_GRID_ARITHMETIC_ONLY_NOT_PBC_PHYSICS",
            "fields":fields,
            "engine_comparisons":[
                {"other":"fukuigrid-fd","reference":"critic2",
                 "field":"fplus","max_abs":1.6e-7,"rmse":1e-8,"status":"PASS"},
                {"other":"multiwfn","reference":"critic2",
                 "field":"fminus","max_abs":5e-8,"rmse":2e-9,"status":"PASS"}],
        }

    def test_three_engines_and_partition_dependence(self):
        paths=[self.make_table("chargemol_h",.36,.63),
               self.make_table("ddec6",.78,1),
               self.make_table("bader",.82,.90)]
        text=evidence_summary(PRE,self.passed_grid(),paths,"Li2S",
                              ["Bader equivalent Li atoms: WARN"])
        self.assertIn("Multiwfn",text.lower().replace("multiwfn","Multiwfn"))
        self.assertIn("fukuigrid-fd",text)
        self.assertIn("1.6e-07",text)
        self.assertIn("| Hirshfeld | S | +0.360 | +0.630",text)
        self.assertIn("| DDEC6 | S | +0.780 | +1.000",text)
        self.assertIn("| Bader | S | +0.820 | +0.900",text)
        self.assertIn("WARN",text)
        self.assertIn("尚未证明",text)
        self.assertLess(len(text.splitlines()),30)

    def test_missing_grid_does_not_claim_agreement(self):
        text=evidence_summary(PRE,None,[],"Li2S")
        self.assertIn("未提供四场均通过验收",text)
        self.assertNotIn("跨软件最大逐点差",text)

    def test_unapproved_atomic_table_rejected(self):
        p=self.make_table("bader",.8,.9)
        p.with_suffix(".md").write_text("**质量检查：** FAIL")
        with self.assertRaisesRegex(ValueError,"missing validated condensed report"):
            evidence_summary(PRE,self.passed_grid(),[p],"Li2S")

    def test_incomplete_grid_does_not_claim_full_coverage(self):
        g=self.passed_grid()
        del g["fields"]["fukuigrid-fd:dual"]
        text=evidence_summary(PRE,g,[],"Li2S")
        self.assertNotIn("已验收软件：multiwfn、critic2、fukuigrid-fd",text)


if __name__=="__main__":
    unittest.main()
