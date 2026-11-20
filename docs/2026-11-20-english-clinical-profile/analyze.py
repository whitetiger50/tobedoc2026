"""Summarize two independent readers' saved forms. No inference or imputation."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
from statistics import mean

from reader import FEATURES, STATUSES, validate
from study import ARMS, CASES, PROFILES, assignments, for_reader


def observed(row, rows, replies, ratings):
    try:
        dialogue = for_reader(row, rows, replies)
    except (FileNotFoundError, UnicodeError, ValueError):
        return "missing_reply_or_context", {}
    if not dialogue["answer"].strip():
        return "missing_reply", {}
    try:
        raw = json.loads((ratings / (row["blind_id"] + ".json")).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return "missing_rating", {}
    except (ValueError, UnicodeError):
        return "invalid_rating", {}
    result = validate(dialogue, raw)
    if result["form_status"] != "complete":
        return result["form_status"], {}
    return "complete", {k: v["status"] for k, v in result["items"].items()}


def agreement(left, right):
    # Binary agreement is conditional on two determinate ratings. Also retain the full table.
    table = Counter(zip(left, right))
    a = table["present", "present"]
    d = table["absent", "absent"]
    discordant = table["present", "absent"] + table["absent", "present"]
    n = a + d + discordant
    both_valid = sum(count for (x, y), count in table.items() if x in STATUSES and y in STATUSES)
    def ratio(x, y):
        return x / y if y else None
    return {"scheduled": len(left), "both_valid": both_valid,
            "four_status_agreement": ratio(sum(table[s, s] for s in STATUSES), both_valid),
            "both_determinate": n,
            "binary_agreement": ratio(a+d, n), "positive_specific_agreement": ratio(2*a, 2*a+discordant),
            "negative_specific_agreement": ratio(2*d, 2*d+discordant),
            "status_table": {x: {y: count for (k, y), count in table.items() if k == x}
                             for x in sorted(set(left))}}


def contrast(cells, feature, target):
    # Four paired cells per turn. Missing, uncertain and insufficient opportunity remain unknown.
    case_values = []
    bounds = []
    for case in CASES:
        turn_diffs, worst, best, arm_diffs = [], [], [], {arm: [] for arm in ARMS}
        for turn in (1, 2):
            estimates, low, high = [], 0, 0
            for arm, profile, weight in (
                (ARMS[1], target, 1), (ARMS[1], "usual", -1),
                (ARMS[0], target, -1), (ARMS[0], "usual", 1),
            ):
                status = cells[case, arm, profile, turn].get(feature)
                if status in ("present", "absent"):
                    value = int(status == "present") * weight
                    low += value
                    high += value
                    estimates.append(value)
                else:
                    low += min(0, weight)
                    high += max(0, weight)
            if len(estimates) == 4:
                turn_diffs.append(sum(estimates))
                arm_diffs[ARMS[1]].append(sum(estimates[:2]))
                arm_diffs[ARMS[0]].append(-sum(estimates[2:]))
            else:
                turn_diffs.append(None)
            worst.append(low)
            best.append(high)
        complete = all(x is not None for x in turn_diffs)
        case_values.append({"case": case, "turn_interactions": turn_diffs,
                            "within_arm_changes_on_paired_turns": {arm: mean(diffs) if complete else None
                                                                  for arm, diffs in arm_diffs.items()},
                            "mean_interaction": mean(turn_diffs) if complete else None})
        bounds.append((mean(worst), mean(best)))
    observed_values = [x["mean_interaction"] for x in case_values if x["mean_interaction"] is not None]
    loo = [mean(observed_values[:i] + observed_values[i+1:]) for i in range(len(observed_values))] if len(observed_values) > 1 else []
    return {"target_profile": target, "cases": case_values, "complete_cases": len(observed_values),
            "complete_case_mean": mean(observed_values) if observed_values else None,
            "leave_one_complete_case_out_range": [min(loo), max(loo)] if loo else None,
            "all_case_unknown_status_bounds": [mean(x for x, _ in bounds), mean(y for _, y in bounds)]}


def summarize(rows, pair):
    cells = {}
    result = {}
    for row, (_, items) in zip(rows, pair):
        cells[row["case_id"], row["arm"], row["profile"], row["turn"]] = items
    result["forms"] = dict(Counter(s for s, _ in pair))
    groups = []
    for arm in ARMS:
        for profile in PROFILES:
            items = [v for (c, a, p, t), v in cells.items() if (a, p) == (arm, profile)]
            for feature in FEATURES:
                counts = Counter(data.get(feature, "missing") for data in items)
                usable = counts["present"] + counts["absent"]
                groups.append({"arm": arm, "profile": profile, "item": feature,
                               "scheduled": len(items), "counts": {s: counts[s] for s in (*STATUSES, "missing")},
                               "positive_among_determinate": counts["present"] / usable if usable else None})
    result["groups"] = groups
    result["case_interactions"] = {f: contrast(cells, f, p) for f, p in
                                   (("DERAILMENT", "associative"), ("POVERTY_OF_CONTENT", "low_elaboration"))}
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("replies", type=Path)
    p.add_argument("reader_a", type=Path)
    p.add_argument("reader_b", type=Path)
    p.add_argument("--repeat-a", type=Path)
    p.add_argument("--repeat-b", type=Path)
    args = p.parse_args()
    dirs = [x.resolve() for x in (args.reader_a, args.reader_b, args.repeat_a, args.repeat_b) if x is not None]
    if len(set(dirs)) != len(dirs):
        p.error("Independent reads require distinct directories")
    if not all(x.is_dir() for x in [args.replies, *dirs]):
        p.error("Supply existing reply and rating directories")
    rows = assignments()
    output, pairs = {}, []
    lengths = {}
    for row in rows:
        try:
            text = for_reader(row, rows, args.replies)["answer"]
        except (FileNotFoundError, UnicodeError, ValueError):
            continue
        if text.strip():
            lengths[row["blind_id"]] = len(re.findall(r"[A-Za-z]+(?:['’][A-Za-z]+)*", text))
    output["length_by_arm_profile"] = []
    for arm in ARMS:
        for profile in PROFILES:
            words = [lengths[r["blind_id"]] for r in rows if r["arm"] == arm and r["profile"] == profile
                     and r["blind_id"] in lengths]
            output["length_by_arm_profile"].append({"arm": arm, "profile": profile,
                                                    "observed": len(words), "word_counts": words})
    for label, rating_dir, repeat_dir in (("reader_a", args.reader_a, args.repeat_a), ("reader_b", args.reader_b, args.repeat_b)):
        pair = [observed(row, rows, args.replies, rating_dir) for row in rows]
        pairs.append(pair)
        output[label] = summarize(rows, pair)
        if repeat_dir:
            selected = [(items, observed(row, rows, args.replies, repeat_dir)[1])
                        for row, (_, items) in zip(rows, pair) if row["repeat_read"]]
            output[label]["repeat_agreement"] = {f: agreement([a.get(f, "missing") for a, b in selected],
                                                               [b.get(f, "missing") for a, b in selected]) for f in FEATURES}
    output["between_readers"] = {f: agreement(*[[items.get(f, "missing") for _, items in pair] for pair in pairs])
                                 for f in FEATURES}
    print(json.dumps(output, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
