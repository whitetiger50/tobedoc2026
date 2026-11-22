"""Example isolation and historical packet integrity; not clinical effect tests."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from speech_module.core import V02_VERSION,V06_VERSION,TEMPLATES,MissingCaseDetail,build_packet,generate,verify_packet


def refs():
    d=json.loads((ROOT/'development/speech-m9-style-examples-v01/reference-examples.json').read_text())
    return [{k:e[k] for k in ['reference_id','facts','clinician','patient']} for e in d['examples']]


class ExampleTests(unittest.TestCase):
    def test_v02_prefix_and_shared_scaffold(self):
        base=TEMPLATES[V02_VERSION].read_text();new=TEMPLATES[V06_VERSION].read_text()
        self.assertEqual(new,base+(ROOT/'development/speech-m9-style-examples-v01/common-scaffold.txt').read_text())

    def test_only_reference_list_changes_model_input(self):
        c=json.loads((ROOT/'development/speech-m8-stress-grounding-v01/plan.json').read_text())['cases'][0]
        a=build_packet(c['input'],module_version=V06_VERSION,style_reference_examples=[],question_reviewed=True)
        b=build_packet(c['input'],module_version=V06_VERSION,style_reference_examples=refs(),question_reviewed=True)
        self.assertEqual(a['input'],b['input']);self.assertEqual(a['input_sha256'],b['input_sha256'])
        self.assertEqual(a['messages'][0],b['messages'][0]);self.assertNotEqual(a['messages_sha256'],b['messages_sha256'])
        left=json.loads(a['messages'][1]['content']);right=json.loads(b['messages'][1]['content'])
        left.pop('style_reference_examples');right.pop('style_reference_examples');self.assertEqual(left,right)
        verify_packet(a);verify_packet(b)

    def test_example_tampering_and_wrong_version_rejected(self):
        c=json.loads((ROOT/'development/speech-m8-stress-grounding-v01/plan.json').read_text())['cases'][0]
        with self.assertRaises(ValueError):build_packet(c['input'],module_version=V02_VERSION,style_reference_examples=refs())
        p=build_packet(c['input'],module_version=V06_VERSION,style_reference_examples=refs(),question_reviewed=True)
        p['style_reference_examples'][0]['patient']+='tamper'
        with self.assertRaises(ValueError):verify_packet(p)

    def test_unreviewed_generation_remains_blocked(self):
        c=json.loads((ROOT/'development/speech-m8-stress-grounding-v01/plan.json').read_text())['cases'][0];calls=[]
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(MissingCaseDetail):generate(c['input'],lambda _:calls.append(1),Path(tmp)/'run',module_version=V06_VERSION,style_reference_examples=refs())
        self.assertEqual(calls,[])

    def test_historical_packet_still_verifies(self):
        p=ROOT/'development/speech-m8-stress-grounding-v01/runs/DEV-M0-03/rep01/v05/turn05/packet.json'
        verify_packet(json.loads(p.read_text()))


if __name__=='__main__':unittest.main()
