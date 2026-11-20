#!/usr/bin/env python3
"""Read a supplied snapshot and print bounded historical checks as JSON.

Standard library only. No imports or execution of snapshot code, writes to the
snapshot, model calls, or recursive file discovery. M18 schema validity is a
recount of saved validator decisions, not a new implementation of that schema.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import itertools
import json
from pathlib import Path
import re
import statistics as stats


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fingerprint(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def normalize(text):
    text = text.lower().replace("–", " ").replace("-", " ").replace("’", "'")
    return re.sub(r"\s+", " ", text).strip()


def mention(text, fact):
    return any(re.search(r"(?<![\w.])" + re.escape(normalize(alias))
                         + r"(?!\w|\.\d|,\d)", normalize(text))
               for alias in fact["aliases"])


class Snapshot:
    def __init__(self, root):
        self.root = root.resolve(strict=True)

    def path(self, relative):
        target = (self.root / relative).resolve(strict=True)
        require(target.is_relative_to(self.root), "Source escaped snapshot")
        return target

    def read(self, relative):
        return json.loads(self.path(relative).read_text(encoding="utf-8"))

    def sha(self, relative):
        return hashlib.sha256(self.path(relative).read_bytes()).hexdigest()


def check_shared(source):
    base = "pilot/runs/shared-verbosity-v02/"
    plan = source.read(base + "plan.json")
    conditions = source.read(base + "conditions.json")
    saved = {r["condition_id"]: r for r in source.read(
        "analysis/shared-verbosity-v02/response-metrics.json")}
    require(len(conditions) == len(saved) == 80, "Shared response count changed")
    require(fingerprint(conditions) == plan["conditions_sha256"], "Conditions hash mismatch")
    sources = {}
    for record in plan["source_provenance"]:
        relative = "evidence/snapshots/" + record["id"] + ".txt"
        sources[relative] = source.sha(relative)
        require(sources[relative] == record["sha256"], "Module source hash mismatch")
    counts = Counter()
    arms = defaultdict(list)
    for condition in conditions:
        key = condition["condition_id"]
        require(re.fullmatch(r"SV-V[1-4]-Q[AB]-R[89]-(?:neutral|simple_verbose|psi_verbose|sim_verbose|sim_concise)", key),
                "Unexpected shared condition")
        raw = source.read(base + "responses/" + key + ".json")
        request = source.read(base + "requests/" + key + ".json")
        text = raw["response_text"]
        words = len(re.findall(r"[A-Za-z0-9]+(?:['’\-][A-Za-z0-9]+)*", text))
        refs = sum(mention(text, fact) for fact in condition["facts"]
                   if fact["domain"] == condition["target_event"])
        checks = {
            "raw_text_matches": text == raw["raw_response"]["message"]["content"],
            "request_hash_matches": fingerprint(request["payload"]) == raw["request_sha256"] == request["request_sha256"],
            "prompt_hash_matches": fingerprint({k: condition[k] for k in ("system_prompt", "interview")}) == raw["prompt_sha256"] == condition["prompt_sha256"],
            "model_matches": raw["model_digest"] == plan["model_digest"],
            "normal_stop": raw["raw_response"]["done_reason"] == "stop",
            "non_fixture": raw["is_fixture"] is False,
            "saved_metrics_match": words == saved[key]["word_count"] and refs == saved[key]["requested_refs"],
        }
        for name, passed in checks.items():
            require(passed, "Shared check failed: " + name + ":" + key)
            counts[name] += 1
        arms[condition["style_id"]].append((words, refs, raw["raw_response"]["eval_count"]))
    summary = {arm: {"responses": len(rows), "mean_words": stats.mean(r[0] for r in rows),
                     "requested_references": sum(r[1] for r in rows),
                     "reference_denominator": 4 * len(rows),
                     "maximum_output_tokens": max(r[2] for r in rows)}
               for arm, rows in sorted(arms.items())}
    return {"responses": len(conditions), "checks": dict(sorted(counts.items())),
            "source_sha256": sources, "conditions_sha256": fingerprint(conditions),
            "arms": summary,
            "psi_minus_simple_words": summary["psi_verbose"]["mean_words"] - summary["simple_verbose"]["mean_words"],
            "sim_minus_simple_words": summary["sim_verbose"]["mean_words"] - summary["simple_verbose"]["mean_words"],
            "scope": "Extracted instruction modules on one Qwen backend; not native-system or clinical validation."}


WORD = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)*")


def team_metrics(text):
    tokens = [m.group().lower().replace("’", "'") for m in WORD.finditer(text)]
    grams = [tuple(tokens[i:i + 3]) for i in range(len(tokens) - 2)]
    return {"words": len(tokens),
            "repeated_trigram_fraction": (len(grams) - len(set(grams))) / len(grams),
            "mattr50": stats.mean(len(set(tokens[i:i + 50])) / 50
                                  for i in range(len(tokens) - 49))}


def check_team(source):
    config = source.read("config/team-corpus-v01.json")
    relative = config["input"]
    manifest = source.read("data/team-corpus-20261104/manifest.json")
    record = next(r for r in manifest["files"] if r["file"] == "utterances.csv")
    require(source.sha(relative) == record["sha256"], "Team corpus hash mismatch")
    with source.path(relative).open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    key = lambda row: (row["generator"], row["q_id"], row["condition"])
    index = {key(row): team_metrics(row["text"]) for row in rows}
    require(len(index) == len(rows) == 228, "Team count or duplicate cell changed")
    conditions = ["N0", "NMULTI", "CIRC1", "CIRC2"] + [t + str(level)
                  for t in ("DER", "TAN", "INC", "PER", "CLANG") for level in (1, 2, 3)]
    expected = set(itertools.product(("Claude", "GPT-4.1"),
                   [f"Q0{i}" for i in range(1, 7)], conditions))
    require(set(index) == expected, "Team grid changed")
    with source.path("analysis/team-corpus-v01/features.csv").open(encoding="utf-8", newline="") as handle:
        saved = {key(row): row for row in csv.DictReader(handle)}
    for cell, metrics in index.items():
        require(all(abs(value - float(saved[cell][name])) < 1e-12
                    for name, value in metrics.items()), "Team saved feature mismatch")
    contrasts = {}
    for generator in ("Claude", "GPT-4.1"):
        differences = [index[generator, f"Q0{i}", "PER3"]["repeated_trigram_fraction"]
                       - index[generator, f"Q0{i}", "N0"]["repeated_trigram_fraction"]
                       for i in range(1, 7)]
        observed = abs(stats.mean(differences))
        p = sum(abs(stats.mean(x * sign for x, sign in zip(differences, signs))) >= observed - 1e-12
                for signs in itertools.product((-1, 1), repeat=6)) / 64
        inc = [index[generator, f"Q0{i}", "INC3"]["mattr50"]
               - index[generator, f"Q0{i}", "N0"]["mattr50"] for i in range(1, 7)]
        contrasts[generator] = {"per3_minus_n0_trigram": stats.mean(differences),
                               "positive_questions": sum(x > 0 for x in differences),
                               "question_count": 6, "exact_sign_flip_p": p,
                               "inc3_minus_n0_mattr50": stats.mean(inc),
                               "inc_positive_questions": sum(x > 0 for x in inc)}
    running = 0
    for rank, cell in enumerate(sorted(contrasts.values(), key=lambda x: x["exact_sign_flip_p"])):
        running = max(running, min(1, (2 - rank) * cell["exact_sign_flip_p"]))
        cell["holm_two_tests"] = running
    lengths = [cell["words"] for cell in index.values()]
    return {"source_sha256": source.sha(relative), "rows": len(rows), "unique_cells": len(index),
            "unique_texts": len({r["text"] for r in rows}), "personas": len({r["persona"] for r in rows}),
            "saved_feature_rows_matched": len(index),
            "lexical_words": {"minimum": min(lengths), "median": stats.median(lengths),
                              "maximum": max(lengths), "within_150_170": sum(150 <= n <= 170 for n in lengths)},
            "contrasts": contrasts,
            "scope": "Exploratory synthetic corpus; generator and generation procedure confounded; no clinical ratings recomputed."}


def check_return(source):
    relative = "analysis/return-control-ablation-v01/response-metrics.jsonl"
    rows = [json.loads(line) for line in source.path(relative).read_text(encoding="utf-8").splitlines()]
    require(len(rows) == 64, "Return-control row count changed")
    groups = defaultdict(list)
    for row in rows:
        groups[row["task_mode"], row["arm"]].append(row)
    cells = {}
    for (mode, arm), group in sorted(groups.items()):
        non_echo = [r for r in group if not r["complete_prefix_echo"]]
        cells[mode + ":" + arm] = {"responses": len(group),
            "other_event_present": sum(r["other_present"] for r in group),
            "primary_return": sum(r["primary_return"] for r in group),
            "non_echo_responses": len(non_echo),
            "non_echo_primary_return": sum(r["primary_return"] for r in non_echo)}
    return {"source_sha256": source.sha(relative), "rows": len(rows), "cells": cells,
            "scope": "Recount of saved response-level annotations, not independent semantic reannotation."}


def parse_rating(text):
    """Same JSON extraction rule as the frozen M12/M18 parser; no JSON repair."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        require(lines[-1].strip() == "```", "Unclosed JSON fence")
        text = "\n".join(lines[1:-1])
    value = json.loads(text)
    require(isinstance(value, dict), "Expected one JSON object")
    return value


def check_m18(source):
    base = "development/rubric-comparison-m18-v01/"
    slots = source.read(base + "schedule.json")["slots"]
    corpus = source.read(base + "corpus.json")
    require(corpus["final12_used"] == 0, "Development corpus boundary changed")
    natural = {r["item_id"] for r in corpus["items"] if r["kind"] == "natural_generated" and r["condition"] == "N"}
    require(len(slots) == 252 and len(natural) == 9, "M18 schedule or natural count changed")
    keys = {(s["item_id"], s["criterion"], s["provider"], s["repetition"]) for s in slots}
    require(len(keys) == 252, "Duplicate M18 schedule slot")
    cells = defaultdict(Counter)
    distributions = defaultdict(Counter)
    natural_by_item = defaultdict(dict)
    failures = []
    source_hashes = []
    for slot in slots:
        require(slot["item_id"].startswith("DEV-M18-") and slot["provider"] in ("codex", "claude")
                and slot["criterion"] in ("realism", "ccf")
                and re.fullmatch(r"[0-9a-f]{18}", slot["opaque_id"]), "Unexpected M18 slot")
        directory = base + "reviews/" + slot["provider"] + "/" + slot["opaque_id"] + "/"
        saved = source.read(directory + "validated.json")
        response = directory + "response.txt"
        source_hashes.append([response, source.sha(response)])
        cell = slot["criterion"] + ":" + slot["provider"]
        cells[cell]["responses"] += 1
        try:
            raw = parse_rating(source.path(response).read_text(encoding="utf-8"))
            cells[cell]["json_objects_parsed"] += 1
            score = raw.get("realism_score")
            score = score if type(score) is int and 1 <= score <= 4 else None
        except (ValueError, TypeError) as error:
            score = None
            failures.append({"item_id": slot["item_id"], "criterion": slot["criterion"],
                             "provider": slot["provider"], "repetition": slot["repetition"],
                             "failure_type": type(error).__name__, "response": response})
        require(score == saved["realism_score"] and (score is not None) == saved["realism_numeric_valid"],
                "M18 reparsed numeric field mismatch")
        require(saved["fully_schema_valid"] == (not saved["schema_errors"]), "Saved schema status inconsistent")
        cells[cell]["numeric_valid"] += score is not None
        cells[cell]["saved_schema_pass"] += saved["fully_schema_valid"]
        cells[cell]["numeric_status_matches_saved"] += 1
        if slot["item_id"] in natural:
            distributions[cell][str(score) if score is not None else "missing"] += 1
            natural_by_item[cell, slot["item_id"]][slot["repetition"]] = score
    natural_cells = {}
    for cell in sorted(cells):
        require(cells[cell]["responses"] == 63, "M18 cell denominator changed")
        pairs = []
        complete = []
        for item in sorted(natural):
            scores = natural_by_item[cell, item]
            require(set(scores) == {1, 2, 3}, "Missing natural repetition")
            valid = [s for s in scores.values() if s is not None]
            pairs.extend(a == b for a, b in itertools.combinations(valid, 2))
            if len(valid) == 3:
                complete.append(len(set(valid)) == 1)
        natural_cells[cell] = {"planned_ratings": 27, "score_distribution": dict(sorted(distributions[cell].items())),
                              "available_pairs": len(pairs), "equal_pairs": sum(pairs),
                              "complete_dialogues": len(complete), "identical_complete_triples": sum(complete)}
    total = Counter()
    for cell in cells.values():
        total.update(cell)
    return {"source_schedule_sha256": source.sha(base + "schedule.json"),
            "response_manifest_sha256": fingerprint(sorted(source_hashes)),
            "schedule_slots": len(slots), "unique_scheduled_items": len({s["item_id"] for s in slots}),
            "natural_dialogues": len(natural), "totals": dict(sorted(total.items())),
            "cells": {key: dict(sorted(value.items())) for key, value in sorted(cells.items())},
            "natural_cells": natural_cells, "json_parse_failures": failures,
            "scope": "Raw numeric scores independently reparsed without repairs; schema passes recount saved validator decisions, not independent schema revalidation. Constant natural scores cannot establish fine discrimination or clinical validity."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="Read-only source snapshot root")
    args = parser.parse_args()
    source = Snapshot(args.snapshot)
    result = {"schema_version": 1, "mode": "read_only_real_records",
              "shared_verbosity": check_shared(source), "team_corpus": check_team(source),
              "return_control": check_return(source), "m18": check_m18(source)}
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
