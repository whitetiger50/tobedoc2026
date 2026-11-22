#!/usr/bin/env python3
"""Deterministic arithmetic for the proposed TLC-derived research index.

No model calls. This does not judge transcripts, implement a clinical TLC,
or aggregate a complete trial. Planned block slots must be retained.
"""
import argparse
import json
import math
from pathlib import Path

ITEMS = ("DER", "INC", "POS")
BLOCKS = 6


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def distance(value, target):
    return max(target[0] - value, 0.0, value - target[1])


def distance_bounds(bounds, target):
    low, high = bounds
    minimum = max(target[0] - high, 0.0, low - target[1])
    maximum = max(distance(low, target), distance(high, target))
    return [minimum, maximum]


def calculate(record):
    if set(record.get("scores", {})) != set(ITEMS):
        raise ValueError("All three item arrays are required, including null slots.")
    if set(record.get("targets", {})) != set(ITEMS):
        raise ValueError("Each item needs a target interval or explicit null=unspecified.")
    output = {"kind": record.get("kind", "unlabelled"), "interview_id": record.get("interview_id"),
              "clinical_tlc_score": False, "items": {}}
    errors = []
    for item in ITEMS:
        scores = record["scores"][item]
        if not isinstance(scores, list) or len(scores) != BLOCKS:
            raise ValueError(f"{item}: exactly six planned blocks are required.")
        for score in scores:
            if score is not None and (type(score) is not int or not 0 <= score <= 4):
                raise ValueError(f"{item}: block grade must be integer 0..4 or null.")
        target = record["targets"][item]
        if target is not None:
            if not isinstance(target, list) or len(target) != 2 or not all(number(x) for x in target):
                raise ValueError(f"{item}: target must be [lower,upper] or null.")
            if not 0 <= target[0] <= target[1] <= 4:
                raise ValueError(f"{item}: invalid target bounds.")
        known = [v for v in scores if v is not None]
        unknown = BLOCKS - len(known)
        bounds = [sum(known) / BLOCKS, (sum(known) + 4 * unknown) / BLOCKS]
        result = {"score": bounds[0] if unknown == 0 else None,
                  "score_identification_bounds": bounds,
                  "known_blocks": len(known), "unknown_blocks": unknown,
                  "grade_counts": {str(v): known.count(v) for v in range(5)},
                  "max_known_grade": max(known) if known else None,
                  "target": target}
        if target is not None:
            error = distance_bounds(bounds, target)
            result["target_distance_bounds"] = error
            result["underexpression_bounds"] = [max(target[0] - bounds[1], 0), max(target[0] - bounds[0], 0)]
            result["overexpression_bounds"] = [max(bounds[0] - target[1], 0), max(bounds[1] - target[1], 0)]
            errors.append(error)
        output["items"][item] = result
    output["specified_items"] = len(errors)
    output["equal_item_summary_error_bounds"] = (
        [sum(e[k] for e in errors) / len(errors) for k in range(2)] if errors else None)
    output["note"] = "Bounds reflect unassessable blocks, not confidence intervals. One-interview arithmetic only."
    return output


def self_test():
    def base():
        return {"kind": "arithmetic_example", "scores": {j: [0] * 6 for j in ITEMS},
                "targets": {j: [0, 0] for j in ITEMS}}
    x = base()
    assert calculate(x)["equal_item_summary_error_bounds"] == [0, 0]
    x["scores"]["DER"] = [None] * 6
    assert calculate(x)["items"]["DER"]["score"] is None
    assert calculate(x)["items"]["DER"]["target_distance_bounds"] == [0, 4]
    x["targets"]["DER"] = [2, 2]
    assert calculate(x)["items"]["DER"]["target_distance_bounds"] == [0, 2]
    assert distance_bounds([0, 1], [2, 3]) == [1, 2]
    assert distance_bounds([2, 3], [0, 1]) == [1, 2]
    assert distance_bounds([1, 2], [1, 2]) == [0, 0]
    x = base()
    x["targets"]["POS"] = None
    assert calculate(x)["specified_items"] == 2
    for invalid in ([0] * 5, [True] * 6, [0.5] * 6, [5] * 6):
        x = base()
        x["scores"]["INC"] = invalid
        try:
            calculate(x)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid grades/denominators must be rejected.")
    # Unknown ranges must contain every possible completion of this block.
    x = base()
    x["scores"]["DER"] = [0, 1, 2, 3, 4, None]
    x["targets"]["DER"] = [1.25, 1.5]
    lo, hi = calculate(x)["items"]["DER"]["target_distance_bounds"]
    for completion in range(5):
        value = distance((10 + completion) / 6, [1.25, 1.5])
        assert lo - 1e-12 <= value <= hi + 1e-12
    print(json.dumps({"self_test": "passed", "model_calls": 0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path)
    parser.add_argument("--allow-example", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    elif args.input:
        record = json.loads(args.input.read_text())
        if record.get("kind") == "arithmetic_example" and not args.allow_example:
            parser.error("Arithmetic example is not research data; use --allow-example explicitly.")
        print(json.dumps(calculate(record), ensure_ascii=False, indent=2))
    else:
        parser.error("Provide an input JSON or --self-test.")
