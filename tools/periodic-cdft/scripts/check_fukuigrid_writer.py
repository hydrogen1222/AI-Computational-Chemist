#!/usr/bin/env python3
"""Read-only known-bug guard for an independently installed FukuiGrid source.

Static inspection guards a documented zero-filter writer regression.
It does NOT certify that any other FukuiGrid version is scientifically correct:
validate a generated field's exact grid count, zero positions and integral.
"""
from __future__ import annotations
import argparse
import ast
from pathlib import Path
import sys


def check_source(source: str):
    tree = ast.parse(source)
    fn = next((n for n in tree.body if isinstance(n, (ast.FunctionDef,ast.AsyncFunctionDef))
               and n.name=='write_fukui_file'),None)
    if fn is None:
        raise ValueError('missing write_fukui_file: UNKNOWN_VERSION (manual smoke test needed)')
    # In the current upstream writer: "for value in row if value != 0".
    # For a volumetric field, zero is a valid sample and must not be filtered.
    for node in ast.walk(fn):
        if isinstance(node,(ast.ListComp,ast.SetComp,ast.GeneratorExp)):
            for generator in node.generators:
                for cond in generator.ifs:
                    for part in ast.walk(cond):
                        if (isinstance(part,ast.Compare)
                                and any(isinstance(op,(ast.NotEq,ast.Eq)) for op in part.ops)
                                and any(isinstance(t,ast.Constant) and t.value==0
                                        for t in [part.left,*part.comparators])):
                            return 'BLOCKED_KNOWN_ZERO_FILTER'
    return 'NO_KNOWN_ZERO_FILTER_FOUND_STILL_NEEDS_NUMERIC_REGRESSION'


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True,help='Path to local FukuiGrid.py, read-only')
    args=p.parse_args(argv)
    try:
        status=check_source(args.source.read_text(encoding='utf-8'))
        print(status)
        return 1 if status.startswith('BLOCKED') else 0
    except (ValueError,OSError,SyntaxError) as exc:
        print(f'FUKUIGRID CHECK UNVERIFIED: {exc}',file=sys.stderr)
        return 2


if __name__=='__main__':
    sys.exit(main())
