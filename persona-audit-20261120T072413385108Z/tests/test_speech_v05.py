"""Version and prompt-scope guards; these are not model-behavior or clinical tests."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from speech_module.core import V02_VERSION,V05_VERSION,TEMPLATES,MissingCaseDetail,build_packet,generate,verify_packet
spec=importlib.util.spec_from_file_location('make05',ROOT/'development/speech-m7-v02-v05-grounding-v01/make_v05.py')
make=importlib.util.module_from_spec(spec);spec.loader.exec_module(make)


class Version05Tests(unittest.TestCase):
    def test_only_added_fact_block_and_unchanged_disclosure_and_repetition(self):
        old=TEMPLATES[V02_VERSION].read_text();new=TEMPLATES[V05_VERSION].read_text()
        self.assertEqual(new.count(make.ADDITION),1)
        self.assertEqual(new.replace(make.ADDITION,'',1),old)
        marker='\n의사소통과 질문 대응:\n'
        self.assertEqual(old[old.index(marker):],new[new.index(marker):])

    def test_input_and_schema_unchanged_across_versions(self):
        plan=json.loads((ROOT/'development/speech-m6-generation-variability-v01/plan.json').read_text())
        for c in plan['cases']:
            for q,ids in zip(c['questions'],c['required_fact_ids']):
                data=json.loads(json.dumps(c['input']));data['current_question']=q
                a=build_packet(data,module_version=V02_VERSION,required_fact_ids=tuple(ids),question_reviewed=True)
                b=build_packet(data,module_version=V05_VERSION,required_fact_ids=tuple(ids),question_reviewed=True)
                self.assertEqual(a['input_sha256'],b['input_sha256']);verify_packet(b)

    def test_historical_v02_v03_v04_packets_still_verify(self):
        paths=['development/speech-m1-v01/runs-v02-functional/DEV-M0-01/packet.json',
               'development/speech-m3-v02-v03-compare-v01/runs/DEV-M0-02/v03/turn01/packet.json',
               'development/speech-m6-generation-variability-v01/runs/DEV-M0-03/rep01/v04/turn03/packet.json']
        for p in paths:verify_packet(json.loads((ROOT/p).read_text()))

    def test_v05_requires_existing_author_readiness_gate(self):
        data=json.loads((ROOT/'development/speech-m0-v01/inputs/DEV-M0-01.json').read_text());calls=[]
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(MissingCaseDetail):generate(data,lambda _:calls.append(1),Path(tmp)/'run',module_version=V05_VERSION)
        self.assertEqual(calls,[])


if __name__=='__main__':unittest.main()
