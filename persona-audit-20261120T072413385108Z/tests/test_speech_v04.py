"""Version preservation and matched-input checks; not clinical validation."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from speech_module.core import MissingCaseDetail, TEMPLATES, V03_VERSION, VERSION, generate, verify_packet


class Version04Tests(unittest.TestCase):
    def test_v03_record_still_verifies_against_its_own_source_map(self):
        path=ROOT/'development/speech-m3-v02-v03-compare-v01/runs/DEV-M0-02/v03/turn01/packet.json'
        packet=json.loads(path.read_text())
        self.assertEqual(packet['module_version'],V03_VERSION)
        verify_packet(packet)

    def test_v04_changes_only_interaction_and_continuity_sections(self):
        def sections(version):
            text=TEMPLATES[version].read_text()
            return re.split(r'(?=\[R[1-8] )',text)
        old,new=sections(V03_VERSION),sections(VERSION)
        self.assertEqual(len(old),9);self.assertEqual(len(new),9)
        self.assertEqual([i for i,(a,b) in enumerate(zip(old,new)) if a!=b],[4,7])

    def test_case_inputs_questions_and_requirements_match_M3_exactly(self):
        old=json.loads((ROOT/'development/speech-m3-v02-v03-compare-v01/plan.json').read_text())
        new=json.loads((ROOT/'development/speech-m4-v02-v04-compare-v01/plan.json').read_text())
        for a,b in zip(old['cases'],new['cases']):
            for key in ['case_id','input','questions','required_fact_ids']:
                self.assertEqual(a[key],b[key])
        self.assertEqual(len(new['cases']),3)
        self.assertEqual(new['generation_model'],old['generation_model'])
        self.assertEqual(new['reasoning_effort'],old['reasoning_effort'])

    def test_both_modern_versions_block_unreviewed_generation(self):
        data=json.loads((ROOT/'development/speech-m0-v01/inputs/DEV-M0-01.json').read_text())
        calls=[]
        with tempfile.TemporaryDirectory() as tmp:
            for version in [V03_VERSION,VERSION]:
                with self.assertRaisesRegex(MissingCaseDetail,'question_not_reviewed'):
                    generate(data,lambda _:calls.append(1),Path(tmp)/version,module_version=version)
        self.assertEqual(calls,[])


if __name__=='__main__':unittest.main()
