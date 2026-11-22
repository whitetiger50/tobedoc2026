"""Compare sealed pairs with their original scores and independently verify the round order."""
from pathlib import Path
from statistics import mean

import run as study

HERE, r = study.HERE, study.r


def main():
    plan = r.read(study.PLAN)
    cases, frozen = r.load_frozen()
    verification = r.read(HERE/"reader-verification.json")
    assert verification["scores_sha256"] == r.digest(HERE/"scores.json")
    assert verification["blind_sha256"] == r.digest(r.BLIND)
    assert verification["reader_freeze_sha256"] == r.digest(r.FROZEN)
    assert study.original()[2] == plan["source_sha256"]
    scores = {(v["reader"],v["uid"]):v for v in r.read(HERE/"scores.json")}
    results, sessions = {}, set()
    for engine, rounds in plan["orders"].items():
        previous_finish = frozen["frozen_utc"]
        for n, order in enumerate(rounds,1):
            for pos, uid in enumerate(order,1):
                slot = plan["slots"][uid]
                root = r.ROOT/engine/uid
                first = root/r.read(root/"accepted.json")["attempt"]
                reason = r.read(first/"forms"/(uid+".json"))
                row = scores[engine,uid]
                assert reason["events"] == row["events"] and reason["status"] == row["status"]
                for scale in r.SCALES:
                    raw = [ev[scale] for ev in reason["events"]]
                    assert row[scale] == (mean(raw) if raw else None)
                file = first/("meta" if engine=="gpt" else "receipts")/(uid+".json")
                receipt = r.read(file)
                assert receipt["started_utc"] >= previous_finish
                previous_finish = receipt["finished_utc" if engine=="gpt" else "ended_utc"]
                session = receipt["cli_session_id" if engine=="gpt" else "session_id"]
                assert session not in sessions
                sessions.add(session)
                results[slot["old_uid"],engine,n] = {"elaboration":row["elaboration"],
                    "clarity":row["meaning_clarity"],"position":pos,"uid":uid}
    rows = []
    for item in plan["items"]:
        ratings = [[results[item["old_uid"],e,n] for e in r.ENGINES] for n in (1,2)]
        rounds = [[v["elaboration"] for v in round_] for round_ in ratings]
        valid = all(v is not None for pair in rounds for v in pair)
        rows.append({**item, "rounds_opus_gpt":rounds,"ratings":ratings,"fully_rated":valid,
            "exact_rounds":sum(pair==item["original_scores"] for pair in rounds) if valid else None,
            "opus_higher_rounds":sum(o>g for o,g in rounds) if valid else None,
            "disagreement_rounds":sum(o!=g for o,g in rounds) if valid else None})
    assert len(rows)==8 and len(scores)==len(sessions)==32
    assert all(cases[rec["uid"]]==cases[row["ratings"][0][0]["uid"]]
               for row in rows for reads in row["ratings"] for rec in reads)
    summary = {}
    for group in ("target","control","all"):
        group_rows = [x for x in rows if group=="all" or x["group"]==group]
        valid = [x for x in group_rows if x["fully_rated"]]
        summary[group] = {"n":len(group_rows),"complete":len(valid),
            "exact_both":sum(x["exact_rounds"]==2 for x in valid),
            "same_disagreement_direction_both":sum(x["opus_higher_rounds"]==2 for x in valid),
            "any_disagreement_rounds_histogram":{str(k):sum(x["disagreement_rounds"]==k for x in valid)
                                                  for k in range(3)},
            "between_round_exact":{e:sum(x["rounds_opus_gpt"][0][j]==x["rounds_opus_gpt"][1][j]
                                  for x in valid) for j,e in enumerate(r.ENGINES)}}
    r.save(HERE/"analysis.json",{"rows":rows, "summary":summary,"unique_sessions":len(sessions),
        "original_payloads_verified":8, "actual_order_verified":True,
        "source_sha256":plan["source_sha256"],"new_scores_sha256":verification["scores_sha256"]})
    for row in rows:
        print(row["case"],row["group"],row["original_scores"],row["rounds_opus_gpt"])
    print(summary)


if __name__ == "__main__":
    main()
