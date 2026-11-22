"""Frozen DAIS-C first-reply distribution analysis from masked rating labels only."""

import argparse
import json
import os
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction as F
from functools import lru_cache
from itertools import combinations, product
from pathlib import Path
from tempfile import NamedTemporaryFile

HERE = Path(__file__).resolve().parent
TYPES = ("expanded", "direct", "clarification", "other")
MODELS = ("developed", "base", "short")
ARMS = ("patient", *MODELS)
QUESTIONS = ("Q2", "Q3")
READERS = ("opus", "gpt")
FEATURES = ("DERAILMENT", "POVERTY_OF_CONTENT", "TANGENTIALITY", "UNCLEAR_REFERENCE")
STATUSES = ("present", "absent", "uncertain", "not_assessable", "technical_missing")
BINS = ("<10", "10–29", "≥30")


@dataclass(frozen=True)
class Interval:
    low: F
    high: F

    def __add__(self, other):
        return Interval(self.low + other.low, self.high + other.high)

    def __mul__(self, weight):
        assert weight >= 0
        return Interval(self.low * weight, self.high * weight)


ZERO = Interval(F(0), F(0))


def interval_json(value):
    if isinstance(value, Interval):
        return {"lo": float(value.low), "hi": float(value.high),
                "exact": [str(value.low), str(value.high)]}
    raise TypeError(type(value).__name__)


def mask_of(rating):
    label = rating["type"]
    if label == "technical_missing":
        return 15
    if label in TYPES:
        return 1 << TYPES.index(label)
    if label != "ambiguous":
        raise ValueError("Invalid type label")
    choices = rating["alternatives"]
    if not isinstance(choices, list) or len(set(choices)) < 2 or not set(choices) <= set(TYPES):
        raise ValueError("Ambiguous type requires at least two distinct candidate types")
    return sum(1 << TYPES.index(label) for label in set(choices))


@dataclass(frozen=True)
class Rated:
    person: str
    question: str
    arm: str
    words: int | None
    label: str
    mask: int
    clinical: tuple


def validate(records):
    if not isinstance(records, list) or len(records) != 140:
        raise ValueError("Expected all 140 planned records, including technical missingness")
    if len({r["uid"] for r in records}) != len(records):
        raise ValueError("Duplicate uid")
    slots = set()
    people = {q: set() for q in QUESTIONS}
    for r in records:
        q, p, a, rep, w = (r[k] for k in ("question", "person", "arm", "rep", "words"))
        if q not in QUESTIONS or not isinstance(p, str) or not p or a not in ARMS:
            raise ValueError("Unexpected question, person or arm")
        if type(rep) is not int or rep not in ((0,) if a == "patient" else (1, 2, 3)):
            raise ValueError("Invalid replication index")
        if w is not None and (type(w) is not int or w < 0):
            raise ValueError("Word count must be a nonnegative integer or null")
        if (p, q, a, rep) in slots:
            raise ValueError("Duplicate input-arm-replication slot")
        slots.add((p, q, a, rep))
        people[q].add(p)
        for reader in READERS:
            entry = r["readers"][reader]
            mask_of(entry["type"])
            if any(entry["clinical"][k] not in STATUSES for k in FEATURES):
                raise ValueError("Invalid clinical label")
    if any(len(ps) != 7 for ps in people.values()) or people["Q2"] & people["Q3"]:
        raise ValueError("Expected 14 distinct people, seven per question")
    expected = {(p, q, a, rep) for q, ps in people.items() for p in ps
                for a in ARMS for rep in ((0,) if a == "patient" else (1, 2, 3))}
    if slots != expected:
        raise ValueError("Planned response slots differ from submitted response slots")


def select_reader(records, key):
    out = []
    for r in records:
        entry = r["readers"][key]
        out.append(Rated(r["person"], r["question"], r["arm"], r["words"],
                         entry["type"]["type"], mask_of(entry["type"]),
                         tuple(entry["clinical"][k] for k in FEATURES)))
    return out


@lru_cache(maxsize=None)
def count_profiles(masks):
    """Distinct attainable category totals; every unresolved row is assigned once."""
    totals = {(0, 0, 0, 0)}
    for mask in masks:
        next_totals = set()
        allowed = [i for i in range(4) if mask & (1 << i)]
        for profile in totals:
            for i in allowed:
                counts = list(profile)
                counts[i] += 1
                next_totals.add(tuple(counts))
        totals = next_totals
    return tuple(sorted(totals))


@lru_cache(maxsize=None)
def distance_by_patient(patient_masks, model_masks):
    """Exact model-distance extrema for each attainable patient count profile."""
    n, m = len(patient_masks), len(model_masks)
    assert n > 0 and m > 0
    denominator = 2 * n * m
    model_scaled = [tuple(n * x for x in counts) for counts in count_profiles(model_masks)]
    out = []
    for counts in count_profiles(patient_masks):
        a, b, c, d = (m * x for x in counts)
        distances = [abs(a - w) + abs(b - x) + abs(c - y) + abs(d - z)
                     for w, x, y, z in model_scaled]
        out.append(Interval(F(min(distances), denominator), F(max(distances), denominator)))
    return tuple(out)


def compare(masks_by_arm, models):
    p = masks_by_arm["patient"]
    conditional = {a: distance_by_patient(p, masks_by_arm[a]) for a in models}
    distance = {a: Interval(min(v.low for v in seq), max(v.high for v in seq))
                for a, seq in conditional.items()}
    paired = {}
    for a, b in combinations(models, 2):
        # Models vary independently conditional on the SAME patient profile.
        pairs = list(zip(conditional[a], conditional[b]))
        paired[a + "_minus_" + b] = Interval(min(x.low - y.high for x, y in pairs),
                                             max(x.high - y.low for x, y in pairs))
    return {"distance": distance, "paired_difference": paired}


def masks_by_arm(rows, arms=ARMS):
    return {a: tuple(sorted(r.mask for r in rows if r.arm == a)) for a in arms}


def weighted_comparisons(comparisons, weights):
    # Distinct questions (or observed length strata) contain disjoint rows.
    return {section: {key: sum((v[section][key] * w for v, w in zip(comparisons, weights)), ZERO)
                      for key in comparisons[0][section]}
            for section in ("distance", "paired_difference")}


def proportions(rows, masks):
    summary = {}
    for a in ARMS:
        n = len(masks[a])
        labels = Counter(r.label for r in rows if r.arm == a)
        totals = count_profiles(masks[a])
        counts = {k: [min(v[i] for v in totals), max(v[i] for v in totals)]
                  for i, k in enumerate(TYPES)}
        summary[a] = {"N": n, "observed_counts": {k: labels[k] for k in (*TYPES, "ambiguous", "technical_missing")},
                      "possible_counts": counts,
                      "possible_proportions": {k: Interval(F(lo, n), F(hi, n))
                                               for k, (lo, hi) in counts.items()}}
    p = summary["patient"]["possible_proportions"]
    signed = {}
    for a in MODELS:
        model = summary[a]["possible_proportions"]
        signed[a] = {k: Interval(model[k].low - p[k].high, model[k].high - p[k].low) for k in TYPES}
    return summary, signed


def word_bin(words):
    if words is None:
        return None
    return BINS[0 if words < 10 else 1 if words < 30 else 2]


def length_check(rows):
    models = ("developed", "base")
    arms = ("patient", *models)
    questions = {}
    for q in QUESTIONS:
        selected = [r for r in rows if r.question == q and r.arm in arms]
        unknown = {a: sum(r.words is None and r.arm == a for r in selected) for a in arms}
        n = sum(r.arm == "patient" for r in selected)
        strata, contributing, weights, gaps = {}, [], [], []
        for band in BINS:
            masks = masks_by_arm([r for r in selected if word_bin(r.words) == band], arms)
            sizes = {a: len(masks[a]) for a in arms}
            weight = F(sizes["patient"], n)
            detail = {"N": sizes, "known_patient_weight": str(weight)}
            if weight:
                missing = [a for a in models if not sizes[a]]
                if missing:
                    gaps.append({"stratum": band, "absent_arms": missing})
                else:
                    detail["known_length_comparison"] = compare(masks, models)
                    contributing.append(detail["known_length_comparison"])
                    weights.append(weight)
            strata[band] = detail
        coverage = not gaps and not any(unknown.values())
        questions[q] = {"known_strata": strata, "unknown_words_N": unknown, "observed_support_gaps": gaps,
                        "coverage_complete": coverage,
                        "standardized": weighted_comparisons(contributing, weights) if coverage else None}
    overall = None
    if all(v["coverage_complete"] for v in questions.values()):
        overall = weighted_comparisons([questions[q]["standardized"] for q in QUESTIONS], [F(1, 2)] * 2)
    return {"questions": questions, "overall": overall}


def clinical_summaries(rows):
    out = {}
    for q in (*QUESTIONS, "both"):
        out[q] = {}
        for a in ARMS:
            values = [r for r in rows if r.arm == a and (q == "both" or r.question == q)]
            features = {}
            for i, feature in enumerate(FEATURES):
                counts = Counter(r.clinical[i] for r in values)
                definite = counts["present"] + counts["absent"]
                features[feature] = {"N": len(values), "n": {s: counts[s] for s in STATUSES},
                                     "definite_N": definite,
                                     "present_among_definite": (counts["present"] / definite if definite else None)}
            out[q][a] = features
    return out


def strict_status(iv):
    return "satisfied" if iv.high < 0 else "failed" if iv.low >= 0 else "assignment_dependent"


def nonworse_status(iv):
    return "satisfied" if iv.high <= 0 else "failed" if iv.low > 0 else "assignment_dependent"


def rank_relation(iv):
    if iv.high < 0:
        return "<"
    if iv.low > 0:
        return ">"
    if iv.low == iv.high == 0:
        return "="
    return "assignment_dependent"


def compare_rankings(overalls):
    """Report guaranteed agreement, guaranteed disagreement or insufficient resolution."""
    first, second = overalls
    fixed = True
    for key in first:
        a, b = first[key], second[key]
        rank_a, rank_b = rank_relation(a), rank_relation(b)
        if rank_a != "assignment_dependent" and rank_b != "assignment_dependent":
            if rank_a != rank_b:
                return "different"
            continue
        fixed = False
        # If one reader always favours an arm and the other can only tie or
        # favour the opposite arm, uncertainty elsewhere cannot reconcile them.
        if (a.high < 0 <= b.low or a.high <= 0 < b.low or
                b.high < 0 <= a.low or b.high <= 0 < a.low):
            return "different"
    return "same" if fixed else "undetermined"


def analyze_reader(rows):
    questions, by_q = {}, {}
    for q in QUESTIONS:
        selected = [r for r in rows if r.question == q]
        masks = masks_by_arm(selected)
        comp = compare(masks, MODELS)
        by_q[q] = comp
        distribution, signed = proportions(selected, masks)
        questions[q] = {**comp, "distribution": distribution, "signed_model_minus_patient": signed}

    overall = weighted_comparisons(list(by_q.values()), [F(1, 2)] * 2)
    overall["signed_model_minus_patient"] = {
        a: {t: sum((questions[q]["signed_model_minus_patient"][a][t] * F(1, 2) for q in QUESTIONS), ZERO)
            for t in TYPES} for a in MODELS}
    leave_one_out = []
    for q, other_q in (QUESTIONS, QUESTIONS[::-1]):
        selected = [r for r in rows if r.question == q]
        for idx, person in enumerate(sorted({r.person for r in selected}), start=1):
            keep = [r for r in selected if r.person != person]
            reduced = compare(masks_by_arm(keep), MODELS)
            mean = weighted_comparisons([reduced, by_q[other_q]], [F(1, 2)] * 2)
            leave_one_out.append({"omitted_question": q, "omission_index_in_question": idx, **mean})

    length = length_check(rows)
    rivals = ("developed_minus_base", "developed_minus_short")
    strict = {k: strict_status(overall["paired_difference"][k]) for k in rivals}
    nonworse = {q: {k: nonworse_status(questions[q]["paired_difference"][k]) for k in rivals}
                for q in QUESTIONS}
    loo_strict = {}
    for k in rivals:
        counts = Counter(strict_status(v["paired_difference"][k]) for v in leave_one_out)
        loo_strict[k] = {label: counts[label] for label in ("satisfied", "failed", "assignment_dependent")}
    length_status = ("unverified_coverage" if length["overall"] is None else
                     strict_status(length["overall"]["paired_difference"]["developed_minus_base"]))
    prelength = (all(v == "satisfied" for v in strict.values())
                 and all(v == "satisfied" for q in nonworse.values() for v in q.values())
                 and all(v["satisfied"] == len(leave_one_out) for v in loo_strict.values()))
    decision = {"strict_overall": strict, "nonworse_each_question": nonworse,
                "strict_leave_one_out_counts": loo_strict, "prelength_criteria_satisfied": prelength,
                "length_developed_below_base": length_status,
                "all_frozen_criteria_satisfied": prelength and length_status == "satisfied",
                "overall_pairwise_ranks": {k: rank_relation(iv) for k, iv in overall["paired_difference"].items()}}
    return {"questions": questions, "overall": overall, "leave_one_out": leave_one_out, "length": length,
            "clinical": clinical_summaries(rows), "decision": decision}


def analyze(records):
    validate(records)
    readers = {reader: analyze_reader(select_reader(records, reader)) for reader in READERS}
    decisions = [r["decision"] for r in readers.values()]
    rank_agreement = compare_rankings([r["overall"]["paired_difference"] for r in readers.values()])
    return {"design": {"people": 14, "people_per_question": 7, "repetitions_per_input_model": 3,
                       "questions": QUESTIONS, "types": TYPES, "clinical_statuses": STATUSES,
                       "distance": "TV = 0.5 * sum(abs(model probability - patient probability))",
                       "question_weights": ["1/2", "1/2"], "difference_direction": "first named minus second named",
                       "assignment_range": "attainable extrema; both distances in a paired difference share patient assignments",
                       "missing_types": "ambiguous allocated to alternatives; technical_missing to all four categories",
                       "leave_one_out": "omit one patient and all 9 corresponding model replies; average Q2 and Q3 equally",
                       "length": "within-question TV conditional on word bin, weighted by question-specific patient bin frequency"},
            "readers": readers, "joint_decision": {"overall_rank_agreement": rank_agreement,
                                                 "common_frozen_criteria_satisfied": rank_agreement == "same" and
                                                 all(d["all_frozen_criteria_satisfied"] for d in decisions)}}


def show(iv, signed=False):
    def num(x):
        return f"{float(x):+.3f}" if signed and x != 0 else f"{float(x):.3f}"
    return num(iv.low) if iv.low == iv.high else f"[{num(iv.low)}, {num(iv.high)}]"


def table(lines, headers, rows):
    lines.extend(["", "| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"])
    lines.extend("| " + " | ".join(map(str, row)) + " |" for row in rows)


def tables(report):
    lines = ["# DAIS-C 첫 답변 분포 비교", "",
             "14명, 질문별 7명. 각 질문에서 모델별 21개 계획 응답을 집계했다. 대괄호는 허용한 유형 배정에서 가능한 최솟값과 최댓값이다. 표는 소수 셋째 자리로 반올림했고 판정은 정확한 분수로 계산했다. Δ는 앞 조건의 거리에서 뒤 조건의 거리를 뺀 값으로 음수면 앞 조건이 환자 분포에 가깝다."]
    rankings = {"same": "일치", "different": "불일치", "undetermined": "배정에 따라 미확정"}
    decision = report["joint_decision"]
    lines.extend(["", f"두 판독기의 전체 순위는 {rankings[decision['overall_rank_agreement']]}이며 동결 기준에 따른 개발판 공통 우위는 " +
                  ("확인됐다." if decision["common_frozen_criteria_satisfied"] else "미확인이다.")])
    for reader, result in report["readers"].items():
        by_q = result["questions"]
        lines.extend(["", "## " + reader, "", "### 반응 유형", "",
                      "각 칸은 확정 유형 수 또는 범주 미확정 수 / 전체 응답 수다. 배정별 유형 비율의 범위는 analysis.json에 있다."])
        rows = []
        for q in QUESTIONS:
            for a in ARMS:
                cell = by_q[q]["distribution"][a]
                rows.append([q, a, *[f"{n}/{cell['N']}" for n in cell["observed_counts"].values()]])
        table(lines, ["질문", "조건", *TYPES, "ambiguous", "technical missing"], rows)
        lines.extend(["", "### 총변동거리와 같은 환자 배정을 사용한 거리 차이"])
        rows = []
        for q, comp in [*( (q, by_q[q]) for q in QUESTIONS), ("동일가중 평균", result["overall"])]:
            rows.append([q, *[show(comp["distance"][a]) for a in MODELS],
                         *[show(v, True) for v in comp["paired_difference"].values()]])
        table(lines, ["질문", *MODELS, "Δ developed−base", "Δ developed−short", "Δ base−short"], rows)
        lines.extend(["", "### 유형별 모델 비율 − 환자 비율"])
        rows = [[q, a, *[show(s["signed_model_minus_patient"][a][t], True) for t in TYPES]]
                for q, s in [*((q, by_q[q]) for q in QUESTIONS), ("동일가중 평균", result["overall"])] for a in MODELS]
        table(lines, ["질문", "조건", *TYPES], rows)
        lines.extend(["", "### 실제 화자와 연결된 모든 반복을 함께 제외한 결과", "",
                      "번호는 질문 안의 익명 순번이다. 각 행은 해당 화자 1명과 모델 응답 9개를 제외한 뒤 두 질문의 거리를 같은 비중으로 평균한 결과다."])
        table(lines, ["제외한 질문", "제외 순번", "Δ developed−base", "Δ developed−short"],
              [[t["omitted_question"], t["omission_index_in_question"],
                show(t["paired_difference"]["developed_minus_base"], True),
                show(t["paired_difference"]["developed_minus_short"], True)] for t in result["leave_one_out"]])
        lines.extend(["", "### 환자 길이층 비율을 적용한 비교", "",
                      "N은 길이층 안의 응답 수다. 환자 비중이 0인 층은 기여도가 0이며 환자가 있는 층에서 비교 조건의 관측값이 없으면 질문별 표준화 거리는 미확인이다."])
        rows = []
        for q, detail in result["length"]["questions"].items():
            for band, v in detail["known_strata"].items():
                comp = v.get("known_length_comparison")
                rows.append([q, band, *v["N"].values(), v["known_patient_weight"],
                             *([show(comp["distance"][a]) for a in ("developed", "base")] +
                               [show(comp["paired_difference"]["developed_minus_base"], True)] if comp else ["—"] * 3)])
            rows.append([q, "길이 미상", *detail["unknown_words_N"].values(), "—", "—", "—", "—"])
        table(lines, ["질문", "단어", "N patient", "N developed", "N base", "환자 가중치", "TV developed", "TV base", "Δ developed−base"], rows)
        rows = []
        for q, comp in [*((q, d["standardized"]) for q, d in result["length"]["questions"].items()), ("동일가중 평균", result["length"]["overall"])]:
            rows.append([q, *([show(comp["distance"][a]) for a in ("developed", "base")] +
                              [show(comp["paired_difference"]["developed_minus_base"], True)] if comp else ["미확인"] * 3)])
        table(lines, ["표준화 거리", "TV developed", "TV base", "Δ developed−base"], rows)
        lines.extend(["", "### 임상 항목", "",
                      "각 셀은 양성·음성·불확실·판독 불충분·기술 결측의 순서로 n을 적었다. 왼쪽의 N이 다섯 상태의 공통 분모다. 괄호의 분모는 양성과 음성의 합이다."])
        rows = []
        for q, arms in result["clinical"].items():
            for arm, feats in arms.items():
                cells = []
                for feature in FEATURES:
                    v = feats[feature]
                    counts = "/".join(str(v["n"][s]) for s in STATUSES)
                    cells.append(f"{counts} ({v['n']['present']}/{v['definite_N']})")
                rows.append([q, arm, feats[FEATURES[0]]["N"], *cells])
        table(lines, ["질문", "조건", "N", *FEATURES], rows)
        d = result["decision"]
        korean = {"satisfied": "충족", "failed": "미충족", "assignment_dependent": "배정에 따라 달라짐",
                  "unverified_coverage": "길이층 비교 미확인"}
        lines.extend(["", "### 판정"])
        rows = []
        for k, label in (("developed_minus_base", "개발−기본"), ("developed_minus_short", "개발−단답")):
            loo = d["strict_leave_one_out_counts"][k]
            rows.append([label, korean[d["strict_overall"][k]], *[korean[d["nonworse_each_question"][q][k]] for q in QUESTIONS],
                         f"{loo['satisfied']}/{loo['failed']}/{loo['assignment_dependent']}"])
        table(lines, ["거리 대비", "전체 엄격 우위", "Q2 열위 없음", "Q3 열위 없음", "1명 제외 시 충족/미충족/배정 의존"], rows)
        lines.extend(["", f"개발−기본 길이층 점검은 {korean[d['length_developed_below_base']]}이다."])
    return "\n".join(lines) + "\n"


def self_test():
    """Independent row-by-row assignment enumeration on unequal-denominator toy data."""
    from random import Random

    rng = Random(7)
    arms = ("patient", "developed", "base")

    def brute_profiles(masks):
        choices = [tuple(i for i in range(4) if mask & (1 << i)) for mask in masks]
        return {tuple(F(s.count(i), len(masks)) for i in range(4)) for s in product(*choices)}

    def tv(x, y):
        return sum(abs(i - j) for i, j in zip(x, y)) / 2

    for _ in range(25):
        sample = {a: tuple(sorted(rng.randint(1, 15) for _ in range(rng.randint(1, 3)))) for a in arms}
        computed = compare(sample, arms[1:])
        deltas, ds, bs = [], [], []
        for p, d, b in product(*(brute_profiles(sample[a]) for a in arms)):
            x, y = tv(p, d), tv(p, b)
            ds.append(x)
            bs.append(y)
            deltas.append(x - y)
        for iv, vals in ((computed["distance"]["developed"], ds), (computed["distance"]["base"], bs),
                         (computed["paired_difference"]["developed_minus_base"], deltas)):
            assert (iv.low, iv.high) == (min(vals), max(vals))
    shared = compare({"patient": (3,), "developed": (1,), "base": (1,)}, arms[1:])
    assert shared["distance"]["developed"] == Interval(0, 1)
    assert shared["paired_difference"]["developed_minus_base"] == ZERO
    assert [word_bin(n) for n in (9, 10, 29, 30, None)] == [BINS[0], BINS[1], BINS[1], BINS[2], None]

    records = []
    for q in QUESTIONS:
        for i in range(7):
            for a in ARMS:
                for rep in ((0,) if a == "patient" else (1, 2, 3)):
                    label = TYPES[0] if a in ("patient", "developed") else TYPES[1] if a == "base" else TYPES[2]
                    entry = {"type": {"type": label, "alternatives": []},
                             "clinical": {k: STATUSES[0] for k in FEATURES}}
                    uid = f"{q}_{i}_{a}_{rep}"
                    records.append(dict(uid=uid, person=f"{q}_{i}", question=q, arm=a, rep=rep, words=9+i,
                                        readers={r: entry for r in READERS}))
    result = analyze(records)
    assert result["joint_decision"] == {"overall_rank_agreement": "same", "common_frozen_criteria_satisfied": True}
    data = result["readers"][READERS[0]]
    assert len(data["leave_one_out"]) == 14
    assert all(s["paired_difference"]["developed_minus_base"] == Interval(-1, -1) for s in data["leave_one_out"])
    assert data["length"]["overall"]["distance"]["base"] == Interval(1, 1)
    assert data["clinical"]["both"]["developed"][FEATURES[0]]["definite_N"] == 42

    for r in records:
        if r["question"] == "Q2" and r["arm"] == "developed" and r["words"] < 10:
            r["words"] = 10
    known_gaps = length_check(select_reader(records, READERS[0]))
    assert known_gaps["questions"]["Q2"]["observed_support_gaps"] == [{"stratum": BINS[0], "absent_arms": ["developed"]}]
    assert known_gaps["overall"] is None
    for r in records:
        if r["arm"] == "developed" and r["person"] == "Q2_0":
            r["words"] = 9
    records[0]["words"] = None
    records[0]["readers"]["opus"]["type"] = {"type": "technical_missing"}
    assert mask_of(records[0]["readers"]["opus"]["type"]) == 15
    assert mask_of({"type": "ambiguous", "alternatives": ["expanded", "other"]}) == 9
    assert length_check(select_reader(records, READERS[0]))["overall"] is None

    # Q2 marginal types match perfectly for developed, but both of its
    # length-specific type distributions are opposite to the patients'.
    for r in records:
        arm = r["arm"]
        index = int(r["person"].split("_")[-1])
        expanded = r["question"] == "Q2" and index < (3 if arm == "base" else 2)
        long = not expanded
        if arm == "developed" and r["question"] == "Q2":
            long = not long
        r["words"] = 31 if long else 8
        for reader in READERS:
            r["readers"][reader]["type"] = {"type": TYPES[0 if expanded else 1], "alternatives": []}
    demo = analyze(records)["readers"]["gpt"]
    edge = "developed_minus_base"
    assert demo["overall"]["paired_difference"][edge] == Interval(F(-1, 14), F(-1, 14))
    assert demo["length"]["overall"]["paired_difference"][edge] == Interval(F(1, 2), F(1, 2))
    assert demo["questions"]["Q2"]["signed_model_minus_patient"]["base"]["expanded"] == Interval(F(1, 7), F(1, 7))
    assert demo["leave_one_out"][2]["paired_difference"][edge] == ZERO
    assert demo["leave_one_out"][7]["paired_difference"][edge] == Interval(F(-1, 14), F(-1, 14))
    assert compare_rankings([{"a": Interval(-1, 0)}, {"a": Interval(1, 1)}]) == "different"
    print("Self-test passed: exact paired extrema, design, leave-one-out, length coverage and clinical denominators.")


def write_atomic(path, contents):
    with NamedTemporaryFile("w", dir=path.parent, encoding="utf-8", delete=False) as stream:
        stream.write(contents)
        temporary = stream.name
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=HERE / "private/ratings.json")
    parser.add_argument("--out-dir", type=Path, default=HERE)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    records = json.loads(args.input.read_text(encoding="utf-8"))
    result = analyze(records)
    as_json = json.dumps(result, ensure_ascii=False, indent=2, default=interval_json) + "\n"
    as_tables = tables(result)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_atomic(args.out_dir / "analysis.json", as_json)
    write_atomic(args.out_dir / "tables.md", as_tables)
    print(json.dumps(result["joint_decision"]))


if __name__ == "__main__":
    main()
