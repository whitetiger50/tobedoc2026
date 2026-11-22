"""Failure-sensitive checks for evidence validation and unknown-value bounds."""
import hashlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from analyze_poster_local_pilot import contrast_bounds, verify_annotation


class PilotAuditTests(unittest.TestCase):
    def test_unknowns_do_not_imply_no_effect(self):
        self.assertEqual(contrast_bounds({f'C{i}': 'uncertain' for i in range(1, 5)}), [-2, 2])

    def test_normal_instruction_change_is_subtracted(self):
        self.assertEqual(contrast_bounds({'C1': 'no', 'C2': 'no', 'C3': 'yes', 'C4': 'yes'}), [0, 0])

    def test_exact_ordered_adjacent_evidence_required(self):
        text = 'I wake at six. Then I eat toast. Finally I leave.'
        source = {'id': 'E001', 'text': text, 'sha256': hashlib.sha256(text.encode()).hexdigest()}
        row = {'id': 'E001', 'sha256': source['sha256'], 'A': 'direct', 'B': 'no', 'C': 'no',
            'before': 'I wake at six.', 'after': 'Then I eat toast.', 'reason': 'Temporal order.'}
        verify_annotation(row, source)
        bad = {**row, 'after': 'Finally I leave.'}
        with self.assertRaises(AssertionError):
            verify_annotation(bad, source)
        with self.assertRaises(AssertionError):
            verify_annotation({**row, 'sha256': 'wrong'}, source)


if __name__ == '__main__':
    unittest.main()
