"""Offline boundary/provenance checks. Fixture strings are not patient generation."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from speech_module.core import LEGACY_VERSION, MissingCaseDetail, build_packet, generate, import_response, prepare, verify_packet

ROOT = Path(__file__).resolve().parents[1]


def sample():
    return json.loads((ROOT / "development/speech-m0-v01/inputs/DEV-M0-01.json").read_text())


def fixture():
    return {"text": "FIXTURE ONLY: no patient utterance was generated.\n", "model_id": "NO_MODEL_TEST_FIXTURE",
            "model_version": "none", "settings": {}, "execution_mode": "test_fixture",
            "provenance": "deterministic unittest fixture, not research output"}


class SpeechModuleTests(unittest.TestCase):
    def test_missing_question_dependency_blocks_before_generation(self):
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "run"
            with self.assertRaisesRegex(MissingCaseDetail, "today_activity"):
                generate(sample(), lambda _: calls.append(1), directory, question_reviewed=True, required_fact_ids=("today_activity",))
            self.assertEqual(calls, [])
            self.assertFalse(directory.exists())

    def test_unknown_to_patient_does_not_satisfy_required_fact(self):
        data = sample()
        data["patient"]["facts"][0]["patient_knows"] = False
        with self.assertRaises(MissingCaseDetail):
            build_packet(data, required_fact_ids=(data["patient"]["facts"][0]["id"],))

    def test_dependency_and_legacy_versions_round_trip(self):
        packet = build_packet(sample(), required_fact_ids=("breakfast",))
        verify_packet(packet)
        legacy = json.loads((ROOT / "development/speech-m0-v01/prepared/DEV-M0-01/packet.json").read_text())
        self.assertEqual(legacy["module_version"], LEGACY_VERSION)
        verify_packet(legacy)

    def test_all_development_inputs_build_without_generation(self):
        paths = sorted((ROOT / "development/speech-m0-v01/inputs").glob("*.json"))
        self.assertEqual(len(paths), 3)
        for path in paths:
            self.assertEqual(build_packet(json.loads(path.read_text()))["partition"], "development")

    def test_complete_long_history_preserved_and_input_not_mutated(self):
        data = sample()
        data["history"] *= 100
        before = deepcopy(data)
        packet = build_packet(data)
        self.assertEqual(json.loads(packet["messages"][1]["content"]), before)
        packet["input"]["history"].clear()
        self.assertEqual(data, before)

    def test_meaning_changes_hash_but_key_order_does_not(self):
        a = sample()
        b = dict(reversed(list(a.items())))
        self.assertEqual(build_packet(a)["messages_sha256"], build_packet(b)["messages_sha256"])
        b["current_question"] += "再質問"
        self.assertNotEqual(build_packet(a)["messages_sha256"], build_packet(b)["messages_sha256"])

    def test_partition_is_explicit(self):
        data = sample()
        data["patient"]["partition"] = "heldout_confirmation"
        with self.assertRaisesRegex(ValueError, "partition mismatch"):
            build_packet(data)
        self.assertEqual(build_packet(data, expected_partition="heldout_confirmation")["partition"], "heldout_confirmation")

    def test_duplicate_fact_odd_history_and_unknown_field_rejected(self):
        changes = [lambda d: d["patient"]["facts"].append(deepcopy(d["patient"]["facts"][0])),
                   lambda d: d["history"].pop(), lambda d: d.update({"trust_score": 1})]
        for change in changes:
            data = sample()
            change(data)
            with self.assertRaises(ValueError):
                build_packet(data)

    def test_one_backend_call_exact_text_and_provenance_preserved(self):
        calls = []
        def backend(messages):
            calls.append(messages)
            messages.clear()  # Backend cannot mutate the saved packet.
            return fixture()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "run"
            text = generate(sample(), backend, directory, question_reviewed=True)
            self.assertEqual(len(calls), 1)
            self.assertEqual(text, fixture()["text"])
            self.assertEqual((directory / "patient.txt").read_text(), text)
            self.assertEqual(json.loads((directory / "result.json").read_text())["status"], "fixture_only")
            self.assertEqual(len(json.loads((directory / "packet.json").read_text())["messages"]), 2)
            with self.assertRaises(FileExistsError):
                generate(sample(), backend, directory, question_reviewed=True)
            self.assertEqual(len(calls), 1)

    def test_backend_failure_is_recorded_without_secret_or_retry(self):
        calls = []
        def fail(messages):
            calls.append(1)
            raise RuntimeError("SECRET_MUST_NOT_APPEAR_IN_LOG")
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "run"
            with self.assertRaises(RuntimeError):
                generate(sample(), fail, directory, question_reviewed=True)
            log = (directory / "result.json").read_text()
            self.assertNotIn("SECRET_MUST_NOT_APPEAR_IN_LOG", log)
            self.assertEqual(json.loads(log)["status"], "backend_failed_no_retry")
            self.assertEqual(calls, [1])

    def test_invalid_return_preserved_without_patient_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "run"
            bad = {"text": "missing provenance and metadata"}
            with self.assertRaises(ValueError):
                generate(sample(), lambda _: bad, directory, question_reviewed=True)
            self.assertEqual(json.loads((directory / "raw_response.json").read_text()), bad)
            self.assertFalse((directory / "patient.txt").exists())
            self.assertEqual(json.loads((directory / "result.json").read_text())["status"], "invalid_response_no_retry")

    def test_nonfinite_metadata_records_failure_without_partial_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "run"
            bad = fixture()
            bad["settings"] = {"temperature": float("nan")}
            with self.assertRaises(ValueError):
                generate(sample(), lambda _: bad, directory, question_reviewed=True)
            self.assertFalse((directory / "raw_response.json").exists())
            result = json.loads((directory / "result.json").read_text())
            self.assertEqual(result["status"], "unserializable_response_no_retry")
            self.assertFalse(result["raw_json_preserved"])

    def test_manual_import_hash_verification_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "run"
            packet = prepare(sample(), directory, question_reviewed=True)
            altered = deepcopy(packet)
            altered["input"]["current_question"] = "tampered"
            (directory / "packet.json").write_text(json.dumps(altered))
            with self.assertRaisesRegex(ValueError, "mismatch"):
                import_response(directory, fixture())
            self.assertFalse((directory / "raw_response.json").exists())
            (directory / "packet.json").write_text(json.dumps(packet))
            result = import_response(directory, fixture())
            self.assertEqual(result["source"], "manual_import_unverified")
            with self.assertRaises(FileExistsError):
                import_response(directory, fixture())


if __name__ == "__main__":
    unittest.main()
