"""Offline aggregation/quote validation; no model calls or synthetic clinical scores as results."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("speech_dev_review", ROOT / "development/speech-m1-v01/review_dev.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def fixtures():
    packet = {"cases": [{"blind_id": "FIXTURE-A", "generated_dialogue": [
        {"turn_id": "D01", "speaker": "clinician", "text": "CLINICIAN FIXTURE"},
        {"turn_id": "P01", "speaker": "patient", "text": "ARITHMETIC FIXTURE ONLY"}]}]}
    review = {"reviews": [{"blind_id": "FIXTURE-A", "score": 2, "reason": "fixture, not clinical evidence",
                           "evidence": [{"patient_turn_id": "P01", "quote": "FIXTURE ONLY"}], "issues": []}]}
    other = deepcopy(review)
    other["reviews"][0]["score"] = 3
    return packet, {"codex": review, "claude": other}


class DevReviewTests(unittest.TestCase):
    def test_arithmetic_mean_preserves_half_point_and_originals(self):
        packet, reviews = fixtures()
        result = MODULE.aggregate(reviews, packet)
        self.assertEqual(result["cases"][0]["arithmetic_mean"], 2.5)
        self.assertEqual(result["cases"][0]["original_scores"], {"codex": 2, "claude": 3})

    def test_missing_reviewer_never_imputed(self):
        packet, reviews = fixtures()
        reviews.pop("claude")
        with self.assertRaisesRegex(ValueError, "Both reviewers"):
            MODULE.aggregate(reviews, packet)

    def test_invalid_numeric_values_rejected(self):
        for bad in [True, 0, 5, 2.5, "3", None]:
            packet, reviews = fixtures()
            reviews["codex"]["reviews"][0]["score"] = bad
            with self.assertRaisesRegex(ValueError, "integer"):
                MODULE.aggregate(reviews, packet)

    def test_fabricated_or_clinician_quote_rejected(self):
        for turn, quote in [("P01", "NOT IN OUTPUT"), ("D01", "CLINICIAN FIXTURE")]:
            packet, reviews = fixtures()
            reviews["codex"]["reviews"][0]["evidence"] = [{"patient_turn_id": turn, "quote": quote}]
            with self.assertRaises(ValueError):
                MODULE.aggregate(reviews, packet)

    def test_duplicate_case_cannot_replace_another(self):
        packet, reviews = fixtures()
        extra = deepcopy(packet["cases"][0])
        extra["blind_id"] = "FIXTURE-B"
        packet["cases"].append(extra)
        for review in reviews.values():
            review["reviews"].append(deepcopy(review["reviews"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            MODULE.aggregate(reviews, packet)


if __name__ == "__main__":
    unittest.main()
