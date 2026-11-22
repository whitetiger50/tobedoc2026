"""Arithmetic and provenance fixtures only; these are not patient transcripts or ratings."""
from copy import deepcopy
import hashlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from schizophrenia_eval_v1 import aggregate, packets, validate


def fixture():
    text = 'ARITHMETIC FIXTURE ONLY. No actual patient or model output.'
    quote = [{'turn_id': 'T1', 'quote': text}]
    data = {'kind': 'arithmetic_fixture', 'evaluation_id': 'schizophrenia-eval-v1',
            'judge': {'identifier': 'NO_MODEL_ARITHMETIC_FIXTURE', 'rubric_sha256': hashlib.sha256(b'fixture').hexdigest()},
            'manifest': [], 'observations': []}
    for case, target, reps in [('positiveA', 2, 3), ('positiveB', 2, 1), ('absent', 0, 1)]:
        for condition in ['existing', 'module']:
            for rep in range(reps):
                ident = 'J' + f'{len(data["manifest"])+1:04d}'
                data['manifest'].append({'item_id': ident, 'case_id': case, 'condition': condition, 'repeat': rep,
                    'targets': {f: target for f in ['DER', 'INC', 'POV']},
                    'transcript': [{'turn_id': 'T1', 'speaker': 'patient', 'text': text}],
                    'fact_checks': [{'id': 'fact1', 'required': True, 'expected': 'Arithmetic fixture'}],
                    'interaction_checks': [{'id': 'role', 'required': True, 'rule': 'Arithmetic fixture'}]})
                # Existing succeeds only on one of two equally weighted positive cases.
                severity = target if condition == 'module' or case == 'positiveB' else 0
                data['observations'].append({'item_id': ident, 'generation_status': 'completed',
                    'observed': {f: {'severity': severity, 'reason': 'Arithmetic fixture, not an LLM judgment', 'evidence': quote}
                                 for f in ['DER', 'INC', 'POV']},
                    'facts': [{'id': 'fact1', 'status': 'correct', 'evidence': quote, 'reason': 'Fixture'}],
                    'interactions': [{'id': 'role', 'status': 'pass', 'evidence': quote, 'reason': 'Fixture'}]})
    return data


class EvaluationTests(unittest.TestCase):
    def test_fixture_cannot_masquerade_as_research(self):
        with self.assertRaisesRegex(ValueError, 'not research'):
            aggregate(fixture())

    def test_case_weights_not_generation_counts(self):
        result = aggregate(fixture(), True)
        self.assertEqual(result['conditions']['existing']['target_realization/macro']['lower'], .5)
        self.assertEqual(result['conditions']['module']['target_realization/macro']['lower'], 1)

    def test_unknown_keeps_possible_success_and_failure(self):
        data = fixture()
        for p, r in zip(data['manifest'], data['observations']):
            if p['case_id'] == 'positiveB' and p['condition'] == 'existing':
                for f in r['observed']:
                    r['observed'][f]['severity'] = None
        result = aggregate(data, True)['conditions']['existing']['target_realization/macro']
        self.assertEqual((result['lower'], result['upper']), (0, .5))

    def test_missing_outputs_cannot_disappear(self):
        data = fixture(); data['observations'].pop()
        with self.assertRaisesRegex(ValueError, 'Missing'):
            aggregate(data, True)

    def test_fabricated_quote_rejected(self):
        data = fixture(); data['observations'][0]['observed']['DER']['evidence'] = [{'turn_id': 'T1', 'quote': 'fabricated'}]
        with self.assertRaisesRegex(ValueError, 'exact quote'):
            aggregate(data, True)

    def test_posthoc_not_applicable_does_not_improve_score(self):
        data = fixture(); data['observations'][0]['facts'][0]['status'] = 'not_applicable'
        r = aggregate(data, True)['conditions']['existing']['fact_preservation']
        self.assertLess(r['lower'], 1)
        self.assertEqual(r['upper'], 1)

    def test_blind_packet_omits_targets_and_condition(self):
        stage1, stage2 = packets(fixture())
        self.assertEqual(set(stage1[0]), {'item_id', 'transcript'})
        self.assertNotIn('targets', stage2[0])

    def test_different_target_for_comparator_rejected(self):
        data = fixture(); data['manifest'][0]['targets']['DER'] = 3
        with self.assertRaisesRegex(ValueError, 'differ across'):
            aggregate(data, True)


if __name__ == '__main__':
    unittest.main()
