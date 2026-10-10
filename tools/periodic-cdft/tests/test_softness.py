"""Synthetic regression tests: never require VASP, external codes or proprietary inputs."""
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1] / "scripts"))
from softness import run


class TestSoftness(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.p = Path(self.t.name)
        (self.p / 'out').mkdir()
        self.pre = self.p / 'pre.json'
        self.pre.write_text(json.dumps({'status':'INPUT_GRID_PASS_SCF_MANUAL_CHECK','n_atoms':2}))
        self.energy = self.p / 'evidence.json'
        self.evidence = {
            'status':'VALIDATED_VERTICAL_IA','reviewed_by_researcher':True,
            'physical_model':'corrected_charged_supercell',
            'preflight_sha256':hashlib.sha256(self.pre.read_bytes()).hexdigest(),
            'source':'synthetic_test_only','reference':'documented common energy reference',
            'correction_record':'synthetic corrected test values',
            'charge_state_protocol':'corrected_integer_vertical_add_remove',
            'I_eV':7,'A_eV':3
        }
        self.energy.write_text(json.dumps(self.evidence))
        self.audit = self.p / 'audit.json'
        fields = {}
        for field, vals in [('fplus',[.4,.6]),('fminus',[.7,.3]),
                            ('fzero',[.55,.45]),('dual',[-.3,.3])]:
            path = self.p / (field+'.cube')
            # 2 x 1 x 1 grid, voxel 1 bohr^3; zero atoms, valid simple cube.
            path.write_text('first\nsecond\n    0 0.0 0.0 0.0\n'
                '    2 1.0 0.0 0.0\n    1 0.0 1.0 0.0\n'
                '    1 0.0 0.0 1.0\n'+' '.join(map(str,vals))+'\n')
            fields['critic2:'+field] = {'path':str(path),'integral':sum(vals)}
        self.audit.write_text(json.dumps({
            'status':'PASS_GRID_ARITHMETIC_ONLY_NOT_PBC_PHYSICS','fields':fields}))
        self.cond = self.p / 'condensed_h.csv'
        self.cond.write_text('atom_index,element,f_plus,f_minus,f_zero,dual\n'
            '1,S,0.4,0.7,0.55,-0.3\n2,Li,0.6,0.3,0.45,0.3\n')
        self.cond.with_suffix('.md').write_text('**质量检查：** PASS')

    def invoke(self):
        return run(self.energy,self.pre,self.audit,'critic2',[self.cond],self.p/'out')

    def test_valid_indices_and_conservation(self):
        result = self.invoke()
        self.assertEqual(result['electronegativity_eV'],5)
        self.assertEqual(result['hardness_eV'],4)
        self.assertEqual(result['hardness_half_gap_eV'],2)
        self.assertEqual(result['softness_inv_eV'],.25)
        self.assertIn('1.0000000000E-01',
                      (self.p/'out/critic2_s_fplus.cube').read_text())
        with (self.p/'out/softness_condensed_h.csv').open() as fh:
            rows = list(csv.DictReader(fh))
        self.assertAlmostEqual(float(rows[0]['s_minus_inv_eV']),.175)
        self.assertAlmostEqual(sum(float(x['s_plus_inv_eV']) for x in rows),.25)

    def test_response_and_half_gap_differ_by_two(self):
        result = self.invoke()
        self.assertAlmostEqual(result['hardness_eV'],2*result['hardness_half_gap_eV'])
        self.assertAlmostEqual(result['softness_inv_eV'],1/(result['I_eV']-result['A_eV']))
        # s is the response-consistent derivative of density w.r.t. mu;
        # don't silently use inverse of the half-gap hardness.
        self.assertNotAlmostEqual(result['softness_inv_eV'],1/result['hardness_half_gap_eV'])

    def test_no_scientific_review(self):
        self.evidence['reviewed_by_researcher'] = False
        self.energy.write_text(json.dumps(self.evidence))
        with self.assertRaisesRegex(ValueError,'not independently reviewed'):
            self.invoke()
        self.assertEqual(list((self.p/'out').iterdir()),[])

    def test_mismatched_preflight(self):
        self.evidence['preflight_sha256'] = 'bad'
        self.energy.write_text(json.dumps(self.evidence))
        with self.assertRaisesRegex(ValueError,'does not match'):
            self.invoke()

    def test_fractional_nelect_rejected(self):
        self.evidence['charge_state_protocol'] = 'N+0.1/N-0.1 raw TOTEN'
        self.energy.write_text(json.dumps(self.evidence))
        with self.assertRaisesRegex(ValueError,'integer vertical I/A'):
            self.invoke()

    def test_negative_hardness_rejected(self):
        self.evidence['A_eV'] = 8
        self.energy.write_text(json.dumps(self.evidence))
        with self.assertRaisesRegex(ValueError,'I>A'):
            self.invoke()

    def test_failed_grid_audit(self):
        audit = json.loads(self.audit.read_text()); audit['status'] = 'FAIL'
        self.audit.write_text(json.dumps(audit))
        with self.assertRaisesRegex(ValueError,'Fukui cube QC'):
            self.invoke()

    def test_failed_atomic_sum(self):
        self.cond.write_text('atom_index,element,f_plus,f_minus,f_zero,dual\n'
                             '1,S,0.4,0.7,0.55,-0.3\n2,Li,0.1,0.3,0.2,-0.2\n')
        with self.assertRaisesRegex(ValueError,'identities|sum'):
            self.invoke()

    def test_no_overwrite(self):
        self.invoke()
        with self.assertRaisesRegex(ValueError,'overwrite'):
            self.invoke()


class TestReportSoftness(unittest.TestCase):
    def test_optional_report_section_and_rejects_unreviewed(self):
        from report import summarize
        pre = {'status':'INPUT_GRID_PASS_SCF_MANUAL_CHECK','reference':'N',
               'n_atoms':2,'grid':[2,1,1],'states':[]}
        ordinary = summarize(pre,None,[])
        self.assertIn('NOT_VALIDATED_FOR_CHARGED_PBC',ordinary)
        self.assertNotIn('额外的已审查能量模型',ordinary)
        example = {'status':'ENERGY_MODEL_REVIEWED_NOT_PBC_CONVERGENCE_PROVEN_BY_SCRIPT',
                   'model':'corrected_charged_supercell','reference':'test only',
                   'source':'synthetic fixture', 'I_eV':7,'A_eV':3,
                   'electronegativity_eV':5,'hardness_eV':4,'hardness_half_gap_eV':2,'softness_inv_eV':0.25}
        expanded = summarize(pre,None,[],example)
        self.assertIn('额外的已审查能量模型',expanded)
        self.assertIn('eta_response=4 eV',expanded)
        self.assertIn('eta_half=2 eV',expanded)
        example['status']='NOT_VALIDATED_FOR_CHARGED_PBC'
        with self.assertRaisesRegex(ValueError,'provenance'):
            summarize(pre,None,[],example)


if __name__ == '__main__':
    unittest.main()
