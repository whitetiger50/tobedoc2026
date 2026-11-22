"""Report the fixed two-turn study from the three locked, blinded reader passes."""
import hashlib
import itertools
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DESIGN = HERE.parent / "dais-two-turn-design.json"
READERS = {"gpt": "GPT", "opus": "Opus"}
PHASES = ("first", "pair", "ground")
TYPES = {
    "direct": "이유 없는 자기 판단", "expanded": "선제 전개", "clarification": "되묻기",
    "other": "기타", "ambiguous": "불명확",
}
ADDITIONS = {
    "personal": "새 경험 근거", "general": "새 일반 설명", "repeat": "반복·미응답", "unclear": "불명확",
}
CONSISTENCY = {"consistent": "일관", "inconsistent": "불일치", "unclear": "불명확"}
SUPPORT = {
    "supported": "카드 근거 있음", "compatible_unverified": "양립하나 미확인",
    "contradicted": "카드와 모순", "unclear": "불명확", "not_applicable": "해당 없음",
}
SAFETY = {
    "clear": "문제 없음", "contradiction": "카드 모순", "major_unsupported_clinical": "근거 없는 중대한 임상 사실",
    "unclear": "불명확",
}
CHECKED_FIELDS = (
    ("first", "type", "첫 답 유형", TYPES),
    ("first", "also_requests_clarification", "되묻기 병존", {True: "있음", False: "없음"}),
    ("first", "alternatives", "첫 답의 대안 해석", None),
    ("pair", "addition", "후속 답의 추가 내용", ADDITIONS),
    ("pair", "consistency", "두 답의 일관성", CONSISTENCY),
    ("ground", "support", "경험의 카드 근거", SUPPORT),
    ("ground", "safety", "카드 모순·임상 추가", SAFETY),
)


def read(path):
    return json.loads(path.read_text())


def check(test, message):
    if not test:
        raise ValueError(message)


def checked_data():
    design = read(DESIGN)
    for arm, expected in design["design"]["prompt_sha256"].items():
        file = HERE.parent / design["design"]["unchanged_prompt_directory"] / (arm + ".txt")
        check(hashlib.sha256(file.read_bytes()).hexdigest() == expected, f"Prompt mismatch: {arm}")
    key = read(HERE / "private/key.json")
    profiles = design["synthetic_profiles"]
    cards = {card["id"]: card for card in profiles["cards"]}
    arms = design["design"]["arms"]
    sequences = design["interviewer_sequences"]
    cells = {(row["card"], row["sequence"], row["arm"]) for row in key}
    check(cells == set(itertools.product(cards, sequences, arms)) and len(key) == 12, "Incomplete study cells")
    ids = {row["id"] for row in key}
    check(len(ids) == 12 and ids == {p.stem for p in (HERE / "blind").glob("*.json")}, "Blind ID mismatch")
    locked = {phase: read(HERE / "ratings" / f"locked-{phase}.json") for phase in PHASES}
    for phase, by_reader in locked.items():
        check(set(by_reader) == READERS.keys() and all(set(records) == ids for records in by_reader.values()),
              f"Incomplete reader lock: {phase}")
    cases = []
    for k in sorted(key, key=lambda k: (k["card"], k["sequence"], arms.index(k["arm"]))):
        packet = read(HERE / "blind" / (k["id"] + ".json"))
        card = cards[k["card"]]
        expected_profile = dict(profiles["shared"], background=card["background"],
                                facts=[dict(profiles["fact_fields_shared_by_all_facts"], content=x) for x in card["facts"]])
        check(packet["profile"] == expected_profile, f"Profile changed: {k['id']}")
        turns = packet["dialogue"]
        check([turn["question"] for turn in turns] == sequences[k["sequence"]], f"Interview questions changed: {k['id']}")
        answers = [turn["answer"] for turn in turns]
        check(all(isinstance(a, str) and a.strip() for a in answers), f"Empty answer: {k['id']}")
        ratings = {model: {phase: locked[phase][model][k["id"]] for phase in PHASES} for model in READERS}
        for model, phases in ratings.items():
            for phase, field, _, labels in CHECKED_FIELDS:
                if phases[phase]["status"] != "valid":
                    continue
                value = phases[phase][field]
                check(value in labels if labels is not None else isinstance(value, list) and set(value) <= TYPES.keys(),
                      f"Unknown {field}: {model}/{k['id']}")
            first, pair, ground = (phases[p] for p in PHASES)
            if first["status"] == "valid":
                check(all(e["quote"] and e["quote"] in answers[0] for e in first["evidence"]), "First quote mismatch")
            if pair["status"] == "valid":
                for field, answer in zip(("quote1", "quote2"), answers):
                    check(isinstance(pair[field], str) and pair[field] in answer, "Pair quote mismatch")
            if ground["status"] == "valid" and ground.get("quote"):
                check(any(ground["quote"] in a for a in answers), "Grounding quote mismatch")
        cases.append({**k, "turns": turns, "ratings": ratings})
    return design, cases


def target(rating):
    first, pair, ground = (rating[p] for p in PHASES)
    if any(r["status"] != "valid" for r in (first, pair, ground)):
        return "판정 불충분"
    if first["type"] == "ambiguous":
        return "판정 불충분"
    if first["type"] != "direct" or pair["addition"] in ("general", "repeat"):
        return "미관찰"
    if pair["consistency"] == "inconsistent" or ground["safety"] in ("contradiction", "major_unsupported_clinical"):
        return "미관찰"
    if ground["support"] == "contradicted":
        return "미관찰"
    if (pair["addition"] == "personal" and pair["consistency"] == "consistent"
            and ground["support"] in ("supported", "compatible_unverified") and ground["safety"] == "clear"):
        return "관찰"
    return "판정 불충분"


def yes(rating):
    return target(rating) == "관찰"


def supported(rating):
    return yes(rating) and rating["ground"]["support"] == "supported"


def value(rating, phase, field):
    row = rating[phase]
    return row.get(field) if row["status"] == "valid" else None


def label(raw, labels):
    if raw is None:
        return "판독 결측"
    if isinstance(raw, list):
        return ", ".join(TYPES[k] for k in sorted(raw)) or "없음"
    return labels[raw]


def case_name(case):
    return f"{case['card']} · {case['sequence']} · {case['arm']}"


def differences(case):
    gpt, opus = (case["ratings"][model] for model in READERS)
    result = []
    for phase in PHASES:
        if gpt[phase]["status"] != opus[phase]["status"]:
            result.append((phase, "잠금 상태", gpt[phase]["status"], opus[phase]["status"]))
    for phase, field, title, labels in CHECKED_FIELDS:
        if any(r[phase]["status"] != "valid" for r in (gpt, opus)):
            continue
        a, b = (label(r[phase][field], labels) for r in (gpt, opus))
        if a != b:
            result.append((phase, title, a, b))
    return result


def lit(s):
    return "\n".join("> " + line if line else ">" for line in s.splitlines())


def report(design, cases):
    arms = design["design"]["arms"]
    output = ["# 두 턴 영어 모의 면담의 자기 판단과 후속 설명", ""]
    write = output.extend
    both = lambda c: all(yes(r) for r in c["ratings"].values())
    strong = lambda c: all(supported(r) for r in c["ratings"].values())
    overlaps = {arm: sum(both(c) for c in cases if c["arm"] == arm) for arm in arms}
    n_diff = sum(bool(differences(c)) for c in cases)
    n_final = sum(len({target(r) for r in c["ratings"].values()}) > 1 for c in cases)
    write(["두 판독자가 모두 첫 답에서는 이유 없이 자기 판단을 밝혔고 그 이유를 묻자 새로운 개인 경험이 나왔다고 판정한 면담은 "
           + ", ".join(f"**{a} {overlaps[a]}/4건**" for a in arms) + "이었다.",
           "", "B는 기존 영어 페르소나, T2는 팀이 개발한 영어 발화기, BC는 B에 조건부 되묻기 규칙을 추가한 후보다. "
           "모두 같은 가상 카드 2장과 DAIS-C 질문 순서 2개를 받았다. 각 조합을 한 번씩 생성했다.",
           "", "## 조건별 건수", "",
           "| 조건 | GPT 관찰 | Opus 관찰 | 두 판독자 모두 관찰 | 그중 두 판독자 모두 카드 근거 확인 |",
           "|---|---:|---:|---:|---:|"])
    for arm in arms:
        group = [c for c in cases if c["arm"] == arm]
        gpt, opus = (sum(yes(c["ratings"][m]) for c in group) for m in READERS)
        write([f"| {arm} | {gpt}/4 | {opus}/4 | {overlaps[arm]}/4 | {sum(strong(c) for c in group)}/4 |"])
    write(["", "확인 사례에는 두 답이 일관되고 카드와 모순되거나 근거 없는 중대한 임상 사실이 추가되지 않은 경우만 포함했다. "
           "가상 카드와 양립하지만 확인할 수 없는 경험도 사전 설계대로 관찰 수에 포함했다. 마지막 열은 같은 분모에서 카드가 실제로 뒷받침한 경우만 센 수다.",
           "", "| 조건 | 판독자 | 첫 답에서 전개 | 이유 없는 자기 판단(direct) | direct 중 되묻기도 함 | direct 중 둘째 답에서 새 경험 | 첫 답 되묻기만·기타 | 첫 답 불명확·결측 |",
           "|---|---|---:|---:|---:|---:|---:|---:|"])
    for arm in arms:
        for m, name in READERS.items():
            rows = [c["ratings"][m] for c in cases if c["arm"] == arm]
            types = Counter(value(r, "first", "type") for r in rows)
            direct = types["direct"]
            mixed = sum(value(r, "first", "type") == "direct" and value(r, "first", "also_requests_clarification") is True for r in rows)
            personal = sum(value(r, "first", "type") == "direct" and value(r, "pair", "addition") == "personal" for r in rows)
            cond = f"{personal}/{direct}" if direct else "평가 기회 없음"
            write([f"| {arm} | {name} | {types['expanded']}/4 | {direct}/4 | {mixed} | {cond} | "
                   f"{types['clarification'] + types['other']}/4 | {types['ambiguous'] + types[None]}/4 |"])
    write(["", "첫 답이 되묻기만 했거나 입장을 밝히지 않으면 고정된 이유 질문이 받아 줄 자기 판단이 없다. "
           "첫 답에 판단과 설명이 함께 있고 마지막에 되묻는 경우는 기존 우선순위에 따라 전개로 기록한다.",
           "", "기존 코딩의 direct는 자기 판단의 이유나 예시를 아직 말하지 않았다는 뜻이다. 질문의 범위를 되묻는 행동은 동시에 기록할 수 있다. "
           "두 판독자 모두 목표 흐름으로 확인하고 첫 답에 되묻기도 없다고 한 면담을 별도로 세면 "
           + ", ".join(f"{arm} {sum(both(c) and all(value(r, 'first', 'also_requests_clarification') is False for r in c['ratings'].values()) for c in cases if c['arm']==arm)}/4건" for arm in arms)
           + "이었다. 이 수치는 사전 주결과를 해석하기 위한 보충 집계다.",
           "", "## 카드와 질문 순서별 판독", "",
           "| 카드 · 순서 · 조건 | GPT 첫 답 / 둘째 답 | Opus 첫 답 / 둘째 답 | 목표 흐름 GPT / Opus |",
           "|---|---|---|---|"])
    for c in cases:
        reading = c["ratings"]
        pair = [label(value(r, "first", "type"), TYPES) + " / " + label(value(r, "pair", "addition"), ADDITIONS)
                for r in reading.values()]
        decisions = " / ".join(target(r) for r in reading.values())
        write([f"| {case_name(c)} | {pair[0]} | {pair[1]} | {decisions} |"])
    write(["", "## 판독이 갈린 면담", "",
           f"첫 답 유형·되묻기 병존·대안 해석, 둘째 답의 새 내용·일관성, 카드 근거·모순 여부를 대조하면 {n_diff}/12건에서 범주 판정이 달랐다. "
           f"목표 흐름의 최종 판정이 달라진 면담은 {n_final}/12건이었다. 같은 범주에서 고른 인용 구절이나 근거 문장만 다른 경우는 세지 않았다.", ""])
    for c in cases:
        diff = differences(c)
        if not diff:
            continue
        write([f"### {case_name(c)}", ""])
        for phase, title, gpt, opus in diff:
            write([f"- {title}에 대한 판정은 GPT **{gpt}**, Opus **{opus}**였다."])
        write(["", "두 판독자의 최종 판정은 " + ", ".join(f"{READERS[m]} **{target(r)}**" for m, r in c["ratings"].items()) + "이다."])
        for phase in dict.fromkeys(row[0] for row in diff):
            for m, name in READERS.items():
                r = c["ratings"][m][phase]
                if r.get("reason"):
                    write(["", f"{name} 판독 근거", "", lit(r["reason"])])
        write([""])
    write(["## 전체 영어 문답", "", "아래는 12개 모의 면담의 전체 연구용 질문과 생성 답이다. 질문의 반복과 머뭇거림도 그대로 실었다.", ""])
    for c in cases:
        write([f"### {case_name(c)}", ""])
        for i, t in enumerate(c["turns"], 1):
            write([f"**면담자 {i}**", "", lit(t["question"]), "", f"**발화기 {i}**", "", lit(t["answer"]), ""])
        write(["| 판독자 | 첫 답 | 둘째 답 | 일관성 | 카드 근거 | 모순·임상 추가 | 목표 흐름 |",
               "|---|---|---|---|---|---|---|"])
        for m, r in c["ratings"].items():
            fields = [label(value(r, phase, fld), loc) for phase, fld, loc in
                      (("first", "type", TYPES), ("pair", "addition", ADDITIONS), ("pair", "consistency", CONSISTENCY),
                       ("ground", "support", SUPPORT), ("ground", "safety", SAFETY))]
            write(["| " + " | ".join([READERS[m], *fields, target(r)]) + " |"])
        write([""])
    write(["## 해석 범위", ""])
    for arm in arms:
        group = [c for c in cases if c["arm"] == arm]
        positive = [c for c in group if both(c)]
        if positive:
            cross = any(a["card"] != b["card"] and a["sequence"] != b["sequence"] for a, b in itertools.combinations(positive, 2))
            text = "카드와 질문 순서가 모두 달라진 두 조합에서도 관찰됐다." if cross else "다른 카드와 다른 질문 순서에서도 반복됐다고 말할 만큼의 짝은 없었다."
            write([f"- **{arm}**에서 목표 흐름이 관찰됐다. {text}"])
        else:
            early = sum(all(value(r, "first", "type") == "expanded" for r in c["ratings"].values()) for c in group)
            text = ("네 조합 모두 두 판독자가 첫 답에서 선제 전개를 확인했다. 이 설계에서 반복된 점검 신호다."
                    if early == 4 else f"두 판독자가 모두 첫 답의 선제 전개를 확인한 면담은 {early}/4건이었다.")
            write([f"- **{arm}**에서는 두 판독자가 공통으로 확인한 목표 흐름이 없었다. {text}"])
    write(["", "실제 환자 두 명은 이 대화 흐름이 보였기 때문에 선택됐다. 질문 순서 역시 같은 언어 창의성 질문의 두 표현이다. "
           "각 카드·질문·조건을 한 번씩 관찰했으므로 결과에서 모집단 빈도, 임상적 재현성이나 발화기 간 우열을 추정할 수 없다.",
           "", "[사전 설계](../dais-two-turn-design.json) · [첫 답 판독](ratings/locked-first.json) · [두 문답 판독](ratings/locked-pair.json) · "
           "[카드 근거 판독](ratings/locked-ground.json) · [DAIS-C 원자료, Delgaram-Nejad 외](https://reshare.ukdataservice.ac.uk/855021/) · "
           "[원전 이용 조건](https://creativecommons.org/licenses/by-sa/4.0/)", ""])
    return "\n".join(output), {"confirmed": overlaps, "disagreements": n_diff, "final_disagreements": n_final}


if __name__ == "__main__":
    design, cases = checked_data()
    markdown, stats = report(design, cases)
    destination = HERE / "RESULTS.ko.md"
    if not destination.is_file() or destination.read_text() != markdown:
        pending = destination.with_suffix(".tmp")
        pending.write_text(markdown)
        pending.replace(destination)
    print(json.dumps(stats, ensure_ascii=False))
