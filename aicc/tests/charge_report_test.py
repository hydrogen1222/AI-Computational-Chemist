#!/usr/bin/env python3
"""No-DFT scientific and human-readable regression tests for charge reports."""
from __future__ import annotations
import csv
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
REPORTER=ROOT/"tools/vasp/scripts/charge_report.py"


def write(folder,name,records):
    if not records:
        raise ValueError("test requires header-bearing records")
    with (folder/name).open("w",encoding="utf-8",newline="") as fh:
        w=csv.DictWriter(fh,fieldnames=list(records[0]))
        w.writeheader();w.writerows(records)


class ReadableCharges(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.output=self.root/"postprocess_summary"
        self.output.mkdir()

    def run_report(self,*args):
        return subprocess.run([sys.executable,str(REPORTER),str(self.output),*args],
                              capture_output=True,text=True,check=False)

    def add_bader(self):
        write(self.output,"bader_cases.csv",[
            dict(case="charge",status="OK",detail="collected",acf_path="/source/ACF.dat",
                 sum_bader_q_e="0",expected_net_charge_e="0",charge_balance_error_e="0"),
            dict(case="failed",status="ERROR",detail="missing ACF.dat",acf_path="",
                 sum_bader_q_e="",expected_net_charge_e="",charge_balance_error_e="NOT_CHECKED"),
        ])
        write(self.output,"bader_elements.csv",[
            dict(case="charge",element="Li",count=2,mean_q_e=".8",min_q_e=".75",max_q_e=".85",
                 spread_e=".10",acf_path="..."),
            dict(case="charge",element="S",count=1,mean_q_e="-1.6",min_q_e="-1.6",
                 max_q_e="-1.6",spread_e="0",acf_path="..."),
        ])
        write(self.output,"bader_atoms.csv",[
            dict(case="charge",atom_index=1,element="S",bader_electrons="7.6",zval=6,net_charge_e="-1.6"),
            dict(case="charge",atom_index=2,element="Li",bader_electrons="2.2",zval=3,net_charge_e=".8"),
            dict(case="charge",atom_index=3,element="Li",bader_electrons="2.2",zval=3,net_charge_e=".8"),
        ])

    def test_bader_chinese_report_and_no_failed_case_values(self):
        self.add_bader()
        result=self.run_report("--methods","bader")
        self.assertEqual(result.returncode,0,result.stderr+result.stdout)
        report=(self.output/"bader_summary.md").read_text()
        for needed in ("可以放进 PPT","Li 的平均净电荷为 +0.8000 e",
                       "S 的平均净电荷为 -1.6000 e","原子电荷","净电荷",
                       "晶胞电荷核对","缺少 ACF.dat"):
            if needed=="缺少 ACF.dat":
                self.assertIn("missing ACF.dat",report)
            else:
                self.assertIn(needed,report)
        self.assertIn("本例没有合格电荷",report)
        self.assertIn("AECCAR0+AECCAR2",report)
        self.assertNotIn("Hirshfeld-I 已收敛",report)

    def test_bader_missing_net_charge_is_not_falsely_verified(self):
        self.add_bader()
        p=self.output/"bader_cases.csv"
        s=p.read_text().replace("0,0,0","0,,NOT_CHECKED")
        p.write_text(s)
        r=self.run_report("--methods","bader")
        self.assertEqual(r.returncode,0,r.stderr)
        text=(self.output/"bader_summary.md").read_text()
        self.assertIn("未验证",text)
        self.assertIn("未检查",text)

    def test_ddec6_all_bond_types_and_bo_qc(self):
        write(self.output,"ddec6_cases.csv",[
            dict(case="test",status="OK",detail="collected",sum_ddec6_q_e="0",
                 charge_balance_error_e="NOT_CHECKED",bond_qc_status="METRIC_NOT_REPORTED",
                 contact_exchange_error_e="",chargemol_dir="/charges/postprocess/chargemol")])
        write(self.output,"ddec6_elements.csv",[
            dict(case="test",element="Li",n_atoms=2,mean_charge_e=".7",
                 min_charge_e=".69",max_charge_e=".71",mean_sbo=".75",min_sbo=".74",max_sbo=".76")])
        write(self.output,"ddec6_atoms.csv",[
            dict(case="test",atom_index_1based=1,element="Li",ddec6_net_charge_e=".7",
                 sum_bond_orders=".75",sbo_from_printed_pairs=".73",sbo_unprinted_remainder=".02")])
        write(self.output,"ddec6_bond_types.csv",[
            dict(case="test",element_pair="Li-S",n_periodic_bonds=8,mean_bond_order=".17",
                 min_bond_order=".15",max_bond_order=".19"),
            dict(case="test",element_pair="S-S",n_periodic_bonds=6,mean_bond_order=".05",
                 min_bond_order=".04",max_bond_order=".06"),
            dict(case="test",element_pair="Li-Li",n_periodic_bonds=6,mean_bond_order=".005",
                 min_bond_order=".004",max_bond_order=".006"),
        ])
        r=self.run_report("--methods","ddec6")
        self.assertEqual(r.returncode,0,r.stderr)
        text=(self.output/"ddec6_report_cn.md").read_text()
        for typ in ("Li-S","S-S","Li-Li"):self.assertIn(typ,text)
        self.assertIn("METRIC_NOT_REPORTED",text)
        self.assertIn("守恒未检查",text)
        self.assertIn("未打印残差",text)

    def test_chargemol_hirshfeld_reports_missing_cm5_without_guessing(self):
        write(self.output,"hirshfeld_cases.csv",[
            dict(case="run",status="OK",detail="read",
                 hirshfeld_charge_sum_e=0,cm5_charge_sum_e="",
                 expected_net_charge_e="NOT_CHECKED",source_log="/run/VASP_DDEC_analysis.output")])
        write(self.output,"hirshfeld_elements.csv",[
            dict(case="run",element="S",count=1,hirshfeld_mean_e=".087865",
                 hirshfeld_min_e=".087865",hirshfeld_max_e=".087865",
                 cm5_mean_e="",ddec6_mean_e="-1.382809")])
        write(self.output,"hirshfeld_atoms.csv",[
            dict(case="run",atom_index_1based=1,element="S",
                 hirshfeld_net_charge_e=".087865",cm5_net_charge_e="",ddec6_net_charge_e="-1.382809")])
        r=self.run_report("--methods","hirshfeld")
        self.assertEqual(r.returncode,0,r.stderr)
        text=(self.output/"hirshfeld_report_cn.md").read_text()
        self.assertIn("普通 Hirshfeld",text)
        self.assertIn("不包含 Hirshfeld-I",text)
        self.assertIn("—",text)
        self.assertIn("参考密度",text)

    def test_multiwfn_failed_hirshfeld_i_does_not_show_intermediate_number(self):
        write(self.output,"multiwfn_qc.csv",[
            dict(case="Li2S",method="hirshfeld",status="OK",detail="parsed",
                 charge_sum_e=0,expected_charge_e=0),
            dict(case="Li2S",method="cm5",status="OK",detail="parsed",
                 charge_sum_e=0,expected_charge_e=0),
            dict(case="Li2S",method="hirshfeld_i",status="ERROR",
                 detail="S-3.rad absent, not converged",charge_sum_e="",expected_charge_e=0),
        ])
        write(self.output,"multiwfn_elements.csv",[
            dict(case="Li2S",element="S",method="hirshfeld",n_atoms=1,
                 mean_q_e="-.285723",min_q_e="-.285723",max_q_e="-.285723"),
            dict(case="Li2S",element="S",method="cm5",n_atoms=1,
                 mean_q_e="-.623443",min_q_e="-.623443",max_q_e="-.623443"),
            dict(case="Li2S",element="S",method="hirshfeld_i",n_atoms=1,
                 mean_q_e="-2.080905",min_q_e="-2.080905",max_q_e="-2.080905"),
        ])
        write(self.output,"multiwfn_atoms.csv",[
            dict(case="Li2S",atom_1based=1,element="S",
                 multiwfn_hirshfeld_e="-.285723",multiwfn_cm5_e="-.623443",
                 multiwfn_hirshfeld_i_e="-2.080905",
                 chargemol_hirshfeld_e=".087865",chargemol_cm5_e="-.247186",
                 chargemol_ddec6_e="-1.382809"),
        ])
        r=self.run_report("--methods","multiwfn")
        self.assertEqual(r.returncode,0,r.stderr)
        text=(self.output/"multiwfn_report_cn.md").read_text()
        self.assertIn("S-3.rad",text)
        self.assertIn("不可引用",text)
        self.assertNotIn("-2.080905",text)
        self.assertIn("-0.2857",text)
        self.assertIn("+0.087865",text)
        self.assertIn("参考密度",text)

    def test_cli_skip_absent_and_fail_on_partial_inputs(self):
        r=self.run_report("--only-present")
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(list(self.output.glob("*.md")),[])
        (self.output/"bader_cases.csv").write_text("case,status\nx,OK\n")
        r=self.run_report("--only-present")
        self.assertEqual(r.returncode,1)
        self.assertIn("缺少 CSV",r.stderr)

    def test_reports_never_change_original_csv(self):
        self.add_bader()
        before={x.name:x.read_bytes() for x in self.output.glob("*.csv")}
        self.assertEqual(self.run_report("--methods","bader").returncode,0)
        after={x.name:x.read_bytes() for x in self.output.glob("*.csv")}
        self.assertEqual(before,after)


if __name__ == "__main__":
    unittest.main()
