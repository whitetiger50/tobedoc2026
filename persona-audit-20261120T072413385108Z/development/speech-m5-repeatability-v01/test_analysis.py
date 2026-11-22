"""Deterministic fixtures for repeated-score and paired-error arithmetic."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('m5', Path(__file__).with_name('experiment.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class AnalysisTests(unittest.TestCase):
    def test_exact_pair_agreement(self):
        self.assertEqual(m.describe([4, 4, 3])['exact_pair_agreements'], 1)
        self.assertEqual(m.describe([4, 4, 4])['exact_pair_agreement'], 1)
        self.assertEqual(m.describe([1, 2, 4])['range'], 3)

    def test_invalid_scores(self):
        for values in ([1, 2], [True, 3, 4], [0, 2, 3]):
            with self.assertRaises(AssertionError): m.describe(values)

    def test_pair_directions_and_original_only_repeatability(self):
        items = []
        for c in ('A', 'B', 'C'):
            for v in ('v02', 'v04', 'error'):
                items.append({'item_id': c+'-'+v, 'case_id': c, 'condition': v,
                              'kind': 'synthetic_error_control' if v == 'error' else 'original',
                              'parent_item_id': c+'-v02'})
        values = {p: {i['item_id']: [4,4,4] for i in items} for p in m.PROVIDERS}
        values['codex']['A-v04'] = [3,4,4]
        values['claude']['A-error'] = [3,3,3]
        values['claude']['B-error'] = [4,4,4]
        values['claude']['C-error'] = [4,3,4]
        result = m.analyze_values(items, values)
        self.assertEqual(result['repeatability_originals_only']['claude']['pair_count'], 18)
        self.assertEqual(result['repeatability_originals_only']['claude']['all_three_equal_count'], 6)
        self.assertEqual(result['error_sensitivity']['claude']['lower_count'], 4)
        self.assertEqual(result['error_sensitivity']['claude']['tie_count'], 5)
        self.assertEqual(result['error_sensitivity']['claude']['pairs_with_strictly_lower_error_mean'], 2)
        self.assertAlmostEqual(result['v04_minus_v02'], -1/18)


if __name__ == '__main__': unittest.main()
