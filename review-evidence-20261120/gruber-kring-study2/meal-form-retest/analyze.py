"""Summarize matched contrasts and exact retest agreement from sealed meal ratings."""
import hashlib
import itertools
import json
from collections import Counter
from pathlib import Path
from statistics import mean


HERE = Path(__file__).resolve().parent
READERS = ("opus", "gpt")
FOODS = ("soup", "tacos")
FORMS = ("compact", "dash", "split")
MEMORY = (False, True)
FACTOR_LABELS = {"food": "음식명", "sentence": "문장 분할", "memory": "기억 문구"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def locked_json(name, expected):
    blob = (HERE / name).read_bytes()
    require(hashlib.sha256(blob).hexdigest() == expected, name + " digest differs from verification.json")
    return json.loads(blob)


def preserve(path, data):
    if path.is_file():
        require(path.read_bytes() == data, path.name + " differs from existing output")
    else:
        with path.open("xb") as stream:
            stream.write(data)


def data_grid(plan, scores):
    items = plan["items"]
    by_cell = {(i["food"], i["form"], i["memory"]): i["id"] for i in items}
    ids = {i["id"] for i in items}
    require(len(items) == len(ids) == 12 and set(by_cell) == set(itertools.product(FOODS, FORMS, MEMORY)),
            "Missing or duplicate factorial cells")
    slots = plan["slots"]
    require(len(slots) == 24 and {(s["item"], s["round"]) for s in slots.values()} ==
            set(itertools.product(ids, (1, 2))), "Unexpected round/item assignment")
    require(len(scores) == 48 and {(s["uid"], s["reader"]) for s in scores} ==
            set(itertools.product(slots, READERS)), "Expected exactly 48 sealed reading records")
    by_uid = {(s["uid"], s["reader"]): s for s in scores}
    grid = {e: {key: [] for key in sorted(ids)} for e in READERS}
    for e in READERS:
        require(len(plan["schedule"][e]) == 2, "Expected two rounds")
        for r, order in enumerate(plan["schedule"][e], 1):
            require(len(order) == 12 and set(order) == {k for k, v in slots.items() if v["round"] == r},
                    "Invalid round schedule")
            for pos, uid in enumerate(order, 1):
                row = by_uid[uid, e]
                value = row["elaboration"]
                if row["status"] == "rated":
                    event_scores = [event["elaboration"] for event in row["events"]]
                    require(event_scores and all(type(v) is int and 1 <= v <= 3 for v in event_scores)
                            and value == mean(event_scores), "Elaboration score differs from individual events")
                else:
                    require(row["status"] in ("no_narrative", "technical_missing") and value is None,
                            "Unexpected or improperly scored missing status")
                grid[e][slots[uid]["item"]].append({"uid": uid, "position": pos, "status": row["status"], "score": value})
    return by_cell, grid


def direction(left, right):
    if left is None or right is None:
        return "missing"
    if right > left:
        return "up"
    if right < left:
        return "down"
    return "same"


def counts(labels, categories):
    observed = Counter(labels)
    return {"planned": len(labels), "valid": len(labels) - observed["missing"],
            **{k: observed[k] for k in (*categories, "missing")}}


def contrast_groups(by_cell):
    def cell(f, t, m):
        return by_cell[f, t, m]
    return {
        "food": [(cell("soup", t, m), cell("tacos", t, m)) for t in FORMS for m in MEMORY],
        "sentence": [(cell(f, "dash", m), cell(f, "split", m)) for f in FOODS for m in MEMORY],
        "memory": [(cell(f, t, False), cell(f, t, True)) for f in FOODS for t in FORMS],
    }


def contrasts(by_item, pairs):
    rows = []
    for left, right in pairs:
        rounds = []
        for r in range(2):
            a, b = by_item[left][r]["score"], by_item[right][r]["score"]
            rounds.append({"left_score": a, "right_score": b, "direction": direction(a, b)})
        label1, label2 = [v["direction"] for v in rounds]
        both = "missing" if "missing" in (label1, label2) else label1 if label1 == label2 else "mixed"
        rows.append({"left_item": left, "right_item": right, "rounds": rounds, "both": both})
    per_round = [counts([row["rounds"][r]["direction"] for row in rows], ("same", "up", "down"))
                 for r in range(2)]
    return {"rounds": per_round,
            "both_rounds": counts([row["both"] for row in rows], ("same", "up", "down", "mixed")),
            "rows": rows}


def analyze(plan, scores):
    by_cell, grid = data_grid(plan, scores)
    groups = contrast_groups(by_cell)
    readers = {}
    for e, by_item in grid.items():
        transitions = [direction(v[0]["score"], v[1]["score"]) for v in by_item.values()]
        readers[e] = {"test_retest": counts(transitions, ("same", "up", "down")),
                      "same_position": sum(v[0]["position"] == v[1]["position"] for v in by_item.values()),
                      "score_by_item_round": by_item,
                      "factors": {name: contrasts(by_item, pairs) for name, pairs in groups.items()}}
    between = []
    for r in range(2):
        compared = [direction(grid["opus"][i][r]["score"], grid["gpt"][i][r]["score"]) for i in by_cell.values()]
        between.append(counts(compared, ("same", "up", "down")))
    return {"readers": readers, "between_readers_opus_to_gpt": between}


def fmt(v):
    return "미채점" if v is None else str(v)


def table(headers, body):
    rows = [headers, ["---"] * len(headers), *body]
    return "\n".join("| " + " | ".join(map(str, row)) + " |" for row in rows)


def report(plan, result):
    lines = ["# 식사 표현별 두 회차의 구체적 전개 점수", "",
             "동일한 영어 문항별 1·2회 최초 점수와 실제 제시 위치를 표시한다. 전개 점수가 높을수록 전개가 부족하다고 읽은 것이다.", ""]
    grid = {e: result["readers"][e]["score_by_item_round"] for e in READERS}
    rows = []
    for item in plan["items"]:
        cells = []
        for e in READERS:
            ratings = grid[e][item["id"]]
            cells.extend([" → ".join(fmt(v["score"]) for v in ratings),
                          " → ".join(str(v["position"]) for v in ratings)])
        rows.append([item["id"], item["answer"], *cells])
    lines.append(table(["문항", "영어 답 전문", "Opus 점수", "Opus 순번", "GPT 점수", "GPT 순번"], rows))
    lines.extend(["", "## 일치도", ""])
    for e in READERS:
        c = result["readers"][e]["test_retest"]
        lines.append(f"- {e.upper()} 재판독 정확 일치 {c['same']}/{c['valid']}, 미채점 쌍 {c['missing']}/{c['planned']}.")
    for r, c in enumerate(result["between_readers_opus_to_gpt"], 1):
        lines.append(f"- {r}회차 모델 간 정확 일치 {c['same']}/{c['valid']}, 미채점 쌍 {c['missing']}/{c['planned']}.")
    lines.extend(["", "## 한 요소만 바꾼 비교", "",
                  "음식은 수프에서 타코, 문장 분할은 같은 단어의 대시 연결에서 두 문장, 기억 문구는 미포함에서 포함으로 바꾼 방향이다. "
                  "각 회차의 유지·상승·하락은 그 회차의 비교값이다. 두 회차 요약에서 혼합은 회차 간 방향이 달랐거나 한 회차에서만 변화한 경우다.", ""])
    body = []
    detail_rows = []
    for e in READERS:
        for factor, data in result["readers"][e]["factors"].items():
            label = FACTOR_LABELS[factor]
            r1, r2 = [f"{v['same']} / {v['up']} / {v['down']} · {v['valid']}/{v['planned']}" for v in data["rounds"]]
            b = data["both_rounds"]
            body.append([e.upper(), label, r1, r2, b["same"], b["up"], b["down"], b["mixed"], f"{b['valid']}/{b['planned']}"])
            for pair in data["rows"]:
                marks = [f"{fmt(v['left_score'])} → {fmt(v['right_score'])}" for v in pair["rounds"]]
                detail_rows.append([e.upper(), label, pair["left_item"], pair["right_item"], *marks])
    lines.append(table(["판독자", "요인", "1회 유지/상승/하락 · 유효/계획", "2회 유지/상승/하락 · 유효/계획",
                        "양회 유지", "양회 상승", "양회 하락", "혼합", "양회 유효/계획"], body))
    lines.extend(["", "## 개별 비교쌍", "", table(["판독자", "요인", "변경 전", "변경 후", "1회", "2회"], detail_rows)])
    return "\n".join(lines) + "\n"


def main():
    lock = json.loads((HERE / "verification.json").read_bytes())
    plan = locked_json("plan.json", lock["plan_sha256"])
    scores = locked_json("scores.json", lock["scores_sha256"])
    result = analyze(plan, scores)
    result["source_sha256"] = {k: lock[k] for k in ("plan_sha256", "scores_sha256")}
    preserve(HERE / "analysis.json", (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode())
    preserve(HERE / "details.md", report(plan, result).encode())


if __name__ == "__main__":
    main()
