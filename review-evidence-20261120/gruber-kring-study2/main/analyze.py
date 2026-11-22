"""Offline, preregistered Gruber–Kring Study 2 comparisons. No model calls."""
import argparse
from collections import Counter
from hashlib import sha256
from itertools import combinations, product
import json
import math
from pathlib import Path
from statistics import mean, median, stdev

HERE = Path(__file__).resolve().parent
CASES = tuple(f"GK{i:02}" for i in range(1, 13))
GROUPS = {
    "positive": ("happy", "compassion", "proud"),
    "negative": ("sad", "afraid", "embarrassed", "disgusted"),
    "neutral": ("directions", "morning", "meal"),
}
TOPICS = tuple(t for topics in GROUPS.values() for t in topics)
CELLS = tuple(product(CASES, TOPICS))
ARMS = ("developed", "base", "short")
READERS = ("opus", "gpt")
SCALES = ("elaboration", "meaning_clarity")
REF = {
    "patient": {"elaboration": (2.40, 2.08, 1.87), "meaning_clarity": (2.06, 2.17, 1.76),
                "words": (184.81, 207.10, 163.93)},
    "nonpatient": {"elaboration": (2.00, 1.85, 1.50), "meaning_clarity": (1.85, 1.77, 1.39),
                   "words": (256.63, 258.51, 150.13)},
}
EPS = 1e-10


def average(items):
    values = list(items)
    return mean(values) if values else None


def descriptive(values):
    observed = [v for v in values if v is not None]
    return {"n": len(observed), "mean": average(observed), "sd": stdev(observed) if len(observed) >= 2 else None,
            "median": median(observed) if observed else None, "min": min(observed, default=None),
            "max": max(observed, default=None)}


def input_data(key, scores):
    index = {(r["case"], r["topic"], r["arm"]): r for r in key}
    assert len(key) == len(index) == 360 and set(index) == {(*ct, a) for ct in CELLS for a in ARMS}
    uids = {r["uid"] for r in key}
    assert len(uids) == 360
    for row in key:
        assert type(row["words"]) is int and row["words"] >= 0
    forms = {(r["reader"], r["uid"]): r for r in scores}
    assert len(forms) == len(scores) == 720 and set(forms) == set(product(READERS, uids))
    for row in scores:
        assert row["status"] in {"rated", "no_narrative", "technical_missing"}
        if row["status"] == "rated":
            assert row["events"]
            for scale in SCALES:
                event_scores = [e[scale] for e in row["events"]]
                assert all(v in (1, 2, 3) and type(v) is int for v in event_scores)
                assert abs(row[scale] - mean(event_scores)) < EPS
        else:
            assert all(row[s] is None for s in SCALES)
    return index, forms


def cell_means(data, cells, *, topic_first=False, missing=None):
    """Full analysis: within person then across people. Matched: within topic then across topics."""
    grouped = {}
    for case, topic in cells:
        v = data[case, topic]
        if v is None:
            v = missing
        if v is not None:
            grouped.setdefault(topic if topic_first else case, {})[case if topic_first else topic] = v
    result = []
    for topics in GROUPS.values():
        if topic_first:
            # A missing required topic makes this vector unavailable.
            per_topic = [average(grouped.get(t, {}).values()) for t in topics]
            result.append(average(per_topic) if None not in per_topic else None)
        else:
            summaries = [average(by_topic[t] for t in topics if t in by_topic) for by_topic in grouped.values()]
            result.append(average(v for v in summaries if v is not None))
    return result


def center(v):
    m = mean(v)
    return [x - m for x in v]


def distance(v, ref, which):
    if which == "S":
        v, ref = center(v), center(ref)
    return mean(abs(x - y) for x, y in zip(v, ref))


def metrics(v, scale):
    full = None not in v
    return {
        "means": v,
        "signed_patient_errors": [None if x is None else x - y for x, y in zip(v, REF["patient"][scale])],
        **{label: {metric: distance(v, refs[scale], metric) if full else None for metric in ("D", "S")}
           for label, refs in REF.items()},
    }


def cross(a, b):
    return (a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0])


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def reference_vertices(ref, vectors, which):
    """Vertices of every polytope of linearity of all absolute deviations inside the rounding box."""
    box = [(x - .005, x + .005) for x in ref]
    identity = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]
    planes = [(axis, x) for axis, bounds in zip(identity, box) for x in bounds]
    for v in vectors:
        for i, axis in enumerate(identity):
            if which == "D":
                planes.append((axis, v[i]))
            else:
                # same zero plane as centered(v)[i] == centered(reference)[i]
                planes.append((tuple(3*x - 1 for x in axis), 3*v[i] - sum(v)))
    for (a, x), (b, y), (c, z) in combinations(planes, 3):
        bc, ca, ab = cross(b, c), cross(c, a), cross(a, b)
        det = dot(a, bc)
        if not det:
            continue
        point = tuple((x*bc[i] + y*ca[i] + z*ab[i])/det for i in range(3))
        if all(lo-EPS <= w <= hi+EPS for w, (lo, hi) in zip(point, box)):
            yield point


def rounding_difference(a, b, ref, which):
    # The same unknown published means apply to both arms.
    ds = [distance(b, r, which) - distance(a, r, which) for r in reference_vertices(ref, (a,b), which)]
    return [min(ds), max(ds)]


def abs_box(lo, hi):
    return (0 if lo <= 0 <= hi else min(abs(lo), abs(hi)), max(abs(lo), abs(hi)))


def missing_distance_interval(lower, upper, ref, which):
    """Conservative joint interval for reference rounding and all missing-cell completions."""
    lo = [x-y-.005 for x, y in zip(lower, ref)]
    hi = [x-y+.005 for x, y in zip(upper, ref)]
    if which == "S":
        lo, hi = (
            [(2*lo[i] - sum(hi[j] for j in range(3) if j != i))/3 for i in range(3)],
            [(2*hi[i] - sum(lo[j] for j in range(3) if j != i))/3 for i in range(3)],
        )
    ab = [abs_box(x,y) for x,y in zip(lo,hi)]
    return [mean(v[side] for v in ab) for side in (0,1)]


def pair_analysis(a, b, planned, scale, topic_first=False):
    common = [c for c in planned if a[c] is not None and b[c] is not None]
    x, y = (cell_means(v, common, topic_first=topic_first) for v in (a,b))
    filled = [[cell_means(v, planned, topic_first=topic_first, missing=m) for m in (1,3)] for v in (a,b)]
    result = {"n_planned": len(planned), "n_common": len(common),
              "common_by_topic": dict(Counter(t for _, t in common)),
              "common_by_valence_cases": {g: len({c for c,t in common if t in ts}) for g,ts in GROUPS.items()},
              "means_developed": x, "means_comparator": y}
    for which in ("D", "S"):
        if None in x or None in y:
            result[which] = {"confirmed_advantage": False, "point_gap": None}
            continue
        ref = REF["patient"][scale]
        dx, dy = distance(x, ref, which), distance(y, ref, which)
        rounding = rounding_difference(x, y, ref, which)
        bounds = rounding
        if len(common) != len(planned):
            (ax,bx), (ay,by) = (missing_distance_interval(*r, ref, which) for r in filled)
            bounds = [ay-bx, by-ax]
        result[which] = {"developed": dx, "comparator": dy, "point_gap": dy-dx,
                         "gap_ref_rounding": rounding, "gap_full_denominator_bounds": bounds,
                         "confirmed_advantage": dy-dx > EPS and rounding[0] > EPS and bounds[0] > EPS}
    return result


def vs_nonpatient(data, scale):
    v = cell_means(data, CELLS)
    if None in v:
        return {"confirmed": False}
    missing = any(y is None for y in data.values())
    if missing:
        box = [cell_means(data, CELLS, missing=m) for m in (1,3)]
    ranges = {}
    for label, refs in REF.items():
        ref = refs[scale]
        if missing:
            ranges[label] = missing_distance_interval(*box, ref, "D")
        else:
            distances = [distance(v,r,"D") for r in reference_vertices(ref, [v], "D")]
            ranges[label] = [min(distances), max(distances)]
    gap = distance(v, REF["nonpatient"][scale], "D") - distance(v, REF["patient"][scale], "D")
    return {"point_gap_nonpatient_minus_patient": gap, "bounds": ranges,
            "confirmed": gap > EPS and ranges["nonpatient"][0] - ranges["patient"][1] > EPS}


def score_counts(values):
    return dict(sorted(Counter(f"{v:.12g}" for v in values if v is not None).items()))


def agreements(key, forms):
    result = {}
    for arm in (*ARMS, "all"):
        roster = [r["uid"] for r in key if arm == "all" or r["arm"] == arm]
        counts = Counter((forms["opus",u]["status"], forms["gpt",u]["status"]) for u in roster)
        both = [u for u in roster if forms["opus",u]["status"] == forms["gpt",u]["status"] == "rated"]
        record = {"n": len(roster), "both_rated": len(both),
                  "eligibility_disagreements": sum(n for (a,b),n in counts.items() if (a=="rated") != (b=="rated")),
                  "status_table": {f"{a}/{b}": n for (a,b),n in counts.items()}}
        for scale in SCALES:
            table = [[0]*3 for _ in range(3)]
            exact = 0
            fractional = Counter()
            for uid in both:
                a, b = [forms[r,uid][scale] for r in READERS]
                exact += abs(a-b)<EPS
                if int(a) == a and int(b) == b:
                    table[int(a)-1][int(b)-1] += 1
                else:
                    fractional[f"{a:.12g}/{b:.12g}"] += 1
            record[scale] = {"matrix_rows_opus_cols_gpt": table, "fractional_pairs": dict(fractional),
                             "exact_all": exact, "denominator_all": len(both)}
        result[arm] = record
    return result


def data_summary(data, cells):
    v = cell_means(data, cells)
    individual = {case: cell_means(data, [ct for ct in cells if ct[0] == case]) for case in CASES}
    return {"means": v, "person_by_valence": individual,
            "between_person": {g: descriptive(c[i] for c in individual.values()) for i,g in enumerate(GROUPS)},
            "by_topic": {t: {"distribution": score_counts(data[c] for c in cells if c[1]==t),
                             **descriptive(data[c] for c in cells if c[1]==t)} for t in TOPICS}}


def close_length(a, b):
    return min(a,b) > 0 and 5*min(a,b) >= 4*max(a,b)


def analyze(key, scores):
    index, forms = input_data(key, scores)
    status, word, data = {}, {}, {}
    for arm in ARMS:
        word[arm] = {c: index[*c,arm]["words"] for c in CELLS}
        for reader in READERS:
            selected = {c: forms[reader, index[*c,arm]["uid"]] for c in CELLS}
            for scale in SCALES:
                data[reader,scale,arm] = {c: s[scale] for c,s in selected.items()}
            status.setdefault(reader,{})[arm] = {
                "all": dict(Counter(s["status"] for s in selected.values())),
                "by_topic": {t: dict(Counter(s["status"] for (_,q),s in selected.items() if q == t)) for t in TOPICS},
                "event_counts_rated": dict(Counter(len(s["events"]) for s in selected.values() if s["status"]=="rated"))}
    length, matched = {}, {}
    for b in ARMS[1:]:
        pairs = [c for c in CELLS if close_length(word["developed"][c], word[b][c])]
        counts = {t: sum(ct[1] == t for ct in pairs) for t in TOPICS}
        length[b] = {"counts": counts, "total": len(pairs), "minimum_topic": min(counts.values()),
                     "coverage_ok": min(counts.values()) >= 6,
                     "included_cases": {t: [c for c, q in pairs if q == t] for t in TOPICS}}
        matched[b] = pairs
    full, comparisons, length_sensitivity, reference_check = {}, {}, {}, {}
    for r in READERS:
        full[r], comparisons[r], length_sensitivity[r], reference_check[r] = {}, {}, {}, {}
        for scale in SCALES:
            full[r][scale] = {}
            for arm in ARMS:
                observations = data[r,scale,arm]
                summary = data_summary(observations, CELLS)
                summary.update(metrics(summary["means"], scale))
                full[r][scale][arm] = summary
            a = data[r,scale,"developed"]
            reference_check[r][scale] = vs_nonpatient(a, scale)
            comparisons[r][scale], length_sensitivity[r][scale] = {}, {}
            for b in ARMS[1:]:
                other = data[r,scale,b]
                pair = pair_analysis(a, other, CELLS, scale)
                # When data are complete, compute every paired rank even for a failing overall claim.
                loo = {}
                for case in CASES:
                    sub = [c for c in CELLS if c[0] != case]
                    result = pair_analysis(a, other, sub, scale)
                    loo[case] = {m: result[m]["point_gap"] for m in ("D","S")}
                for m in ("D","S"):
                    g = pair[m]["point_gap"]
                    sign = lambda x: (x>EPS) - (x < -EPS)
                    pair[m]["loo_changed_cases"] = [c for c,v in loo.items() if g is not None and
                                                    v[m] is not None and sign(v[m]) != sign(g)]
                pair["leave_one_out_gaps"] = loo
                comparisons[r][scale][b] = pair
                p = matched[b]
                nvalid = {t: sum(q == t and a[c,q] is not None and other[c,q] is not None for c,q in p) for t in TOPICS}
                enough = length[b]["coverage_ok"] and min(nvalid.values()) >= 6
                length_sensitivity[r][scale][b] = {"coverage_ok": enough, "scorable_pairs_by_topic": nvalid,
                    "result": pair_analysis(a, other, p, scale, topic_first=True) if enough else None}
    rankings = {}
    for r,s in product(READERS,SCALES):
        rank_cases = {}
        for omitted in (None, *CASES):
            mask = [c for c in CELLS if c[0] != omitted and all(data[r,s,arm][c] is not None for arm in ARMS)]
            vectors = {arm: cell_means(data[r,s,arm], mask) for arm in ARMS}
            groups = {}
            for metric in ("D","S"):
                ds = {arm: distance(v,REF["patient"][s],metric) if None not in v else None for arm,v in vectors.items()}
                tiers = []
                if None not in ds.values():
                    for arm in sorted(ds, key=ds.get):
                        if tiers and abs(ds[arm] - ds[tiers[-1][0]]) <= EPS:
                            tiers[-1].append(arm)
                        else:
                            tiers.append([arm])
                groups[metric] = {"distances": ds, "closest_to_farthest": tiers}
            rank_cases[omitted or "all"] = groups
        rankings.setdefault(r,{})[s] = rank_cases
    primary = all(comparisons[r]["elaboration"][b][m]["confirmed_advantage"]
                  for r,b,m in product(READERS,ARMS[1:],("D","S")))
    support = primary and all(comparisons[r]["meaning_clarity"][b]["D"]["confirmed_advantage"]
                              for r,b in product(READERS,ARMS[1:]))
    stable = primary and all(not comparisons[r]["elaboration"][b][m]["loo_changed_cases"]
                             for r,b,m in product(READERS,ARMS[1:],("D","S")))
    length_primary = primary and all(v["coverage_ok"] and all(v["result"][m]["confirmed_advantage"] for m in ("D","S"))
                for r in READERS for v in length_sensitivity[r]["elaboration"].values())
    length_support = length_primary and support and all(v["coverage_ok"] and v["result"]["D"]["confirmed_advantage"]
                for r in READERS for v in length_sensitivity[r]["meaning_clarity"].values())
    return {"reference": REF,"word_summaries": {a:data_summary(word[a], CELLS) for a in ARMS},
            "status": status,"agreement": agreements(key, forms),"full": full,"comparisons": comparisons,
            "length_pairs": length,"length_sensitivity": length_sensitivity,"developed_reference": reference_check,
            "three_way_rankings_leave_one_out": rankings,
            "conclusions": {"elaboration_both_distances_both_controls_both_readers": primary,
                            "elaboration_same_direction_all_leave_one_out": stable,
                            "supporting_clarity_with_primary": support, "primary_persists_at_similar_lengths": length_primary,
                            "clarity_persists_at_similar_lengths": length_support,
                            "developed_closer_to_patient_than_nonpatient_both_scales_readers":
                            all(reference_check[r][s]["confirmed"] for r,s in product(READERS,SCALES))}}


def fmt(x, digits=3):
    return "—" if x is None else f"{x:.{digits}f}"


def table(columns, rows):
    def row(parts):
        return "| " + " | ".join(map(str,parts)) + " |"
    return "\n".join([row(columns),row(["---"]*len(columns)),*(row(parts) for parts in rows)])


def report(out):
    names={"developed":"개발판","base":"기본판","short":"단답 대조","opus":"Opus","gpt":"GPT",
           "elaboration":"구체적 전개","meaning_clarity":"의미 명료도"}
    parts=["# Gruber–Kring Study 2 과제 비교표", "각 벡터의 순서는 긍정·부정·중립이다. 거리와 차이는 반올림 전 값으로 판단했다. 주 분석은 가상 인물 12명에게 같은 가중치를 준다. 표에서 1점은 각 항목이 가장 양호함을 뜻한다."]
    for scale in SCALES:
        rows=[]
        for ref,name in (("patient","원저 환자군"),("nonpatient","원저 비환자군")):
            rows.append(["사람",name,*[fmt(v,2) for v in REF[ref][scale]],"—","—","—"])
        for r,a in product(READERS,ARMS):
            v=out["full"][r][scale][a]
            rows.append([names[r],names[a],*[fmt(x) for x in v["means"]],
                         fmt(v["patient"]["D"]),fmt(v["patient"]["S"]),fmt(v["nonpatient"]["D"])])
        parts.extend(["## "+names[scale],table(["판독","조건","긍정","부정","중립","환자 D","환자 S","비환자 D"],rows)])

    rows=[]
    for r,s,b,m in product(READERS,SCALES,ARMS[1:],("D","S")):
        item=out["comparisons"][r][s][b]
        res=item[m]
        bounds=res.get("gap_full_denominator_bounds")
        rows.append([names[r],names[s],names[b],m,item["n_common"],fmt(res["point_gap"],4),
                     "–".join(fmt(v,4) for v in bounds) if bounds else "—",
                     "충족" if res["confirmed_advantage"] else "미충족",", ".join(res["loo_changed_cases"]) or "없음"])
    parts.extend(["## 같은 인물·문항에서의 개발판 우위 판정",
        "차이는 대조 거리에서 개발판 거리를 뺀 값이다. 양수이면 개발판이 더 가깝다. 범위는 문헌 평균 반올림 ±0.005를 고려한다. 결측이 있으면 미관측 1–3점의 보수적 범위도 포함한다. 표의 사례 제외 변화는 점추정 순위 기준이다.",
        table(["판독","항목","대조","거리","공통 수","차이","차이 범위","개발판 우위","하나 제외 시 방향 변경"],rows)])

    rows=[]
    for s in SCALES:
        for r in READERS:
            chk=out["developed_reference"][r][s]
            rows.append([names[r],names[s],fmt(chk.get("point_gap_nonpatient_minus_patient"),4),
                         "충족" if chk["confirmed"] else "미충족"])
    parts.extend(["## 개발판과 비환자 준거",table(["판독","항목","비환자 D − 환자 D","개발판이 환자 쪽에 더 가까움"],rows)])

    rows=[]
    for t in TOPICS:
        rows.append([t,*[fmt(out["word_summaries"][a]["by_topic"][t]["mean"],1) for a in ARMS],
                     *[out["length_pairs"][b]["counts"][t] for b in ARMS[1:]]])
    rows.append(["전체 대응 쌍","—","—","—",*[out["length_pairs"][b]["total"] for b in ARMS[1:]]])
    parts.extend(["## 문항별 단어 수와 길이 대응 쌍",
        "조건별 문항당 생성 답 12개의 평균 단어 수다. 개발판과 대조의 같은 인물·문항에서 짧은 쪽이 긴 쪽 길이의 80% 이상이면 길이가 대응한다.",
        table(["주제","개발판 단어","기본판 단어","단답 단어","개발–기본 (쌍)","개발–단답 (쌍)"],rows)])
    rows=[]
    for label,vec in (("원저 환자군",REF["patient"]["words"]),("원저 비환자군",REF["nonpatient"]["words"])):
        rows.append([label,*[fmt(x,2) for x in vec]])
    for a in ARMS:
        rows.append([names[a],*[fmt(x,2) for x in out["word_summaries"][a]["means"]]])
    parts.extend(["### 정서조건별 단어 수",table(["집단 또는 조건","긍정","부정","중립"],rows)])
    rows=[]
    for r,s,b in product(READERS,SCALES,ARMS[1:]):
        test=out["length_sensitivity"][r][s][b]
        score=test["result"]
        rows.append([names[r],names[s],names[b],min(test["scorable_pairs_by_topic"].values()),
                     "충족" if test["coverage_ok"] else "판정 보류",*
                     [fmt(score[m]["point_gap"],4) if score else "—" for m in ("D","S")]])
    parts.extend(["### 길이 대응 후 비교", "각 문항에서 판독 가능한 대응 쌍이 6개 이상 있어야 판정한다. 통과 시 문항 안에서 사람들, 정서조건 안에서 문항들에 같은 가중치를 준다.",
                  table(["판독","항목","대조","문항별 최소 쌍","분모 기준","D 차이","S 차이"],rows)])

    rows=[]
    for r,a in product(READERS,ARMS):
        st=out["status"][r][a]
        rows.append([names[r],names[a],*[st["all"].get(status,0) for status in ("rated","no_narrative","technical_missing")],
                     sum(v for k,v in st["event_counts_rated"].items() if int(k)>1)])
    parts.extend(["## 제공률과 판독자 간 일치도",table(["판독","조건","채점","서사 미제공","기술 결측","별개 사건 복수"],rows)])
    agreement=out["agreement"]["all"]
    parts.append(f"판독 가능 여부가 갈린 답은 {agreement['eligibility_disagreements']}/{agreement['n']}개다.")
    for s in SCALES:
        c=agreement[s]
        rows=[[i+1,*v] for i,v in enumerate(c["matrix_rows_opus_cols_gpt"])]
        parts.extend(["### "+names[s],table(["Opus 점수","GPT 1","GPT 2","GPT 3"],rows),
                      f"답 단위 정확 일치 {c['exact_all']}/{c['denominator_all']}. 한 판독자라도 사건 평균이 분수 점수인 답 {sum(c['fractional_pairs'].values())}개는 3×3표 밖에서 정확 일치 분모에 포함했다."])
    rows=[]
    for r,s,a in product(READERS,SCALES,ARMS):
        st=out["full"][r][s][a]["between_person"]
        rows.append([names[r],names[s],names[a],*[fmt(st[g]["sd"]) for g in GROUPS]])
    parts.extend(["## 인물 간 점수의 흩어짐","각 인물의 정서조건별 문항 평균을 낸 뒤 인물 간 표본 표준편차를 구했다.",
                  table(["판독","항목","조건","긍정 SD","부정 SD","중립 SD"],rows)])
    rows=[]
    for r,topic,a in product(READERS,TOPICS,ARMS):
        values=[]
        for s in SCALES:
            dist=out["full"][r][s][a]["by_topic"][topic]["distribution"]
            values.extend([dist.get(str(i),0) for i in [1,2,3]])
            values.append(", ".join(f"{v}×{n}" for v,n in dist.items() if v not in {"1","2","3"}) or "—")
        missing=out["status"][r][a]["by_topic"][topic]
        rows.append([names[r],topic,names[a],*values,missing.get("no_narrative",0),missing.get("technical_missing",0)])
    parts.extend(["## 문항별 점수 빈도",table(["판독","문항","조건","전개 1","전개 2","전개 3","전개 분수",
                  "명료도 1","명료도 2","명료도 3","명료도 분수","서사 미제공","기술 결측"],rows),
                  "개별 사건이 여럿이면 해당 판독자의 사건 점수 평균이 문항 점수다. 사람 판독의 집단 집계치와 LLM이 채점한 합성문의 비교다. [원저 Study 2 표 3](https://esilab.berkeley.edu/wp-content/uploads/2017/12/Gruber-Kring-2008.pdf#page=9) · [인물별 평균·길이 대응 사례·민감도 전체 계산](analysis.json)"])
    return "\n\n".join(parts) + "\n"


def self_check():
    import random
    rng=random.Random(20261121)
    assert close_length(8,10) and not close_length(7,10) and not close_length(0,0)
    # Person-first and topic-first must differ on an unbalanced eligible subset.
    ds={("A","happy"):1,("A","proud"):3,("B","happy"):1,("A","compassion"):3}
    assert math.isclose(cell_means(ds,ds)[0],(7/3+1)/2)
    assert math.isclose(cell_means(ds,ds,topic_first=True)[0],7/3)
    for which in ("D","S"):
        ref=[1.5,2.0,2.5]
        for k in range(6):
            a=[v+rng.uniform(-.009,.009) for v in ref]
            b=[v+rng.uniform(-.009,.009) for v in ref]
            low,high=rounding_difference(a,b,ref,which)
            for offs in product([-.005,-.0025,0,.0025,.005],repeat=3):
                y=[v+d for v,d in zip(ref,offs)]
                gap=distance(b,y,which)-distance(a,y,which)
                assert low-EPS<=gap<=high+EPS
        zero=rounding_difference(ref,ref,ref,which)
        assert max(abs(v) for v in zero)<EPS
    # A rounded D comparison can cross zero at the interior as well as at a box face.
    assert rounding_difference([2,2,2],[2.003,2,2],[2,2,2],"D")[0] < 0
    assert abs(distance([2.4,2.4,2.4],[2,2,2],"S")) < EPS
    assert abs(distance([2.4,2.4,2.4],[2,2,2],"D")-.4) < EPS
    print("Offline arithmetic checks passed.")


def dump_immutable(path, text):
    if path.exists():
        if path.read_text() != text:
            raise ValueError(f"Existing output differs: {path.name}")
    else:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(text)
        tmp.replace(path)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check",action="store_true")
    opts=parser.parse_args()
    self_check()
    if not opts.self_check:
        key, scores = HERE/"private/key.json", HERE/"scores.json"
        out=analyze(json.loads(key.read_text()),json.loads(scores.read_text()))
        out["source_sha256"]={p.name:sha256(p.read_bytes()).hexdigest() for p in
                              (key,scores,Path(__file__),HERE.parent/"DESIGN.ko.md")}
        dump_immutable(HERE/"analysis.json",json.dumps(out,indent=2,ensure_ascii=False,allow_nan=False)+"\n")
        dump_immutable(HERE/"tables.md",report(out))
        print(json.dumps(out["conclusions"],ensure_ascii=False))
