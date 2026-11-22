"""Recheck stored readings against local dialogue; emit no quotations or reader rationales."""
from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
import read_local as run


def main():
    os.umask(0o077)
    files = run.HERE / "private"
    manifest = json.loads((files / "manifest.json").read_text())
    if manifest["reader_code_sha256"] != sha256(Path(run.__file__).read_bytes()).hexdigest():
        raise ValueError("Reader code changed")
    counts = json.loads((run.HERE / "counts.json").read_text())
    tallies = {}
    anchors = 0
    repairs = Counter()
    report = {}
    short_readings = {f: Counter() for f in run.FEATURES}
    for n, (q, token, data) in enumerate(run.collect(), 1):
        entry = manifest["cases"][n-1]
        if (entry["blind"], entry["group"], entry["source_digest"], entry["input_digest"]) != (
                n, q, token, run.digest(run.dump(data))):
            raise ValueError("Input identity check failed")
        record = json.loads((files / f"read-{n:02}.json").read_text())
        short = len(run.WORD.findall(data["reply"].lower().replace("’", "'"))) < 10
        fields = ["response", *run.FEATURES]
        if set(record["rows"]) | set(record["invalid"]) != set(fields):
            raise ValueError("Reader field omitted")
        group = tallies.setdefault(q, {f: Counter() for f in fields})
        extra = report.setdefault(q, {"n": 0, "all_four_definite": 0, "none_definite": 0,
                                      "ambiguous_type_options": [], "also_requested_clarification": 0})
        extra["n"] += 1
        definite = 0
        repairs.update(record["anchor_repairs"])
        for f in fields:
            row = record["rows"].get(f)
            if row is None:
                group[f]["technical_missing"] += 1
                if short and f in short_readings:
                    short_readings[f]["technical_missing"] += 1
                continue
            for ev in row["evidence"]:
                a, b = ev["start"], ev["end"]
                if not (0 <= a < b <= len(data["reply"]) and data["reply"][a:b] == ev["quote"]):
                    raise ValueError("Evidence does not match source")
                anchors += 1
            initial = record["response"] if f == "response" else record["clinical"][f]
            key = "type" if f == "response" else "status"
            if initial[key] != row[key] or initial["reason"] != row["reason"]:
                raise ValueError("Initial judgments or reasons were modified")
            group[f][row[key]] += 1
            if f != "response":
                definite += row["status"] in {"present", "absent"}
                if short:
                    short_readings[f][row["status"]] += 1
            else:
                if row["type"] == "ambiguous":
                    extra["ambiguous_type_options"].append(row["alternatives"])
                extra["also_requested_clarification"] += int(row["also_requests_clarification"])
        extra["all_four_definite"] += int(definite == 4)
        extra["none_definite"] += int(definite == 0)
    if tallies != counts or any(sum(c.values()) != 7 for g in tallies.values() for c in g.values()):
        raise ValueError("Question-level tally mismatch")
    result = {"verified_input_pairs": 14, "anchors_verified": anchors,
              "anchor_only_repairs_by_field": dict(repairs),
              "under_10_words_quality_check_only": short_readings,
              "groups": report, "reader_model_digest": run.DIGEST}
    run.write(run.HERE / "verification.json", result)
    print(run.dump(result))


if __name__ == "__main__":
    main()
