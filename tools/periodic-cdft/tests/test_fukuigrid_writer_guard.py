"""Read-only smoke checks for upstream FukuiGrid writer known zero-filter bug."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from check_fukuigrid_writer import check_source


class TestFukuiGridKnownBug(unittest.TestCase):
    def test_buggy_upstream_comprehension_blocked(self):
        source = '''
def write_fukui_file(FILE1, NATOMS, fukui, filename):
    for row in fukui:
        formatted_row = " ".join(f"{value: .11E}" for value in row if value != 0)
'''
        self.assertEqual(check_source(source),'BLOCKED_KNOWN_ZERO_FILTER')

    def test_zero_preserving_comprehension_not_blocked(self):
        source = '''
def write_fukui_file(FILE1, NATOMS, fukui, filename):
    for row in fukui:
        formatted_row = " ".join(f"{value: .11E}" for value in row)
'''
        self.assertEqual(check_source(source),
                         'NO_KNOWN_ZERO_FILTER_FOUND_STILL_NEEDS_NUMERIC_REGRESSION')

    def test_unknown_writer_not_certified(self):
        with self.assertRaisesRegex(ValueError,'UNKNOWN_VERSION'):
            check_source('def different_writer(): pass')


if __name__=='__main__':
    unittest.main()
