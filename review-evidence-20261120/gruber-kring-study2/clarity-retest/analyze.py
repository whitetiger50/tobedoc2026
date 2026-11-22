"""Audit identical packets, session isolation and order; compare all first readings offline."""
from collections import Counter
from datetime import datetime
import json

from collect import BOUNDARY, HERE, fixed, signatures
import summarize as prior_verifier

SCALES = ("meaning_clarity", "elaboration")


def audit(engine, orders, cases, frozen):
    rows = {}
    sessions, packet_hashes = set(), {}
    last_end = None
    for r, order in enumerate(orders, 1):
        parent = HERE / f"round{r}"
        prior_verifier.HERE = parent
        folder = parent / engine
        assert len(list((folder / "forms").glob("*.json"))) == len(cases)
        assert not list((folder / "meta").glob("*transport-failure*"))
        for pos, k in enumerate(order, 1):
            record = prior_verifier.load_scores(engine, k, cases[k], frozen)
            subfolder = "meta" if engine == "gpt" else "receipts"
            receipt = fixed.read(folder / subfolder / (k + ".json"))
            start = datetime.fromisoformat(receipt["started_utc"])
            end = datetime.fromisoformat(receipt["finished_utc" if engine == "gpt" else "ended_utc"])
            assert (last_end is None or start >= last_end) and end >= start
            last_end = end
            assert record["session"] not in sessions
            sessions.add(record["session"])
            assert packet_hashes.setdefault(k, receipt["packet_sha256"]) == receipt["packet_sha256"]
            rows.setdefault(k, []).append({"position": pos, **record})
    return rows, packet_hashes


def reader_results(rows, groups):
    middle = [ids[1] for ids in groups.values()]
    anchors = [k for k in rows if k not in middle]
    def clarity(k, r):
        return rows[k][r]["scores"]["meaning_clarity"]
    def triplet_ok(ids, r):
        return [clarity(k, r) for k in ids] == [1, 2, 3]
    rounds = []
    for r in (0, 1):
        rounds.append({
            "exact_middle": sum(clarity(k, r) == 2 for k in middle),
            "anchors_scored_2": sum(clarity(k, r) == 2 for k in anchors),
            "exact_anchors": sum(clarity(ids[i], r) == i + 1 for ids in groups.values() for i in (0, 2)),
            "fully_distinguished": sum(triplet_ok(ids, r) for ids in groups.values())
        })
    repeat = {}
    for scale in SCALES:
        transitions = Counter((a["scores"][scale], b["scores"][scale]) for a, b in rows.values())
        repeat[scale] = {"exact": sum(n for (a, b), n in transitions.items() if a is not None and a == b),
                         "transitions": {f"{a} -> {b}": n for (a, b), n in transitions.items()}}
    return {"rounds": rounds, "retest": repeat,
            "middle_2_twice": sum(clarity(k, 0) == clarity(k, 1) == 2 for k in middle),
            "fully_distinguished_twice": sum(all(triplet_ok(ids, r) for r in (0, 1)) for ids in groups.values())}


def main():
    frozen = fixed.read(HERE / "freeze.json")
    assert frozen["sha256"] == signatures()
    assert fixed.hashes() == fixed.read(BOUNDARY / "freeze.json")["sha256"]
    plan = fixed.read(HERE / "plan.json")
    cases = fixed.read(HERE / "examples.json")
    records, summaries, packet_hashes = {}, {}, {}
    for engine in ("opus", "gpt"):
        records[engine], packet_hashes[engine] = audit(engine, plan["orders"][engine], cases, frozen["frozen_utc"])
        summaries[engine] = reader_results(records[engine], plan["triplets_in_expected_clarity_order"])
    assert packet_hashes["opus"] == packet_hashes["gpt"]
    assert len({r["session"] for rows in records.values() for pair in rows.values() for r in pair}) == 36
    agreement = {}
    for scale in SCALES:
        agreement[scale] = []
        for r in (0, 1):
            pairs = [(records["opus"][k][r]["scores"][scale], records["gpt"][k][r]["scores"][scale]) for k in cases]
            agreement[scale].append(sum(a is not None and a == b for a, b in pairs))
    summary = {"unique_examples": len(cases), "readings": 36, "reader_summary": summaries,
               "between_reader_exact_by_round": agreement, "rows": records}
    (HERE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps([summaries, agreement], indent=2))


if __name__ == "__main__":
    main()
