"""Regression tests for the default, concise Chinese periodic cDFT report."""
import csv
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from report import summarize, summarize_readable, main

PRE={
    "status":"INPUT_GRID_PASS_SCF_MANUAL_CHECK",
    "reference":"N", "n_atoms":3, "grid":[2,2,2],
    "states":[
        {"label":"N","delta_electrons":0,"NELECT":12,
         "integrated_electrons":12,"SCF_EDIFF_marker":True},
        {"label":"p010","delta_electrons":0.1,"NELECT":12.1,
         "integrated_electrons":12.1,"SCF_EDIFF_marker":True},
        {"label":"m010","delta_electrons":-0.1,"NELECT":11.9,
         "integrated_electrons":11.9,"SCF_EDIFF_marker":True},
    ],
}


class TestReadableReport(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p=Path(self.tmp.name)

    def make_table(self, method, splus, sminus):
        p=self.p/("condensed_"+method+".csv")
        values=[("S",splus,sminus),("Li",(1-splus)/2,(1-sminus)/2),
                ("Li",(1-splus)/2,(1-sminus)/2)]
        with p.open("w",encoding="utf-8",newline="") as fh:
            w=csv.writer(fh)
            w.writerow(("atom_index","element","f_plus","f_minus","f_zero","dual"))
            for i,(elem,fp,fm) in enumerate(values,1):
                w.writerow((i,elem,fp,fm,(fp+fm)/2,fp-fm))
        p.with_suffix(".md").write_text("**质量检查：** PASS",encoding="utf-8")
        return p

    def passed_grid(self):
        fields={f"{e}:{k}":{"integral":0 if k=="dual" else 1}
                for e in ("multiwfn","critic2","fukuigrid-fd")
                for k in ("fplus","fminus","fzero","dual")}
        return {
            "status":"PASS_GRID_ARITHMETIC_ONLY_NOT_PBC_PHYSICS",
            "fields":fields,
            "engine_comparisons":[
                {"other":"fukuigrid-fd","reference":"critic2",
                 "field":"fplus","max_abs":1.6e-7,"rmse":1e-8,"status":"PASS"},
                {"other":"multiwfn","reference":"critic2",
                 "field":"fminus","max_abs":5e-8,"rmse":2e-9,"status":"PASS"}],
        }

    def test_default_text_contains_results_not_logs(self):
        paths=[self.make_table("chargemol_h",.36,.63),
               self.make_table("ddec6",.78,1.0),
               self.make_table("bader",.82,.90)]
        short=summarize_readable(PRE,self.passed_grid(),paths,"Li₂S",
                                 ["Bader 两个等价 Li 位点不一致"])
        self.assertIn("# Li₂S｜周期性概念 DFT 结果",short)
        self.assertIn("Multiwfn、Critic2、FukuiGrid",short)
        self.assertIn("1.6e-07",short)
        self.assertIn("| Hirshfeld (Chargemol) | S | +0.360 | +0.630",short)
        self.assertIn("| DDEC6 | S | +0.780 | +1.000",short)
        self.assertIn("| Bader | S | +0.820 | +0.900",short)
        self.assertIn("Bader 两个等价 Li",short)
        self.assertIn("双描述符",short)
        self.assertNotIn("SCF 终止标志",short)
        self.assertNotIn("## 同一种有限差分近似下的软件对照",short)
        self.assertLess(len(short.splitlines()),40)
        detailed=summarize(PRE,self.passed_grid(),paths)
        self.assertIn("## 同一种有限差分近似下的软件对照",detailed)

    def test_grid_missing_never_claims_three_engine_agreement(self):
        text=summarize_readable(PRE,None,[],"Li₂S")
        self.assertIn("尚未获得完整的已验收网格",text)
        self.assertNotIn("软件一致性：已验收",text)

    def test_missing_derived_field_not_claimed(self):
        grid=self.passed_grid()
        del grid["fields"]["fukuigrid-fd:dual"]
        short=summarize_readable(PRE,grid,[],"Li₂S")
        self.assertNotIn("Multiwfn、Critic2、FukuiGrid",short)
        self.assertIn("Multiwfn、Critic2",short)

    def test_bad_atomic_qc_rejected(self):
        file=self.make_table("bader",.8,.9)
        file.with_suffix(".md").write_text("**质量检查：** FAIL",encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"missing validated condensed report"):
            summarize_readable(PRE,self.passed_grid(),[file],"Li₂S")

    def test_cli_defaults_to_readable_and_is_not_overwritten(self):
        import json
        pre=self.p/"preflight.json"
        grid=self.p/"grid.json"
        pre.write_text(json.dumps(PRE),encoding="utf-8")
        grid.write_text(json.dumps(self.passed_grid()),encoding="utf-8")
        out=self.p/"periodic_cdft_report.md"
        opts=["--preflight",str(pre),"--grid-audit",str(grid),
              "--system","Li₂S","--out",str(out)]
        self.assertEqual(main(opts),0)
        self.assertIn("## 主要结果",out.read_text(encoding="utf-8"))
        self.assertNotIn("## 同一种有限差分近似下的软件对照",out.read_text(encoding="utf-8"))
        self.assertEqual(main(opts),1)
        detailed=self.p/"detail.md"
        opts[-1]=str(detailed)
        self.assertEqual(main(opts+["--detailed"]),0)
        self.assertIn("## 同一种有限差分近似下的软件对照",
                      detailed.read_text(encoding="utf-8"))


if __name__=="__main__":
    unittest.main()
