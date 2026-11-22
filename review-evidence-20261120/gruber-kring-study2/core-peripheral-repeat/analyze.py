"""Audit sessions and first scores; apply the frozen case-level classification."""
from collections import Counter
from statistics import mean

import run as study

HERE, r = study.HERE, study.r
KINDS = ("detail", "peripheral", "repeat")
LABELS = dict(zip(KINDS, ("핵심 세부", "주변 세부", "반복")))


def observed_readings():
    cases, frozen = r.load_frozen()
    plan = r.read(study.PLAN)
    verify = r.read(HERE / "reader-verification.json")
    assert verify["scores_sha256"] == r.digest(HERE / "scores.json")
    assert verify["reader_freeze_sha256"] == r.digest(r.FROZEN)
    assert verify["blind_sha256"] == r.digest(r.BLIND)
    scores = {(row["reader"],row["uid"]):row for row in r.read(HERE / "scores.json")}
    sessions, observed = set(), {}
    for engine, rounds in plan["orders"].items():
        last = frozen["frozen_utc"]
        for n, order in enumerate(rounds,1):
            for uid in order:
                job = r.ROOT / engine / uid
                attempt = job / r.read(job / "accepted.json")["attempt"]
                kind = "receipts" if engine == "opus" else "meta"
                rec = r.read(attempt / kind / (uid + ".json"))
                assert rec["started_utc"] >= last
                last = rec["ended_utc" if engine == "opus" else "finished_utc"]
                session = rec["session_id" if engine == "opus" else "cli_session_id"]
                assert session not in sessions
                sessions.add(session)
                slot = plan["slots"][uid]
                assert slot["round"] == n
                row = scores[engine,uid]
                if row["status"] != "technical_missing":
                    form = r.read(attempt / "forms" / (uid + ".json"))
                    assert form["events"] == row["events"] and form["status"] == row["status"]
                    for scale in r.SCALES:
                        marks = [ev[scale] for ev in form["events"]]
                        assert row[scale] == (mean(marks) if marks else None)
                observed[slot["item"],engine,n] = row
    assert len(scores) == len(sessions) == len(observed) == 48
    return cases, plan, observed


def classify(case):
    d, p, rep = [case[k] for k in KINDS]
    if any(None in pair for pair in (d,p,rep)):
        return "missing"
    if all(pair == [1,1] for pair in (d,p,rep)):
        return "all_one"
    if d != [1,1] or min(rep) <= 1:
        return "control_contrast_absent_or_unstable"
    if p == [1,1]:
        return "peripheral_also_sufficient"
    if min(p) > 1:
        return "core_only"
    return "peripheral_unstable"


def main():
    cases, plan, observed = observed_readings()
    per_engine = {e:{} for e in r.ENGINES}
    lines = ["# 영어 문답 12개와 눈가림 판독 근거", "",
             "각 점수는 구체적 전개를 뜻한다. 여러 사건으로 채점한 응답은 사건별 점수와 근거도 표기했다.", ""]
    for item in plan["items"]:
        cid, kind = item["case"], item["kind"]
        if kind == "detail":
            lines.extend([f"## {cid}", "", item["question"], ""])
        lines.extend([f"### {LABELS[kind]} · {item['words']}단어", "", item["answer"], "",
                      f"삽입한 {item['added_words']}단어 · {item['insert']}", ""])
        for e in r.ENGINES:
            ratings = []
            for n in (1,2):
                row = observed[item["id"],e,n]
                assert cases[row["uid"]]["answer"] == item["answer"]
                ratings.append(row["elaboration"])
                reasons = " / ".join(f"({ev['elaboration']}) {ev['elaboration_reason']}" for ev in row["events"])
                lines.append(f"- {e.upper()} {n}차 · {row['elaboration']} · {reasons or row['status']}")
            per_engine[e].setdefault(cid,{})[kind] = ratings
        lines.append("")
    by_engine, joint = {}, {}
    for engine, caseset in per_engine.items():
        by_engine[engine] = {
            "cases":caseset, "classification":{cid:classify(case) for cid,case in caseset.items()},
            "both_rounds_one":{k:sum(case[k]==[1,1] for case in caseset.values()) for k in KINDS},
            "identical_across_rounds":sum(None not in pair and pair[0]==pair[1]
                                         for case in caseset.values() for pair in case.values())}
    for k in KINDS:
        joint[k] = sum(all(per_engine[e][cid][k]==[1,1] for e in r.ENGINES) for cid in study.PERIPHERAL)
    result = {"readers":by_engine, "joint_both_rounds_one":joint,
              "n_sessions":len(observed), "status_counts":dict(Counter(v["status"] for v in observed.values())),
              "event_counts":dict(Counter(len(v["events"]) for v in observed.values())),
              "clarity_counts":dict(Counter(v["meaning_clarity"] for v in observed.values())),
              "source_sha256":plan["source_sha256"], "scores_sha256":r.digest(HERE/"scores.json")}
    r.save(HERE / "analysis.json",result)
    dest = HERE / "details.md"
    output = "\n".join(lines) + "\n"
    if dest.exists():
        assert dest.read_text() == output
    else:
        with dest.open("x") as f:
            f.write(output)
    print(by_engine, joint, result["status_counts"], result["event_counts"])


if __name__ == "__main__":
    main()
