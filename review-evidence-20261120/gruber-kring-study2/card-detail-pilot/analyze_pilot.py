"""Analyze the 36 matched pairs only after both blinded readers' results are locked."""
import hashlib
import itertools
import json
import os
import re
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path
from statistics import mean, median

HERE = Path(__file__).resolve().parent
ARMS = ("developed", "base", "short")
LABEL = {"all": "전체", "developed": "개발판", "base": "기본 모델", "short": "단답 대조"}
VERSIONS = ("full", "core")
READERS = ("opus", "gpt")
SCALES = ("elaboration", "meaning_clarity")
STATES = ("one", "above_one", "no_narrative", "technical_missing")
STATE_LABEL = ("1점", "1점 초과", "서사 미제공", "기술 결측")
PLAN_SHA = "6842bc038634f681ab5db7aeb3fb1625c45407bfa1123991b635a7b96b5e6cde"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    return json.loads(path.read_bytes())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_locked_inputs(root):
    scores_file = root / "scores.json"
    blind_file = root / "blind.json"
    lock_file = root / "reader-verification.json"
    freeze_file = root / "freeze.json"
    plan_file = root / "plan.json"
    lock = load(lock_file)
    require(lock["scores_sha256"] == digest(scores_file), "Blinded scores differ from their lock.")
    require(lock["blind_sha256"] == digest(blind_file), "Blinded corpus differs from its lock.")
    require(digest(plan_file) == PLAN_SHA, "The prespecified 36-pair plan has changed.")
    scores = load(scores_file)
    blind = load(blind_file)
    uids = {r["uid"] for r in blind}
    require(len(uids) == len(blind) == 72, "Need all 72 planned output records.")
    require(len(scores) == 144 and {(r["uid"], r["reader"]) for r in scores}
            == set(itertools.product(uids, READERS)), "Both readers must have all 72 records.")
    # No schedule access before checking both readers' score and corpus commitments.
    key_file = root / "private/schedule.json"
    require(load(freeze_file)["schedule_sha256"] == digest(key_file), "Allocation key changed.")
    paths = [scores_file, blind_file, lock_file, freeze_file, plan_file, key_file]
    sources = {str(p.relative_to(root)): digest(p) for p in paths}
    return load(plan_file), load(key_file), blind, scores, sources


def word_count(text):
    folded = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    return len(re.findall(r"[A-Za-z]+(?:['’][A-Za-z]+)*", folded))


def state(score, scale="elaboration"):
    if score["status"] != "rated":
        return score["status"]
    return "one" if score[scale] == 1 else "above_one"


def describe(values):
    return {"n": len(values), "mean": mean(values) if values else None,
            "median": median(values) if values else None, "min": min(values, default=None),
            "max": max(values, default=None)}


def distribution(values):
    counts = Counter(values)
    return {str(v): counts[v] for v in sorted(counts)}


def check_score(row):
    require(row["status"] in ("rated", *STATES[2:]), "Invalid response status.")
    rated = row["status"] == "rated"
    require(isinstance(row["events"], list) and bool(row["events"]) == rated, "Invalid event list.")
    for scale in SCALES:
        values = [event[scale] for event in row["events"]]
        require(all(type(v) is int and v in (1, 2, 3) for v in values), "Invalid event score.")
        require(row[scale] == (mean(values) if rated else None), "Question score disagrees with events.")


def exact_signflip(card_contrasts):
    observed = sum(card_contrasts)
    extreme = sum(sum(sign * v for sign, v in zip(signs, card_contrasts)) >= observed
                  for signs in itertools.product((-1, 1), repeat=len(card_contrasts)))
    allocations = 2 ** len(card_contrasts)
    return {"count_ge": extreme, "allocations": allocations, "one_sided_p": extreme / allocations}


def pair_shift(full, core):
    if full == "one" and core == "above_one":
        return 1
    if full == "above_one" and core == "one":
        return -1
    return 0


def summarize_pairs(pairs, reader):
    b = c = complete = 0
    table = {s: dict.fromkeys(STATES, 0) for s in STATES}
    observed = Counter()
    worst = Counter()
    worst_arms = Counter()
    marginal = {}
    for pair in pairs:
        a, z = [state(pair[v]["scores"][reader]) for v in VERSIONS]
        table[a][z] += 1
        complete += a in STATES[:2] and z in STATES[:2]
        shift = pair_shift(a, z)
        b += shift == 1
        c += shift == -1
        observed[pair["case"]] += shift
        shift_worst = pair_shift(a if a in STATES[:2] else "above_one", z if z in STATES[:2] else "one")
        worst[pair["case"]] += shift_worst
        worst_arms[pair["arm"]] += shift_worst
    for v in VERSIONS:
        scores = [pair[v]["scores"][reader] for pair in pairs]
        rated = [score for score in scores if score["status"] == "rated"]
        counts = Counter(state(score) for score in scores)
        marginal[v] = {
            "elaboration_states": {s: counts[s] for s in STATES},
            "one_fraction_planned": counts["one"] / len(pairs),
            "one_fraction_rated": counts["one"] / len(rated) if rated else None,
            "events_per_rated_answer": distribution([len(score["events"]) for score in rated]),
            "question_score_distribution": {
                scale: distribution([score[scale] for score in rated]) for scale in SCALES},
            "question_score_mean": {
                scale: mean(score[scale] for score in rated) if rated else None for scale in SCALES},
            "event_score_distribution": {
                scale: distribution([event[scale] for score in rated for event in score["events"]])
                for scale in SCALES}}
    return {"planned": len(pairs), "complete": complete, "marginal": marginal,
            "full_rows_core_columns": table, "b": b, "c": c, "signed": b-c,
            "delta": (b-c)/len(pairs), "complete_delta": (b-c)/complete if complete else None,
            "card_net": dict(sorted(observed.items())),
            "worst_missing": {"net": sum(worst.values()), "delta": sum(worst.values())/len(pairs),
                              "arm_net": dict(worst_arms), "card_net": dict(sorted(worst.items()))}}


def reader_summary(pairs, reader):
    groups = {"all": summarize_pairs(pairs, reader)}
    groups.update({a: summarize_pairs([p for p in pairs if p["arm"] == a], reader) for a in ARMS})
    whole = groups["all"]
    worst = whole["worst_missing"]
    whole["randomization"] = exact_signflip(list(whole["card_net"].values()))
    worst["randomization"] = exact_signflip(list(worst["card_net"].values()))
    without = summarize_pairs([p for p in pairs if p["case"] != "GK04"], reader)
    return {"groups": groups, "without_GK04": {k: without[k] for k in ("planned","complete","b","c","signed","delta")}}


def classify(readers):
    common = set(ARMS)
    common_worst = set(ARMS)
    by_reader = {}
    for reader, result in readers.items():
        groups = result["groups"]
        all_pairs = groups["all"]
        worst = all_pairs["worst_missing"]
        full_one, core_one = [all_pairs["marginal"][v]["elaboration_states"]["one"] for v in VERSIONS]
        common.intersection_update(a for a in ARMS if groups[a]["signed"] > 0)
        common_worst.intersection_update(a for a in ARMS if worst["arm_net"][a] > 0)
        by_reader[reader] = {"full_at_least_33": full_one >= 33, "core_at_least_33": core_one >= 33,
                             "net_at_least_9": all_pairs["signed"] >= 9,
                             "p_at_most_005": all_pairs["randomization"]["one_sided_p"] <= 0.05,
                             "worst_net_at_least_9": worst["net"] >= 9,
                             "worst_p_at_most_005": worst["randomization"]["one_sided_p"] <= 0.05}
    effect_gates = ("full_at_least_33", "net_at_least_9", "p_at_most_005",
                    "worst_net_at_least_9", "worst_p_at_most_005")
    return {"by_reader": by_reader, "common_positive_arms": sorted(common),
            "worst_common_positive_arms": sorted(common_worst),
            "card_contribution": len(common) >= 2 and len(common_worst) >= 2 and
            all(all(vals[k] for k in effect_gates) for vals in by_reader.values()),
            "full_concentration_reproduced": all(v["full_at_least_33"] for v in by_reader.values()),
            "concentration_persists": all(v["full_at_least_33"] and v["core_at_least_33"] for v in by_reader.values())}


def agreement(outputs):
    comparisons = [tuple(row["scores"][r] for r in READERS) for row in outputs]
    rated = [(x, y) for x, y in comparisons if x["status"] == y["status"] == "rated"]
    return {"total":len(comparisons),"both_rated":len(rated),
            "status_same":sum(x["status"] == y["status"] for x,y in comparisons),
            "floor_state_same":sum(state(x) == state(y) for x,y in comparisons),
            "event_count_same_among_rated":sum(len(x["events"]) == len(y["events"]) for x,y in rated),
            "question_score_same_among_rated":{s: sum(x[s] == y[s] for x,y in rated) for s in SCALES}}


def analyze(plan, schedule, blind, scores):
    desired = {(i["case"], i["topic"], a, v) for i in plan["items"] for a in ARMS for v in VERSIONS}
    assigned = {(i["case"], i["topic"], i["arm"], i["version"]) for i in schedule}
    require(assigned == desired and len(assigned) == len(schedule) == 72, "Schedule differs from selected cells.")
    require(len({x["job"] for x in schedule}) == 72, "Duplicate generation job.")
    uids = {r["uid"] for r in schedule}
    require(len(uids) == len(blind) == 72 and uids == {r["uid"] for r in blind}, "Unmatched blind IDs.")
    require(len(scores) == 144 and {(r["uid"], r["reader"]) for r in scores}
            == set(itertools.product(uids, READERS)), "Unmatched reader scores.")
    for r in scores:
        check_score(r)
    ratings = {(r["uid"],r["reader"]): r for r in scores}
    words = {r["uid"]: word_count(r["answer"]) for r in blind}
    groups = {}
    for job in schedule:
        case, topic, arm, version, uid = [job[k] for k in ("case", "topic", "arm", "version", "uid")]
        pair = groups.setdefault((case, topic, arm), {"case": case, "topic": topic, "arm": arm})
        pair[version] = {"uid": uid, "words": words[uid], "scores": {r: ratings[uid, r] for r in READERS}}
    pairs = [groups[k] for k in sorted(groups)]
    readers = {e: reader_summary(pairs, e) for e in READERS}
    lengths = {}
    agreements = {}
    for arm in ("all", *ARMS):
        selected = [p for p in pairs if arm == "all" or p["arm"] == arm]
        lengths[arm] = {v: describe([p[v]["words"] for p in selected]) for v in VERSIONS}
        lengths[arm]["paired_core_minus_full"] = describe([p["core"]["words"]-p["full"]["words"] for p in selected])
        agreements[arm] = {v: agreement([p[v] for p in selected]) for v in VERSIONS}
        agreements[arm]["both_versions"] = agreement([p[v] for p in selected for v in VERSIONS])
    return {"decision":classify(readers), "readers":readers, "words":lengths, "agreement":agreements, "pairs":pairs}


def table(headings, rows):
    return ["| " + " | ".join(map(str,row)) + " |" for row in [headings, ["---"]*len(headings), *rows]]


def percent(fraction):
    return f"{100*fraction:.1f}"


def freq(counts):
    return ", ".join(f"{v}점 {n}건" for v,n in counts.items()) or "—"


def tables(result):
    lines = ["# 카드 세부 제공 대조 실험 수치표", "", "## 구체적 전개", "",
             "카드별 상태는 전개 1점 / 1점 초과 / 서사 미제공 / 기술 결측 순서다. Δ는 중심 사실 카드로 바꿨을 때 계획된 쌍 수 대비 1점 초과 순증가 폭이다.", ""]
    rows = []
    for reader, data in result["readers"].items():
        for arm,g in data["groups"].items():
            states = [" / ".join(str(g["marginal"][v]["elaboration_states"][s]) for s in STATES) for v in VERSIONS]
            rows.append([reader.upper(), LABEL[arm], *states, f"{g['complete']}/{g['planned']}",
                         g["b"],g["c"], percent(g["delta"])])
    lines += table(["판독자","조건","원래 카드","중심 사실 카드","완전쌍","1→초과","초과→1","Δ (%p)"], rows)
    lines += ["", "## 사전 판정과 길 안내 제외 결과", ""]
    rows = []
    for r,data in result["readers"].items():
        g = data["groups"]["all"]
        rand = g["randomization"]
        worst = g["worst_missing"]
        without = data["without_GK04"]
        rows.append([r.upper(), g["signed"], f"{rand['count_ge']}/{rand['allocations']}",
                     f"{rand['one_sided_p']:.6f}", worst["net"], f"{worst['randomization']['one_sided_p']:.6f}",
                     f"{without['signed']}/{without['planned']} ({percent(without['delta'])}%p)"])
    lines += table(["판독자","순전환","단측 꼬리 배정 수/전체","정확 p","결측 최악 순전환","결측 최악 p","GK04 제외 순전환"],rows)
    dec = result["decision"]
    def yesno(value):
        return "충족" if value else "미충족"
    lines += ["", f"- 원래 카드의 1점 집중 재현 {yesno(dec['full_concentration_reproduced'])}",
              f"- 두 버전 모두에서 1점 집중 유지 {yesno(dec['concentration_persists'])}",
              f"- 사전 카드 기여 기준 {yesno(dec['card_contribution'])}",
              "- 양 판독자 공통 양의 방향 조건 " + (", ".join(LABEL[a] for a in dec['common_positive_arms']) or "없음"),
              "- 미채점 최악 배정에서도 공통 양의 방향인 조건 " +
              (", ".join(LABEL[a] for a in dec['worst_common_positive_arms']) or "없음"),
              "", "## 전개 상태 교차표", "",
              "행은 원래 카드이고 열은 중심 사실 카드다. 전체 교차표를 제시하며 생성 조건별 교차표는 analysis.json에 보존한다.", ""]
    rows=[]
    for r,data in result["readers"].items():
        cross = data["groups"]["all"]["full_rows_core_columns"]
        rows.extend([r.upper(),label,*[cross[s][t] for t in STATES]] for s,label in zip(STATES,STATE_LABEL))
    lines += table(["판독자", "원래 카드", *STATE_LABEL],rows)
    lines += ["", "## 사건을 평균한 질문 점수와 사건 수", "",
              "사건 수는 채점된 답에서의 사건 개수별 답변 수다. 두 척도 모두 사건 점수를 먼저 질문 안에서 평균했다.", ""]
    rows=[]
    for r,data in result["readers"].items():
        for a,g in data["groups"].items():
            for v,label in zip(VERSIONS,("원래","중심")):
                m = g["marginal"][v]
                d = m["question_score_distribution"]
                events = ", ".join(f"{k}개 {n}건" for k,n in m["events_per_rated_answer"].items()) or "—"
                rows.append([r.upper(),LABEL[a],label,freq(d["elaboration"]),freq(d["meaning_clarity"]),events])
    lines += table(["판독자","조건","카드","전개 점수 분포","명료도 점수 분포","사건 수 분포"],rows)
    lines += ["","## 단어 수와 판독 일치", "",
              "단어 수는 중앙값이다. 짝 내 변화는 각 쌍에서 중심 사실 카드 길이에서 원래 카드 길이를 뺀 후 중앙값을 구했다.", ""]
    rows=[]
    for a,g in result["words"].items():
        agree = result["agreement"][a]["both_versions"]
        rows.append([LABEL[a],g["full"]["median"],g["core"]["median"],g["paired_core_minus_full"]["median"],
                     f"{agree['floor_state_same']}/{agree['total']}",
                     *[f"{agree['question_score_same_among_rated'][s]}/{agree['both_rated']}" for s in SCALES],
                     f"{agree['event_count_same_among_rated']}/{agree['both_rated']}"])
    lines += table(["조건","원래","중심","짝 내 변화","전개 상태 일치","전개 점수 일치","명료도 점수 일치","사건 수 일치"],rows)
    return "\n".join(lines) + "\n"


def store(path, data):
    if path.is_file():
        require(path.read_bytes() == data, f"Existing output differs: {path.name}")
        return
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", delete=False) as stream:
        stream.write(data)
        name = stream.name
    os.replace(name, path)


def main():
    plan, schedule, blind, scores, sources = load_locked_inputs(HERE)
    result = analyze(plan, schedule, blind, scores)
    result["sources_sha256"] = sources
    store(HERE/"analysis.json", (json.dumps(result, ensure_ascii=False, indent=2)+"\n").encode())
    store(HERE/"tables.md", tables(result).encode())
    print(json.dumps(result["decision"], ensure_ascii=False))


if __name__ == "__main__":
    main()
