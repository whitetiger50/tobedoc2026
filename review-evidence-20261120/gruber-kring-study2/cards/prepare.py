"""Prepare and verify hypothetical inputs locally. This module has no model client."""
from collections import Counter
import csv
from hashlib import sha256
import json
from pathlib import Path
import random
import re
from statistics import mean
import sys
import unicodedata

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
EVIDENCE = STUDY.parent
ROOT = EVIDENCE.parent
PROFILE = ROOT / "tobedoc2026/docs/2026-11-20-english-clinical-profile"
SOURCE = ROOT / "persona-audit-20261120T072413385108Z"
sys.path.insert(0, str(PROFILE))
import generation as builder
import study as legacy

TOPICS = {
    "happy": "기쁨", "compassion": "연민", "proud": "자부심",
    "sad": "슬픔", "afraid": "두려움", "embarrassed": "당혹감", "disgusted": "혐오",
    "directions": "길 안내", "morning": "아침 일과", "meal": "마지막 식사",
}
SEED = "GK-study2-cards-v1"
ARMS = ("developed", "base", "short")
SHORT = "Keep your reply brief and vague."
WORD = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)*")
CUE = re.compile(r"\b(?:brief(?:ly)?|vague(?:ly)?|concise(?:ly)?|elaborat(?:e|ion)|word count|"
                 r"short answer|long answer|answer length|respond|speak|referent|unclear|disorgani[sz]ed|"
                 r"incoheren\w*|score|rubric|diagnos\w*|schizophren\w*|hallucinat\w*|delusion\w*|"
                 r"one sentence|few words|be clear|in detail|lengthy|verbosity)\b", re.I)


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def words(s):
    folded = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return [v.lower().replace("’", "'") for v in WORD.findall(folded)]


def script():
    design = (STUDY / "DESIGN.ko.md").read_text()
    intro, = re.findall(r"^\*\*공통 안내\.\*\* “([^”]+)”", design, re.M)
    rows = re.findall(r"^\| (긍정|부정|중립) · ([^|]+?) \| ([^|]+?\?) \|$", design, re.M)
    assert len(rows) == 10 and [r[1] for r in rows] == list(TOPICS.values())
    return intro, {k: (valence, q) for k, (valence, _, q) in zip(TOPICS, rows)}


def assignments(ids):
    profiles = {}
    for block, extra in enumerate(legacy.PROFILES):
        group = [*legacy.PROFILES, extra]
        random.Random(f"{SEED}/profile/{block}").shuffle(group)
        profiles.update(zip(ids[4*block:4*block+4], group))
    reverse = {}
    for topic in TOPICS:
        order = ids.copy()
        random.Random(f"{SEED}/supporting-facts/{topic}").shuffle(order)
        reverse[topic] = set(order[:6])
    return profiles, reverse


def packet_for(card, topic, profile, reverse_details, current_question, arm):
    """Reconstruct one local packet. Only its messages are eventual model input."""
    if arm not in ARMS:
        raise ValueError(arm)
    communication = legacy.case_input("C01", profile)["communication"]
    communication.update(spontaneity="You are willing to speak freely about familiar subjects.",
                         guardedness="You are comfortable sharing these ordinary experiences.")
    core, first, second = card["items"][topic]
    notes = [core, second, first] if reverse_details else [core, first, second]
    facts = [{"id": f"F{i}", "kind": "background", "content": note, "patient_knows": True,
              "disclosure": "on_topic"} for i, note in enumerate(notes, 1)]
    dto = {"patient": {"case_id": card["id"], "partition": "development",
                       "provenance": "independently_authored_fictional_english_case",
                       "facts": facts, "self_understanding": card["anchor"]},
           "communication": communication}
    condition = "development_v02" if arm == "developed" else "role_only_ablation"
    system, user = builder.render(SOURCE, dto, [], current_question, condition, {})["messages"]
    if arm == "short":
        system = {**system, "content": system["content"].rstrip("\n") + "\n\n" + SHORT + "\n"}
    return [system, user]


def reference_texts():
    refs = {}
    for folder, name in (("dais-generator-20261121", "cards"), ("first-turn-revision-proposal", "proposed-cards")):
        old = read(EVIDENCE / folder / (name + ".json"))
        refs[folder] = [(c["id"], " ".join([*c["facts"], c["self_understanding"]])) for c in old]
    refs["prior_english_cases"] = [(k, " ".join(case[1])) for k, case in legacy.CASES.items()]
    for folder in ("boundary", "clarity-retest"):
        refs[folder] = [(k, v["answer"]) for k, v in read(STUDY / folder / "examples.json").items()]
    return refs


def overlap(cards):
    refs = reference_texts()
    notes = [(c["id"], s) for c in cards for s in [c["anchor"], *(n for v in c["items"].values() for n in v)]]
    hits = []
    for label, entries in refs.items():
        prior = [(k, " " + " ".join(words(v)) + " ") for k, v in entries]
        for cid, note in notes:
            tokens = words(note)
            # Full short notes (>=4 words) and any six consecutive words of longer notes.
            if len(tokens) < 4:
                continue
            width = min(len(tokens), 6)
            spans = {" " + " ".join(tokens[i:i+width]) + " " for i in range(len(tokens)-width+1)}
            for old_id, text in prior:
                if any(span in text for span in spans):
                    hits.append([cid, note, label, old_id])
    roster = SOURCE / "share/PATIENTSIM-reliability-pilot-v01/analysis_key_DO_NOT_SHOW_JUDGES.csv"
    with roster.open(encoding="utf-8-sig", newline="") as f:
        reserved_ids = {row["case_id"] for row in csv.DictReader(f)}
    assert len(reserved_ids) == 12 and reserved_ids.isdisjoint(c["id"] for c in cards)
    return {"reference_counts": {k: len(v) for k, v in refs.items()}, "phrase_matches": hits,
            "reserved_case_ids_checked": len(reserved_ids), "reserved_id_matches": 0,
            "reserved_content_semantically_compared": False}


def stats(values):
    return {"n": len(values), "min": min(values), "mean": round(mean(values), 2), "max": max(values)}


def build():
    cards = read(HERE / "cards.json")
    ids = [c["id"] for c in cards]
    assert ids == [f"GK{i:02}" for i in range(1, 13)]
    assert len({c["anchor"] for c in cards}) == len(ids)
    intro, questions = script()
    profiles, swaps = assignments(ids)
    assert Counter(profiles.values()) == dict.fromkeys(legacy.PROFILES, 4)
    old_freeze = read(EVIDENCE / "dais-generator-20261121/freeze.json")
    assert digest(PROFILE / "generation.py") == old_freeze["builder_sha256"]
    prior_calibration = read(STUDY / "boundary/freeze.json")["sha256"]
    for rel, expected in prior_calibration.items():
        assert digest(EVIDENCE / rel) == expected
    lengths = {k: [] for k in TOPICS}
    rows, inputs, systems, note_texts = [], set(), {}, []
    for c in cards:
        assert set(c) == {"id", "anchor", "items"} and set(c["items"]) == set(TOPICS)
        cid = c["id"]
        assert not CUE.search(c["anchor"])
        for k, (_, q) in questions.items():
            facts = c["items"][k]
            assert len(facts) == len(set(facts)) == 3
            for s in facts:
                assert isinstance(s, str) and s.strip() == s and words(s)
                assert not CUE.search(s) and not re.search(r"\b(?:I|we|my|our)\b|[!?“”\"]", s, re.I)
            note_texts.extend(facts)
            count = sum(len(words(s)) for s in facts)
            lengths[k].append(count)
            swap = cid in swaps[k]
            question = intro + "\n\n" + q
            triple = {}
            bodies = []
            for arm in ARMS:
                sysmsg, payload = packet_for(c, k, profiles[cid], swap, question, arm)
                assert sysmsg["role"] == "system" and payload["role"] == "user"
                syshash = builder.sha(sysmsg["content"].encode())
                assert syshash == old_freeze["system_sha256"][arm]
                systems[arm] = syshash
                body = payload["content"]
                obj = json.loads(body)
                assert obj["history"] == [] and obj["current_question"] == question
                assert obj["patient"]["self_understanding"] == c["anchor"]
                assert [f["content"] for f in obj["patient"]["facts"]] == [facts[i] for i in ((0,2,1) if swap else (0,1,2))]
                bodies.append(body.encode("utf-8"))
                triple[arm] = builder.sha(builder.canonical([sysmsg, payload]))
            assert bodies[0] == bodies[1] == bodies[2]
            userhash = builder.sha(bodies[0])
            inputs.add(userhash)
            rows.append({"id": cid, "topic": k, "profile": profiles[cid], "reverse_details": swap,
                         "word_count": count, "numeric_tokens": len(re.findall(r"\b\d+\b", " ".join(facts))),
                         "user_sha256_all_three": userhash, "messages_sha256": triple})
    assert len(rows) == len(inputs) == 120
    assert len({v for r in rows for v in r["messages_sha256"].values()}) == 360
    by_group = {v: stats([n for k, (g, _) in questions.items() if g == v for n in lengths[k]])
                for v in ("긍정", "부정", "중립")}
    paths = [HERE / "cards.json", Path(__file__), STUDY / "DESIGN.ko.md", PROFILE / "generation.py",
             PROFILE / "study.py", EVIDENCE / "dais-generator-20261121/freeze.json",
             STUDY / "boundary/calibrate.py", STUDY / "clarity-retest/freeze.json"]
    audit = {"seed": SEED, "cases": len(cards), "items": len(rows), "fact_slots": len(note_texts),
             "unique_note_strings": len(set(" ".join(words(n)) for n in note_texts)),
             "anchors_word_counts": stats([len(words(c["anchor"])) for c in cards]),
             "three_way_equal_user_bodies": len(inputs), "distinct_prepared_packets": len(rows)*len(ARMS),
             "by_topic_words": {k: stats(l) for k, l in lengths.items()}, "by_category_words": by_group,
             "category_words_plus_numbers": {
                 v: stats([r["word_count"] + r["numeric_tokens"] for r in rows if questions[r["topic"]][0] == v])
                 for v in by_group},
             "by_card_words": {i: stats([r["word_count"] for r in rows if r["id"] == i]) for i in ids},
             "by_profile_words": {p: stats([r["word_count"] for r in rows if r["profile"] == p]) for p in legacy.PROFILES},
             "profile_cases": profiles, "fixed_fact_slot_count_per_item": 3,
             "style_cue_pattern_hits": 0, "prior_overlap": overlap(cards), "system_sha256": systems,
             "source_sha256": {str(p.relative_to(ROOT)): digest(p) for p in paths}, "entries": rows}
    for k in TOPICS:
        assert sum(r["reverse_details"] for r in rows if r["topic"] == k) == 6
    book = ["# Gruber–Kring 영어 가상 사례 카드 12장", "",
            "각 카드의 배경 한 줄은 열 문항에 공통이다. 각 면담에는 해당 문항의 사실 세 개만 전달한다. 아래 열 이름과 한국어 문항 표시는 연구팀 열람용이다. 실제 입력에서는 중심 사실을 먼저 두고 두 세부 사실의 순서는 문항마다 인물 절반에서 바꾼다.", ""]
    for c in cards:
        book += ["## " + c["id"], "", c["anchor"], "",
                 "| 문항 | 중심 사실 | 세부 사실 1 | 세부 사실 2 |", "|---|---|---|---|"]
        book += ["| " + " | ".join([name, *c["items"][k]]) + " |" for k, name in TOPICS.items()]
        book += [""]
    return {"audit.json": json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
            "CARDS.ko.md": "\n".join(book)}


if __name__ == "__main__":
    if sys.argv[1:] not in (["build"], ["verify"]):
        raise SystemExit("Use build to create local materials or verify to compare them offline.")
    for name, content in build().items():
        path = HERE / name
        if sys.argv[1] == "build" and not path.exists():
            with path.open("x") as f:
                f.write(content)
        elif path.read_text() != content:
            raise ValueError("Stored materials differ: " + name)
    print("12 cards, 120 question-specific inputs, 360 prepared packets verified locally.")
