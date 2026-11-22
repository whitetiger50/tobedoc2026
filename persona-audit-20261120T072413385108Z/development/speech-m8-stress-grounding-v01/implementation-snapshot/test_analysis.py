import importlib.util
import json
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('m8',Path(__file__).with_name('experiment.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class StressTests(unittest.TestCase):
    def test_probe_groups_have_three_challenges_and_known_recovery(self):
        probes=m.read(Path(__file__).with_name('probes.json'))['cases']
        parent=m.read(m.PARENT/'plan.json')
        for c in parent['cases']:
            p=probes[c['case_id']]
            self.assertEqual([r['type'] for r in p],['time','person','cause','recovery'])
            known={f['id'] for f in c['input']['patient']['facts'] if f['patient_knows']}
            self.assertTrue(all(set(r['required_fact_ids']).issubset(known) for r in p))

    def test_limits_not_counted_as_evasion_and_recovery_separate(self):
        items=[];reviews={p:{} for p in m.PROVIDERS}
        for c in ('A','B','C'):
            for v in ('v02','v05'):
                for rep in (1,2,3):
                    ident=f'{c}-{rep}-{v}'
                    items.append({'item_id':ident,'case_id':c,'condition':v,'replicate':rep,'generated_dialogue':[{'speaker':'patient','text':'FIXTURE ONLY'}]})
                    for p in m.PROVIDERS:
                        labels={f'P{n:02d}':'appropriate_limit_or_correction' if n in (5,6,7) else 'substantive_answer' for n in range(1,9)}
                        if c=='A' and v=='v05' and rep==1 and p=='claude':labels['P08']='unnecessary_evasion'
                        reviews[p][ident]={'score':4,'grounding_review':{'status':'no_issue_identified','findings':[]},'avoidance_review':{'turn_labels':labels}}
        r=m.analyze(items,reviews)
        self.assertEqual(r['patient_turns'],144)
        self.assertEqual(r['avoidance_summary']['codex']['v02']['dialogues_with_unnecessary_evasion'],0)
        self.assertEqual(r['avoidance_summary']['claude']['v05']['recovery_P08_label_counts']['unnecessary_evasion'],1)
        self.assertEqual(r['avoidance_summary']['codex']['v02']['all_turn_label_counts']['appropriate_limit_or_correction'],27)


if __name__=='__main__':unittest.main()
