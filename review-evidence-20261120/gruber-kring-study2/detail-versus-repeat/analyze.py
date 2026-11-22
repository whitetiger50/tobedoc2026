"""Summarize the two blinded readings and show every paired text with the judges' reasons."""
from collections import Counter
from statistics import mean

import run as study

HERE, r = study.HERE, study.r
NAMES = {"detail":"세부 추가", "repeat":"반복"}
TOPICS = {"GK02":"두려움", "GK05":"아침 일과", "GK07":"당혹감", "GK12":"자부심"}


def main():
    cases, frozen = r.load_frozen()
    plan = r.read(study.PLAN)
    verified = r.read(HERE / "reader-verification.json")
    assert verified["scores_sha256"] == r.digest(HERE/"scores.json")
    assert verified["reader_freeze_sha256"] == r.digest(r.FROZEN)
    assert verified["blind_sha256"] == r.digest(r.BLIND)
    scores = {(x["reader"],x["uid"]):x for x in r.read(HERE/"scores.json")}
    assert len(scores)==32
    sessions, observed = set(), {}
    for e, rounds in plan["orders"].items():
        end = frozen["frozen_utc"]
        for n, order in enumerate(rounds,1):
            for pos,uid in enumerate(order,1):
                root = r.ROOT/e/uid
                attempt = root/r.read(root/"accepted.json")["attempt"]
                rec = r.read(attempt/("receipts" if e=="opus" else "meta")/(uid+".json"))
                assert rec["started_utc"] >= end
                end = rec["ended_utc" if e=="opus" else "finished_utc"]
                session = rec["session_id" if e=="opus" else "cli_session_id"]
                assert session not in sessions
                sessions.add(session)
                raw = r.read(attempt/"forms"/(uid+".json"))
                score = scores[e,uid]
                assert raw["events"]==score["events"] and raw["status"]==score["status"]
                for scale in r.SCALES:
                    values = [v[scale] for v in raw["events"]]
                    assert score[scale] == (mean(values) if values else None)
                assert plan["slots"][uid]["round"]==n
                key = (plan["slots"][uid]["item"],n,e)
                observed[key] = {"uid":uid,"position":pos,**score}
    assert len(sessions)==32
    by_case = {}
    lines = ["# 사례별 영어 문답과 눈가림 판독", "",
             "점수는 구체적 전개이며 Opus / GPT 순서다. 본문은 판독자들에게 전달된 영어 문장을 그대로 수록했다.", ""]
    for item in plan["items"]:
        cid, kind = item["case"], item["kind"]
        group = by_case.setdefault(cid,{})
        if not group:
            lines += [f"## {cid} · {TOPICS[cid]}", "", item["question"], ""]
        rounds = [[observed[item["id"],n,e] for e in r.ENGINES] for n in (1,2)]
        pair_scores = [[rec["elaboration"] for rec in row] for row in rounds]
        consensus = [None if None in pair else pair==[1,1] for pair in pair_scores]
        group[kind] = {"scores":pair_scores, "consensus_one":consensus,
                       "both":None if None in consensus else all(consensus)}
        lines += [f"### {NAMES[kind]} · {item['words']}단어", "", item["answer"], "",
                  f"삽입한 {item['added_words']}단어 · {item['insert']}", ""]
        for n, row in enumerate(rounds,1):
            for e,rec in zip(r.ENGINES,row):
                assert cases[rec["uid"]]["answer"] == item["answer"]
                reason = " ".join(ev["elaboration_reason"] for ev in rec["events"])
                lines.append(f"- {n}차 {e.upper()} · {rec['elaboration']} · {reason or rec['status']}")
        lines.append("")
    counts = {kind:sum(item[kind]["both"] is True for item in by_case.values()) for kind in NAMES}
    paired = Counter()
    for conditions in by_case.values():
        values = [conditions[k]["both"] for k in ("detail","repeat")]
        paired["incomplete" if None in values else ("both" if all(values) else
               "detail_only" if values[0] else "repeat_only" if values[1] else "neither")] += 1
    assert study.stimuli()[1]==plan["source_sha256"]
    result = {"by_case":by_case,"both_rounds_joint_one":counts, "paired_counts":dict(paired),
              "complete_readings":sum(s["status"]=="rated" for s in scores.values()),
              "unique_sessions":len(sessions),"source_sha256":plan["source_sha256"],
              "scores_sha256":verified["scores_sha256"],"orders_verified":True}
    r.save(HERE/"analysis.json",result)
    text = "\n".join(lines) + "\n"
    dest = HERE/"details.md"
    if dest.is_file():
        assert dest.read_text()==text
    else:
        with dest.open("x") as f:
            f.write(text)
    print(by_case, counts, dict(paired))


if __name__ == "__main__":
    main()
