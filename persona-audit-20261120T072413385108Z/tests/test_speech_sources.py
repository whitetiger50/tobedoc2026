"""Version, optional-example, and provenance boundaries; no clinical-effect tests."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from speech_module.core import MissingCaseDetail, TEMPLATES, V02_VERSION, VERSION, build_packet, generate, import_response, prepare, verify_packet


def sample():
    data = json.loads((ROOT / "development/speech-m0-v01/inputs/DEV-M0-01.json").read_text())
    data["speech_examples"] = [{"context": "아침 식사를 물은 상황", "utterance": "빵 먹었어요.",
                                "fact_ids": ["breakfast"], "provenance": "synthetic_author_example_not_patient_data", "target_feature": "expression", "author_checked": True}]
    return data


class SourceVersionTests(unittest.TestCase):
    def test_unreviewed_live_question_blocks_without_backend_or_files(self):
        data = sample(); data.pop("speech_examples")
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "run"
            with self.assertRaisesRegex(MissingCaseDetail, "question_not_reviewed"):
                generate(data, lambda _: calls.append(1), out)
            self.assertEqual(calls, [])
            self.assertFalse(out.exists())

    def test_unreviewed_packet_cannot_import_manual_output(self):
        data = sample(); data.pop("speech_examples")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "run"
            prepare(data, out)
            with self.assertRaisesRegex(MissingCaseDetail, "question_not_reviewed"):
                import_response(out, {"text": "not an actual generation"})
            self.assertFalse((out / "raw_response.json").exists())

    def test_examples_require_opt_in_and_author_content_check(self):
        with self.assertRaises(ValueError): build_packet(sample())
        data = sample(); data["speech_examples"][0]["author_checked"] = False
        with self.assertRaises(ValueError): build_packet(data, allow_experimental_examples=True)

    def test_v02_packet_still_verifies_against_original_template(self):
        packet = json.loads((ROOT / "development/speech-m1-v01/runs-v02-functional/DEV-M0-01/packet.json").read_text())
        self.assertEqual(packet["module_version"], V02_VERSION)
        verify_packet(packet)

    def test_same_information_can_build_both_versions_without_examples(self):
        data = sample(); data.pop("speech_examples")
        old = build_packet(data, module_version=V02_VERSION)
        new = build_packet(data)
        self.assertEqual(old["input_sha256"], new["input_sha256"])
        self.assertNotEqual(old["template_sha256"], new["template_sha256"])
        self.assertEqual(new["module_version"], VERSION)

    def test_optional_examples_are_preserved_and_do_not_become_history(self):
        data = sample(); before = deepcopy(data)
        packet = build_packet(data, allow_experimental_examples=True)
        self.assertEqual(packet["input"], before)
        self.assertEqual(json.loads(packet["messages"][1]["content"]), before)
        self.assertEqual(data, before)
        verify_packet(packet)

    def test_example_requires_explicit_synthetic_provenance_and_known_fact_ids(self):
        for change in [lambda d: d["speech_examples"][0].update(provenance="actual_patient"),
                       lambda d: d["speech_examples"][0].update(fact_ids=["other_case_fact"]),
                       lambda d: d["patient"]["facts"][1].update(patient_knows=False)]:
            data = sample(); change(data)
            with self.assertRaises(ValueError): build_packet(data, allow_experimental_examples=True)

    def test_legacy_schema_does_not_silently_accept_new_example_information(self):
        with self.assertRaises(ValueError): build_packet(sample(), module_version=V02_VERSION)

    def test_source_mapping_hash_is_part_of_packet_integrity(self):
        packet = build_packet(sample(), allow_experimental_examples=True)
        path = TEMPLATES[VERSION].with_suffix(".sources.json")
        self.assertEqual(packet["prompt_source_map_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        packet["prompt_source_map_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "mismatch"): verify_packet(packet)


if __name__ == "__main__": unittest.main()
