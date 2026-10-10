#!/usr/bin/env python3
"""Global indices and spatial/atomic local softness from externally VALIDATED I/A.

Does not infer I/A from periodic VASP TOTEN, band gap or fractional NELECT.
Requires same-case provenance, a researcher review and already-QC'd Fukui data.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

FIELDS = ('fplus', 'fminus', 'fzero', 'dual')
MODELS = ('corrected_charged_supercell', 'vacuum_aligned_slab', 'electrode_referenced_interface')


def validated_energy(evidence, preflight_bytes):
    if evidence.get('status') != 'VALIDATED_VERTICAL_IA' or evidence.get('reviewed_by_researcher') is not True:
        raise ValueError('I/A not independently reviewed: NOT_VALIDATED_FOR_CHARGED_PBC')
    if evidence.get('physical_model') not in MODELS:
        raise ValueError('missing defensible periodic energy model')
    if evidence.get('preflight_sha256') != hashlib.sha256(preflight_bytes).hexdigest():
        raise ValueError('I/A energy evidence does not match this exact VASP preflight')
    for key in ('source', 'reference', 'correction_record', 'charge_state_protocol'):
        if not isinstance(evidence.get(key), str) or not evidence[key].strip():
            raise ValueError(f'missing I/A provenance: {key}')
    if evidence['charge_state_protocol'] != 'corrected_integer_vertical_add_remove':
        raise ValueError('only corrected integer vertical I/A accepted; no raw fractional-NELECT TOTEN or band-gap proxy')
    try:
        i, a = float(evidence['I_eV']), float(evidence['A_eV'])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('I_eV/A_eV must be explicitly supplied') from exc
    if not (math.isfinite(i) and math.isfinite(a) and i > a):
        raise ValueError('I/A must be finite and I>A; otherwise hardness/softness invalid')
    eta = (i - a)/2
    return {'I_eV': i, 'A_eV': a, 'electronegativity_eV': (i+a)/2,
            'hardness_eV': eta, 'softness_inv_eV': 1/eta,
            'hardness_convention': '(I-A)/2', 'softness_convention': '1/eta',
            'model': evidence['physical_model'], 'reference': evidence['reference'],
            'source': evidence['source'], 'correction_record': evidence['correction_record'],
            'charge_state_protocol': evidence['charge_state_protocol'],
            'status': 'ENERGY_MODEL_REVIEWED_NOT_PBC_CONVERGENCE_PROVEN_BY_SCRIPT'}


def cube(path):
    lines = path.read_text(encoding='utf-8').splitlines(keepends=True)
    if len(lines) < 6:
        raise ValueError(f'cube header incomplete: {path}')
    header = lines[2].split()
    nat = int(header[0]); dims = []; axes = []
    if nat < 0:
        raise ValueError('orbital/multifield cube unsupported')
    for ln in lines[3:6]:
        p = ln.split(); n = int(p[0]); dims.append(n)
        axes.append([float(x) for x in p[1:4]])
    if any(n <= 0 for n in dims):
        raise ValueError('positive-count bohr cube required')
    stop = 6 + nat
    if len(lines) < stop:
        raise ValueError('cube missing atoms')
    data = [float(x.replace('D','E')) for ln in lines[stop:] for x in ln.split()]
    if len(data) != math.prod(dims) or not all(map(math.isfinite, data)):
        raise ValueError('invalid cube density samples')
    a, b, c = axes
    vol = abs(a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0]))
    if vol <= 0:
        raise ValueError('invalid cube voxel volume')
    return lines[:stop], data, vol


def checked_atoms(path, atom_count):
    if not path.with_suffix('.md').is_file() or '**质量检查：** PASS' not in path.with_suffix('.md').read_text(encoding='utf-8'):
        raise ValueError(f'condensed Fukui QC is not PASS: {path}')
    with path.open(encoding='utf-8-sig', newline='') as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) != atom_count:
        raise ValueError('condensed atom count does not match preflight')
    if not rows or not {'atom_index','element','f_plus','f_minus','f_zero','dual'}.issubset(rows[0]):
        raise ValueError('condensed columns missing')
    nums = {k: [] for k in ('f_plus','f_minus','f_zero','dual')}
    for j, row in enumerate(rows, 1):
        if int(row['atom_index']) != j or not row['element']:
            raise ValueError('invalid atom index/order')
        for key in nums:
            n = float(row[key])
            if not math.isfinite(n):
                raise ValueError('nonfinite condensed Fukui')
            nums[key].append(n)
        if (abs(nums['f_zero'][-1]-(nums['f_plus'][-1]+nums['f_minus'][-1])/2)>0.001
                or abs(nums['dual'][-1]-(nums['f_plus'][-1]-nums['f_minus'][-1]))>0.001):
            raise ValueError('invalid condensed identities')
    for key, vals in nums.items():
        expected = 0 if key=='dual' else 1
        if abs(math.fsum(vals)-expected)>0.05:
            raise ValueError(f'condensed {key} sum inconsistent')
    return rows


def run(evidence_path, preflight_path, audit_path, engine, condensed, output_dir):
    pb = preflight_path.read_bytes()
    pre = json.loads(pb)
    if pre.get('status')!='INPUT_GRID_PASS_SCF_MANUAL_CHECK':
        raise ValueError('VASP input grid preflight has not passed')
    global_indices = validated_energy(json.loads(evidence_path.read_text(encoding='utf-8')), pb)
    audit = json.loads(audit_path.read_text(encoding='utf-8'))
    if audit.get('status')!='PASS_GRID_ARITHMETIC_ONLY_NOT_PBC_PHYSICS':
        raise ValueError('Fukui cube QC not PASS')
    inputs = {}
    for field in FIELDS:
        key = f'{engine}:{field}'
        if key not in audit.get('fields',{}):
            raise ValueError(f'missing QC validated cube {key}')
        meta = audit['fields'][key]
        if abs(float(meta['integral']) - (0 if field=='dual' else 1)) > 0.05:
            raise ValueError('Fukui integral check failed')
        path = Path(meta['path'])
        if not path.is_absolute():
            path = audit_path.resolve().parent/path
        head, nums, voxel = cube(path)
        if abs(math.fsum(nums)*voxel-(0 if field=='dual' else 1)) > 0.05:
            raise ValueError(f'cube integrals changed since grid QC: {field}')
        inputs[field] = (path, head, nums)
    atom_tables = [(path, checked_atoms(path, pre['n_atoms'])) for path in condensed]
    if not output_dir.is_dir():
        raise ValueError('output-dir must already exist')
    planned = [output_dir/'global_indices.json']
    planned += [output_dir/f'{engine}_s_{f}.cube' for f in FIELDS]
    planned += [output_dir/f'softness_{p.stem}.csv' for p, _ in atom_tables]
    if len(planned)!=len(set(planned)) or any(p.exists() for p in planned):
        raise ValueError('refusing to overwrite or duplicate output files')
    s = global_indices['softness_inv_eV']
    global_indices['source_preflight_sha256'] = hashlib.sha256(pb).hexdigest()
    global_indices['source_fukui_audit'] = str(audit_path)
    global_indices['grid_engine'] = engine
    global_indices['note'] = 'Local softness is S*f, not an independent barrier; negative lobes retained.'
    for f in FIELDS:
        _, head, nums = inputs[f]
        # Annotate the changed unit rather than preserving misleading Fukui comments.
        head[0] = 'Local softness S*f, eV^-1 bohr^-3; signed field\n'
        head[1] = 'From independently reviewed I/A and QC-passed Fukui cube\n'
        with (output_dir/f'{engine}_s_{f}.cube').open('w',encoding='utf-8') as fh:
            fh.writelines(head)
            for j in range(0,len(nums),6):
                fh.write(' '.join(f'{v*s:.10E}' for v in nums[j:j+6])+'\n')
    for path, rows in atom_tables:
        with (output_dir/f'softness_{path.stem}.csv').open('w',encoding='utf-8',newline='') as fh:
            w = csv.writer(fh)
            w.writerow(['atom_index','element','s_plus_inv_eV','s_minus_inv_eV','s_zero_inv_eV','s_dual_inv_eV'])
            for row in rows:
                w.writerow([row['atom_index'],row['element'],
                            *(format(float(row[k])*s,'.12g') for k in ('f_plus','f_minus','f_zero','dual'))])
    (output_dir/'global_indices.json').write_text(json.dumps(global_indices,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return global_indices


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ('evidence','preflight','grid-audit','output-dir'):
        parser.add_argument('--'+arg,required=True,type=Path)
    parser.add_argument('--engine',default='critic2',choices=('critic2','multiwfn','fukuigrid-fd','fukuigrid-interp'))
    parser.add_argument('--condensed',action='append',default=[],type=Path)
    args=parser.parse_args(argv)
    try:
        result=run(args.evidence,args.preflight,args.grid_audit,args.engine,args.condensed,args.output_dir)
        print(f"VALIDATED-INPUT indices: chi={result['electronegativity_eV']:.6g} eV, eta={result['hardness_eV']:.6g} eV, S={result['softness_inv_eV']:.6g} eV^-1")
        return 0
    except (ValueError,OSError,TypeError,KeyError,OverflowError) as exc:
        print(f'PERIODIC SOFTNESS NOT AVAILABLE: {exc}',file=sys.stderr)
        return 1


if __name__=='__main__':
    sys.exit(main())
