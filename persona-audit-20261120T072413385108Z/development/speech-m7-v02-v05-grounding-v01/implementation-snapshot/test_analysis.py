import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('m7',Path(__file__).with_name('experiment.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class GroundingTests(unittest.TestCase):
    def test_fresh_generation_grouping_and_grounding_counts(self):
        items=[];reviews={p:{} for p in m.PROVIDERS}
        for c in ('A','B','C'):
            for v in ('v02','v05'):
                for rep in (1,2,3):
                    ident=f'{c}-{rep}-{v}'
                    items.append({'item_id':ident,'case_id':c,'condition':v,'replicate':rep,'generated_dialogue':[{'speaker':'patient','text':'FIXTURE ONLY'}]})
                    for p in m.PROVIDERS:
                        issue=(c=='B' and v=='v02' and p=='claude' and rep==2)
                        reviews[p][ident]={'score':3 if issue else 4,'grounding_review':{'status':'concern' if issue else 'no_issue_identified','findings':[{'kind':'scope_shift'}] if issue else []}}
        result=m.analyze(items,reviews)
        self.assertAlmostEqual(result['v05_minus_v02'],1/18)
        self.assertEqual(result['grounding_summary']['claude']['v02']['finding_count'],1)
        self.assertEqual(result['grounding_summary']['claude']['v05']['status_counts'],{'no_issue_identified':9})

    def test_unknown_fact_or_fabricated_quote_rejected(self):
        packet={'profiles':{'P':{'patient_setting':{'facts':[{'id':'living'}]}}},'cases':[{'blind_id':'H1','profile_ref':'P','generated_dialogue':[{'turn_id':'P01','speaker':'patient','text':'FIXTURE ONLY'}]}]}
        row={'blind_id':'H1','score':3,'reason':'fixture','evidence':[{'patient_turn_id':'P01','quote':'FIXTURE'}],'issues':[],
             'grounding_review':{'checked_turn_ids':['P01','P02','P03','P04'],'status':'concern','findings':[{'patient_turn_id':'P01','quote':'FIXTURE','kind':'scope_shift','fact_ids':['living'],'explanation':'fixture'}]}}
        m.validate_review({'reviews':[row]},packet)
        row['grounding_review']['findings'][0]['fact_ids']=['foreign_fact']
        with self.assertRaises(ValueError):m.validate_review({'reviews':[row]},packet)


if __name__=='__main__':unittest.main()
