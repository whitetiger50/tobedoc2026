"""Join frozen sources to retrospective evidence spans. No inference or scoring client."""
from collections import Counter
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import random
from statistics import median


HERE = Path(__file__).resolve().parent
MAIN = HERE.parent
STUDY = MAIN.parent
ARMS = {"developed": "개발판", "base": "기본 모델", "short": "단답 대조"}
TOPICS = dict(zip(
    "happy compassion proud sad afraid embarrassed disgusted directions morning meal".split(),
    "기쁨 연민 자부심 슬픔 두려움 당혹감 혐오 길안내 아침일과 마지막식사".split()))
READERS = {"opus": "Opus", "gpt": "GPT"}
STATUS = {"E": "반영", "P": "일부 반영", "N": "확인되지 않음"}


def load(path):
    return json.loads(path.read_text())


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def evidence(panel, row, key, blind, score, tally):
    uid = row["uid"]
    answer = blind[uid]["answer"]
    trace = panel[uid]
    slots = trace["slots"]
    assert len(slots) == 2
    codes = []
    for item in slots:
        code, quote = item["code"], item["quote"]
        assert code in STATUS and ((code == "N" and not quote) or (code != "N" and quote and quote in answer))
        codes.append(code)
        tally[code] += 1
    tally["both_E"] += codes == ["E", "E"]
    tally["at_least_one_E"] += "E" in codes
    tally["n"] += 1
    reasons = {}
    for reader in READERS:
        record = score[uid, reader]
        quote = trace[reader + "_quote"]
        assert record["status"] == "rated"
        assert not quote or any(quote in e["elaboration_reason"] for e in record["events"])
        tally[reader + "_specific"] += bool(quote)
        reasons[reader] = record
    return {"uid": uid, "answer": answer, "words": key[uid]["words"], "slots": slots,
            "opus_quote": trace["opus_quote"], "gpt_quote": trace["gpt_quote"], "reasons": reasons}


def collect():
    sources = [MAIN/"private/key.json", MAIN/"blind.json", MAIN/"scores.json", STUDY/"cards/cards.json",
               STUDY/"DESIGN.ko.md", STUDY/"boundary/calibrate.py"]
    key = {x["uid"]: x for x in load(sources[0])}
    blind = {x["uid"]: x for x in load(sources[1])}
    score = {(x["uid"], x["reader"]): x for x in load(sources[2])}
    cards = {x["id"]: x for x in load(sources[3])}
    assert digest(sources[0]) == load(MAIN/"generation-verification.json")["private_key_sha256"]
    assert digest(sources[1]) == load(MAIN/"reader-verification.json")["blind_sha256"]
    assert digest(sources[2]) == load(MAIN/"reader-verification.json")["scores_sha256"]
    assert digest(sources[3]) == "d48e6793c80023526b4fac3ef3ccd25256fcd022d712ee21e296575c943ba06a"
    frozen = load(STUDY/"boundary/freeze.json")["sha256"]
    assert all(digest(p) == frozen[str(p.relative_to(STUDY.parent))] for p in sources[4:])
    traces = load(HERE/"evidence.json")
    panel = {x["uid"]: x for x in traces}
    assert len(traces) == len(panel) == len(blind) == len(key) == 360 and set(blind) == set(panel) == set(key)
    assert len(score) == 720
    groups, tallies = {}, {arm: Counter() for arm in ARMS}
    for uid,row in key.items():
        cid, t, arm = row["case"], row["topic"], row["arm"]
        group = groups.setdefault((cid,t), {"case":cid, "topic":t, "question":blind[uid]["question"],
            "anchor":cards[cid]["anchor"], "facts":cards[cid]["items"][t], "arms":{}})
        assert group["question"] == blind[uid]["question"] and arm not in group["arms"]
        group["arms"][arm] = evidence(panel, row, key, blind, score, tallies[arm])
    assert len(groups) == 120 and all(set(gr["arms"]) == set(ARMS) for gr in groups.values())
    counts, length = Counter(), {}
    for gr in groups.values():
        w = {arm: gr["arms"][arm]["words"] for arm in ARMS}
        length[gr["case"]+"-"+gr["topic"]] = w
        counts["base_longer_than_short"] += w["base"] > w["short"]
        counts["base_longer_than_developed_longer_than_short"] += w["base"] > w["developed"] > w["short"]
        counts["three_arm_lengths_at_least_80pct"] += 5*min(w.values()) >= 4*max(w.values())
    sample = list(sorted(cards))
    random.Random("GK-floor-descriptive-v1-topic-sample").shuffle(sample)
    verification_sample = []
    for topic,cid in zip(TOPICS,sample):
        verification_sample += [gr for gr in groups[cid,topic]["arms"].values()]
    return groups, {"n_triplets":len(groups), "n_answers":len(key), "n_frozen_readings":len(score),
        "by_arm":tallies, "all":sum(tallies.values(), Counter()), "length":counts,
        "median_paired_base_minus_short_words":median(w["base"]-w["short"] for w in length.values()),
        "three_arm_length_matched_triplets":[k for k,w in length.items() if 5*min(w.values())>=4*max(w.values())],
        "largest_base_short_gap":max(length, key=lambda k:length[k]["base"]-length[k]["short"]),
        "spotcheck_30": dict(Counter(s["code"] for row in verification_sample for s in row["slots"])),
        "source_hashes":{str(p.relative_to(STUDY)):digest(p) for p in sources}, "evidence_sha256":digest(HERE/"evidence.json")}


def render_arm(arm, item):
    out = [f'<article><h3>{ARMS[arm]} <small>{item["words"]}단어</small></h3>',
           f'<div class="quoted" lang="en">{escape(item["answer"].strip())}</div><h4>카드와 겹치는 표현</h4>']
    for i,s in enumerate(item["slots"], 1):
        out.append(f'<p><strong>세부 {i} · {STATUS[s["code"]]}</strong><br><span lang="en">{escape(s["quote"])}</span></p>')
    for rid, label in READERS.items():
        r = item["reasons"][rid]
        out.append(f'<details><summary>{label} · 전개 {r["elaboration"]:g} / 명료도 {r["meaning_clarity"]:g}</summary>')
        for n,e in enumerate(r["events"], 1):
            if len(r["events"])>1: out.append(f'<h4>사건 {n}</h4>')
            out.append(f'<p><strong>전개 {e["elaboration"]}</strong><br>{escape(e["elaboration_reason"])}</p>')
            out.append(f'<p><strong>명료도 {e["meaning_clarity"]}</strong><br>{escape(e["meaning_clarity_reason"])}</p>')
        out.append('</details>')
    out.append('</article>')
    return ''.join(out)


def html(groups):
    cards = sorted({i for i,t in groups})
    case_options = ''.join(f'<option>{cid}</option>' for cid in cards)
    topic_options = ''.join(f'<option value="{t}">{label}</option>' for t,label in TOPICS.items())
    panels = []
    for cid in cards:
        for t,label in TOPICS.items():
            gr = groups[cid,t]
            facts = ''.join(f'<li><b>{f}</b> {escape(v)}</li>' for f,v in zip(("중심 사실","세부 1","세부 2"),gr["facts"]))
            anchor = 'id="'+cid+'-'+t+'"'
            panels.append(f'<section {anchor} class="panel" data-case="{cid}" data-topic="{t}"><h2>{cid} · {label}</h2>'
                f'<p class="question" lang="en">{escape(gr["question"])}</p><p><b>배경</b> {escape(gr["anchor"])}</p>'
                f'<ul class="facts">{facts}</ul><div class="cols">'+''.join(render_arm(a, gr["arms"][a]) for a in ARMS)+'</div></section>')
    template = (HERE/"viewer.html.in").read_text()
    return template.replace("{{CASES}}",case_options).replace("{{TOPICS}}",topic_options).replace("{{PANELS}}","\n".join(panels))


if __name__ == "__main__":
    groups, summary = collect()
    (HERE/"summary.json").write_text(json.dumps(summary, indent=2,ensure_ascii=False)+"\n")
    (HERE/"compare.html").write_text(html(groups))
