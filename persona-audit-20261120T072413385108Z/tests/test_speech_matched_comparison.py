"""Paired arithmetic and missing-data boundaries; fixture scores are not research results."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('matched_experiment',ROOT/'development/speech-m3-v02-v03-compare-v01/experiment.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def fixture():
    packet={'cases':[]};key={};reviews={p:{'reviews':[]} for p in ['codex','claude']}
    # Blind order deliberately interleaves versions and cases.
    for blind,case,condition,scores in [('Z','case2','v03',(3,4)),('A','case1','v02',(2,3)),
                                       ('Q','case2','v02',(4,4)),('B','case1','v03',(4,3))]:
        packet['cases'].append({'blind_id':blind,'generated_dialogue':[{'turn_id':'P01','speaker':'patient','text':'FIXTURE ONLY'}]})
        key[blind]={'case_id':case,'condition':condition}
        for provider,score in zip(reviews,scores):
            reviews[provider]['reviews'].append({'blind_id':blind,'score':score,'reason':'arithmetic fixture',
                'evidence':[{'patient_turn_id':'P01','quote':'FIXTURE ONLY'}],'issues':[]})
    return reviews,packet,key


class MatchedComparisonTests(unittest.TestCase):
    def test_pairing_uses_private_mapping_and_equal_case_means(self):
        reviews,packet,key=fixture();result=module.aggregate(reviews,packet,key)
        self.assertEqual([r['delta_v03_minus_v02'] for r in result['cases']],[1,-.5])
        self.assertEqual(result['condition_means'],{'v02':3.25,'v03':3.5})
        self.assertEqual(result['delta_v03_minus_v02'],.25)
        self.assertEqual(result['judge_specific_means']['codex']['delta_v03_minus_v02'],.5)
        self.assertEqual(result['judge_specific_means']['claude']['delta_v03_minus_v02'],0)

    def test_single_reviewer_never_substitutes_for_pair(self):
        reviews,packet,key=fixture();reviews.pop('claude')
        with self.assertRaisesRegex(ValueError,'Both'):module.aggregate(reviews,packet,key)

    def test_missing_blind_mapping_never_disappears_from_mean(self):
        reviews,packet,key=fixture();key.pop('A')
        with self.assertRaisesRegex(ValueError,'incomplete'):module.aggregate(reviews,packet,key)

    def test_duplicate_condition_cannot_replace_other_version(self):
        reviews,packet,key=fixture();key['B']['condition']='v02'
        with self.assertRaisesRegex(ValueError,'Duplicate'):module.aggregate(reviews,packet,key)

    def test_case_without_both_conditions_cannot_be_aggregated(self):
        reviews,packet,key=fixture();key['B']['case_id']='case3'
        with self.assertRaisesRegex(ValueError,'both versions'):module.aggregate(reviews,packet,key)


if __name__=='__main__':unittest.main()
