"""Verify all first readings, then pair rounds for the four planned comparisons."""
from collections import Counter
from statistics import mean

from run import HERE, PLAN, r

LABELS = {"original":"추가 없음", "repeat":"반복만", "mug":"머그잔만", "both":"반복과 머그잔"}
CONTRASTS = {"repeat_without_mug":("original","repeat"), "repeat_with_mug":("mug","both"),
             "mug_without_repeat":("original","mug"), "mug_with_repeat":("repeat","both")}


def main():
    bank, freeze = r.load_frozen()
    p = r.read(PLAN)
    receipt = r.read(HERE/"reader-verification.json")
    assert receipt["scores_sha256"] == r.digest(HERE/"scores.json")
    assert receipt["reader_freeze_sha256"] == r.digest(r.FROZEN)
    scores = {(s["reader"],s["uid"]):s for s in r.read(HERE/"scores.json")}
    sessions, observed = set(), {}
    for e, rounds in p["orders"].items():
        last = freeze["frozen_utc"]
        for n,seq in enumerate(rounds,1):
            for uid in seq:
                job = r.ROOT/e/uid
                attempt = job/r.read(job/"accepted.json")["attempt"]
                rec = r.read(attempt/("meta" if e=="gpt" else "receipts")/(uid+".json"))
                session = rec["cli_session_id" if e=="gpt" else "session_id"]
                assert session not in sessions and rec["started_utc"] >= last
                sessions.add(session)
                last = rec["finished_utc" if e=="gpt" else "ended_utc"]
                key = p["slots"][uid]["item"]
                assert bank[uid] == p["items"][key]
                s = scores[e,uid]
                if s["status"] != "technical_missing":
                    form = r.read(attempt/"forms"/(uid+".json"))
                    assert form["status"] == s["status"] and form["events"] == s["events"]
                    for scale in r.SCALES:
                        vals = [ev[scale] for ev in form["events"]]
                        assert s[scale] == (mean(vals) if vals else None)
                observed[e,key,n] = s
    assert len(scores) == len(observed) == len(sessions) == receipt["unique_sessions"] == 16
    table = {e:{k:{scale:[observed[e,k,n][scale] for n in (1,2)] for scale in r.SCALES}
                for k in LABELS} for e in r.ENGINES}
    pairs = {e:{name:list(map(list,zip(table[e][a]["elaboration"],table[e][b]["elaboration"])))
                for name,(a,b) in CONTRASTS.items()} for e in r.ENGINES}
    result = {"scores":table, "paired_elaboration_before_after":pairs,
              "score_file_sha256":receipt["scores_sha256"], "prior_hashes":p["source_sha256"],
              "n_sessions":len(sessions), "statuses":dict(Counter(x["status"] for x in scores.values())),
              "events_per_reading":dict(Counter(len(x["events"]) for x in scores.values()))}
    r.save(HERE/"analysis.json",result)
    lines = ["# 네 가지 영어 답과 16회 최초 판독", "", p["items"]["original"]["question"], ""]
    for k,label in LABELS.items():
        ans = p["items"][k]["answer"]
        lines.extend([f"## {label} · {len(ans.split())}단어", "", ans, ""])
        for e in r.ENGINES:
            for n in (1,2):
                row = observed[e,k,n]
                lines.extend([f"### {e.upper()} {n}차", ""])
                for ev in row["events"]:
                    lines.extend([f"- 전개 {ev['elaboration']}점 · {ev['elaboration_reason']}",
                                  f"- 명료도 {ev['meaning_clarity']}점 · {ev['meaning_clarity_reason']}"])
                if not row["events"]:
                    lines.append(row["status"])
                lines.append("")
    output = "\n".join(lines)+"\n"
    path = HERE/"details.md"
    if path.exists():
        assert path.read_text() == output
    else:
        with path.open("x") as f:
            f.write(output)
    print(table, pairs)


if __name__ == "__main__":
    main()
