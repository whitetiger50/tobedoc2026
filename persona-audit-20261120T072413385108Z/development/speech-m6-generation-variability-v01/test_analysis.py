import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('m6',Path(__file__).with_name('experiment.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class ArithmeticTests(unittest.TestCase):
    def test_three_generation_summary(self):
        r=m.description([3,4,4])
        self.assertAlmostEqual(r['mean'],11/3)
        self.assertEqual(r['range'],1)
        with self.assertRaises(ValueError):m.description([4,4])

    def test_grouping_and_equal_case_weight(self):
        items=[];reviews={p:{} for p in m.PROVIDERS}
        for case in ('A','B','C'):
            for v in ('v02','v04'):
                for rep in (1,2,3):
                    ident=f'{case}-{rep}-{v}'
                    items.append({'item_id':ident,'case_id':case,'condition':v,'replicate':rep,
                        'generated_dialogue':[{'speaker':'patient','text':'同じ'}]})
                    for p in m.PROVIDERS:
                        score=3 if (case=='B' and v=='v04' and p=='claude' and rep!=1) else 4
                        reviews[p][ident]={'score':score,'disclosure_flow':{'pattern':'limited','first_sensitive_turn':'P01'},'repetition_flow':{'pattern':'brief_reconfirmation'}}
        result=m.analyze(items,reviews)
        self.assertAlmostEqual(result['v04_minus_v02'],-1/9)
        self.assertEqual(result['cases'][0]['v02']['unique_exact_patient_sequences'],1)
        self.assertEqual(result['cases'][1]['v04']['combined_scores']['values'],[4,3.5,3.5])

    def test_flow_evidence_guard(self):
        packet={'cases':[{'blind_id':'G1','generated_dialogue':[{'turn_id':'P01','speaker':'patient','text':'집에서 빵 먹었어요.'}]}]}
        row={'blind_id':'G1','score':4,'reason':'fixture','evidence':[{'patient_turn_id':'P01','quote':'빵'}],
             'issues':[],'disclosure_flow':{'first_sensitive_turn':'none','pattern':'not_applicable','explanation':'fixture','evidence':[{'patient_turn_id':'P01','quote':'빵'}]},
             'repetition_flow':{'pattern':'brief_reconfirmation','explanation':'fixture','evidence':[{'patient_turn_id':'P01','quote':'빵'}]}}
        m.validate_review({'reviews':[row]},packet)
        row['repetition_flow']['evidence'][0]['quote']='not present'
        with self.assertRaises(ValueError):m.validate_review({'reviews':[row]},packet)


if __name__=='__main__':unittest.main()
