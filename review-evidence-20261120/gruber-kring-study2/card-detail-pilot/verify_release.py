"""Audit sealed first responses, matching, timing, and exact paired tests."""
from collections import Counter, defaultdict
from datetime import datetime
from fractions import Fraction
import json
from pathlib import Path
from statistics import median

import read_pilot
import prepare_plan as plan

HERE = Path(__file__).resolve().parent
read = plan.load
digest = plan.digest
save = read_pilot.reader.save


def signed_tail(values):
    counts = Counter({0: 1})
    for v in values:
        new = Counter()
        for total, n in counts.items():
            new[total + v] += n
            new[total - v] += n
        counts = new
    return Fraction(sum(n for total, n in counts.items() if total >= sum(values)), sum(counts.values()))


def seconds(a, b):
    return (datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds()


def main():
    verify = read(HERE / "reader-verification.json")
    analysis = read(HERE / "analysis.json")
    assert verify["scores_sha256"] == digest(HERE / "scores.json")
    for relative, expected in analysis["sources_sha256"].items():
        assert digest(HERE / relative) == expected
    for relative, expected in read(HERE / "plan.json")["source_sha256"].items():
        assert digest(HERE.parent / relative) == expected
    slots = read(HERE / "private/schedule.json")
    blind = {r["uid"]: r for r in read(HERE / "blind.json")}
    freeze = read(HERE / "freeze.json")
    raw_values = {}
    sessions = set()
    starts, ends = [], []
    for slot in slots:
        job = slot["job"]
        rec = read(HERE / "private/generated" / (job + ".json"))
        packet_path = HERE / "private/messages" / (job + ".json")
        assert digest(packet_path) == rec["packet_sha256"] == freeze["packet_sha256"][job]
        assert rec["session"] not in sessions
        sessions.add(rec["session"])
        starts.append(rec["started_utc"])
        ends.append(rec["completed_utc"])
        item = blind[slot["uid"]]
        assert rec["raw"] == item["answer"]
        source_question = json.loads(read(packet_path)["user"])["current_question"].split("\n\n")[-1]
        assert source_question == item["question"] and set(item) == {"question","answer","uid"}
    assert freeze["frozen_utc"] <= starts[0] and all(a <= b for a,b in zip(starts,ends))
    assert all(a <= b for a,b in zip(ends,starts[1:]))
    cases, reader_freeze = read_pilot.reader.load_frozen()
    assert ends[-1] <= reader_freeze["frozen_utc"]
    for engine in ("opus", "gpt"):
        for uid, dialogue in cases.items():
            folder = HERE / "readers" / engine / uid
            attempt = folder / read(folder / "accepted.json")["attempt"]
            raw, sid, _ = read_pilot.reader.verified_response(
                engine, attempt, uid, read_pilot.reader.packet_bytes(dialogue), reader_freeze["frozen_utc"])
            assert sid not in sessions
            sessions.add(sid)
            form = json.loads(raw)
            raw_values[engine,uid] = (form["status"],[event["elaboration"] for event in form["events"]])
    for engine in ("opus", "gpt"):
        cards = defaultdict(int)
        pairs = defaultdict(dict)
        for slot in slots:
            status, values = raw_values[engine,slot["uid"]]
            pairs[slot["case"],slot["arm"]][slot["version"]] = (
                int(any(v > 1 for v in values)) if status == "rated" and values else None)
        marginal = Counter()
        for (case, arm), pair in pairs.items():
            a,b = pair["full"],pair["core"]
            cards[case] += b-a if None not in (a,b) else 0
            for version,x in pair.items():
                if x == 0:
                    marginal[arm,version] += 1
        res = analysis["readers"][engine]["groups"]
        for arm in plan.ARMS:
            for v in ("core","full"):
                assert res[arm]["marginal"][v]["elaboration_states"]["one"] == marginal[arm,v]
        assert dict(cards) == res["all"]["card_net"]
        p = res["all"]["randomization"]
        assert signed_tail(cards.values()) == Fraction(p["count_ge"], p["allocations"])
    gaps = [seconds(starts[i], starts[i+1]) for i in range(0,72,2)]
    save(HERE / "release-check.json", {"unique_generation_and_reader_sessions": len(sessions),
        "unaltered_answers_and_questions_checked": len(blind), "raw_reader_forms_checked": len(raw_values),
        "slot_launch_order_verified": True, "within_pair_start_gap_seconds":
        {"min":min(gaps), "median":median(gaps), "max":max(gaps)}, "reader_exact_tails_recomputed":2,
        "analysis_sha256": digest(HERE / "analysis.json"),
        "prior_source_hashes_checked":len(read(HERE / "plan.json")["source_sha256"])})
    assert len(sessions) == 216
    print(f"Verified {len(blind)} raw answers, {len(raw_values)} raw readings, and 2 exact tails.")


if __name__ == "__main__":
    main()
