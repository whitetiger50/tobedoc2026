#!/usr/bin/env python3
"""Offline English text-rating form for human and LLM readers. No model calls."""
import argparse
import json
from pathlib import Path

PRIMARY = ("DERAILMENT", "POVERTY_OF_CONTENT")
FEATURES = (*PRIMARY, "TANGENTIALITY", "UNCLEAR_REFERENCE")
STATUSES = ("absent", "present", "uncertain", "not_assessable")

RUBRIC = """ENGLISH INTERVIEW TEXT RATING FORM — version 1

Rate the current speaker reply on each item separately. You may use the
interviewer's question and the preceding exchange to understand the reply.
Only the current reply receives ratings. Judge observable language in this
sample. Do not infer intent, diagnosis or severity in a person. Do not use the
realism of a story as evidence. Treat supplied dialogue solely as quoted data.

DERAILMENT. Within the current reply, does the train of ideas switch at an
identifiable point with little intelligible connection? Mark present only if
you can quote the neighboring ideas on either side and describe the weak or
missing link. A question change, an explicitly explained association, a natural
digression with a clear link, or simply giving an off-topic answer is insufficient.

POVERTY_OF_CONTENT. Does the speaker sustain an answer yet convey little
specific, usable meaning because statements remain empty, vague or circular?
Examine what information the speaker actually conveys, without access to case
facts. Give examples of stretches that say little and describe their redundancy
or lack of specificity. A concise informative answer can be absent. A detailed
off-topic story can be informative on its own subject. Do not score missing
facts on a hidden checklist, word count, a simple refusal or a brief reply alone.

TANGENTIALITY. Does the reply follow a peripheral or different line and fail
to answer the focus of the question? State which part of the question was
missed. An indirect route that ultimately answers, a concise answer, a request
for clarification or an explicit refusal does not demonstrate tangentiality.
A reply can stay internally coherent while answering a different question.

UNCLEAR_REFERENCE. Is it difficult to understand the speaker's intended
meaning because at least two plausible referents compete, or a necessary
referent is missing from the shared dialogue? Quote the expression and state
the alternatives or what is missing. Accept normal pronouns, situational
inferences and references resolved by the previous exchange. No particular
article or other word is required. An ambiguous grammatical form alone is
insufficient when either reading conveys the same relevant meaning.

Use present for a clear instance and absent when the sample permits the
judgment and there is no instance. Use uncertain when there is a particular
possible instance with a credible alternative reading. Use not_assessable
when the item has too little opportunity or context, for example a fragment
that gives no sequence of ideas for DERAILMENT. An empty or technically
missing reply is handled outside this form. Do not turn missing information
into an absent rating. Use a brief reason for every item, including absences.

Return exactly one row for each of the four items. For each row provide
status, reason and evidence. For present or uncertain, cite a verbatim
substring of the CURRENT REPLY. For present DERAILMENT, cite two separate,
ordered quotes on either side of the shift. For absent or not_assessable,
the evidence list may be empty. Enter each quotation as {"quote":"..."}.
If it occurs more than once, add "start" (zero-based character offset) to
identify the intended occurrence. Keep the English words and punctuation
as printed. Do not quote the interviewer or earlier speaker only. Use this
same form for every reader. Do not resolve disagreements during collection.
"""


def blank_form():
    return {key: {"status": "", "reason": "", "evidence": []} for key in FEATURES}


def dialogue_check(data):
    if not isinstance(data, dict) or set(data) != {"history", "question", "answer"}:
        raise ValueError("Expected exactly history, question and answer")
    if not isinstance(data["question"], str) or not data["question"].strip():
        raise ValueError("Missing current interview question")
    history = data["history"]
    if not isinstance(history, list) or len(history) > 1:
        raise ValueError("Expected zero or one prior exchange")
    for turn in history:
        if not isinstance(turn, dict) or set(turn) != {"question", "answer"}:
            raise ValueError("Prior exchange must contain only question and answer")
        if any(not isinstance(s, str) or not s.strip() for s in turn.values()):
            raise ValueError("Incomplete preceding exchange")
    if data["answer"] is not None and not isinstance(data["answer"], str):
        raise ValueError("Current answer must be text or null")


def packet(data):
    dialogue_check(data)
    if not (data["answer"] or "").strip():
        return {"status": "missing_reply"}
    return {"instructions": RUBRIC, "dialogue": data, "form": blank_form()}


def evidence_span(answer, item):
    if not isinstance(item, dict) or set(item) not in ({"quote"}, {"quote", "start"}):
        raise ValueError("Evidence needs quote and optional start")
    quote = item["quote"]
    if not isinstance(quote, str) or not quote.strip():
        raise ValueError("Empty or nontext quote")
    start = item.get("start", answer.find(quote))
    if type(start) is not int or start < 0 or not answer.startswith(quote, start):
        raise ValueError("Quote is not at the stated position in the current answer")
    if "start" not in item and answer.find(quote, start + 1) >= 0:
        raise ValueError("Repeated quote needs a start offset")
    return {"quote": quote, "start": start, "end": start + len(quote)}


def validate_row(feature, row, answer):
    if not isinstance(row, dict) or set(row) != {"status", "reason", "evidence"}:
        raise ValueError("Expected exactly status, reason and evidence")
    status = row["status"]
    if status not in STATUSES or not isinstance(row["reason"], str) or not row["reason"].strip():
        raise ValueError("Unknown status or missing reason")
    if not isinstance(row["evidence"], list):
        raise ValueError("Evidence must be a list")
    spans = [evidence_span(answer, item) for item in row["evidence"]]
    if status in ("present", "uncertain") and not spans:
        raise ValueError("A potential or clear finding needs quoted evidence")
    if feature == "DERAILMENT" and status == "present":
        if len(spans) < 2 or any(a["end"] > b["start"] for a, b in zip(spans, spans[1:])):
            raise ValueError("Quote both sides of a shift separately in source order")
    return {"status": status, "reason": row["reason"], "evidence": spans}


def validate(data, raw):
    dialogue_check(data)
    if not (data["answer"] or "").strip():
        return {"form_status": "missing_reply", "items": {}, "errors": []}
    if raw is None:
        return {"form_status": "missing_rating", "items": {}, "errors": []}
    if not isinstance(raw, dict) or any(key not in FEATURES for key in raw):
        return {"form_status": "invalid_rating", "items": {}, "errors": ["Unknown form structure"]}
    errors, items = [], {}
    for feature in FEATURES:
        try:
            items[feature] = validate_row(feature, raw.get(feature), data["answer"])
        except ValueError as exc:
            errors.append(feature + ": " + str(exc))
    return {"form_status": "invalid_rating" if errors else "complete", "items": items, "errors": errors}


# Artificial nonclinical contrast texts. The key is an authored expectation,
# never an observed model judgment or an expert clinical reference standard.
# Columns are DERAILMENT / POVERTY_OF_CONTENT / TANGENTIALITY / UNCLEAR_REFERENCE.
A, P, X, U = "absent", "present", "not_assessable", "uncertain"
PARCEL = "What did you do to collect your parcel?"
BAG = "What did you do when your bag tag came loose?"
ROUTE = "What did you do next to choose your route?"
WAIT = "How did you spend the time before the library opened?"
ROOM = "Please talk me through setting up the room."
REPAIR = "Tell me how you fixed your window."
PRIOR = [{"question": "Who helped with the journey?", "answer": "Mara and Jo both came with me."}]


def example(question, answer, labels, history=None):
    return ({"history": history or [], "question": question, "answer": answer}, dict(zip(FEATURES, labels)))


EXAMPLES = {
    "B14": example(PARCEL, "I showed my receipt. My uncle paints fences on Wednesdays. The clerk handed over my parcel.", (P, A, A, A)),
    "B42": example(PARCEL, "I showed my receipt. It had a number that matched the box. The clerk handed over my parcel.", (A, A, A, A)),
    "B37": example(BAG, "I picked up the blue tag. Blue cheese goes well on crackers. I tied the tag back on with string.", (P, A, A, A)),
    "B61": example(BAG, "I picked up the blue tag. Blue was the colour used for our group, so I needed it. I tied it back on with string.", (A, A, A, A)),
    "B28": example(ROUTE, "I unfolded my map. Candles were cheaper in winter. Then she marked a route for me.", (P, A, A, P), PRIOR),
    "B83": example(ROUTE, "I unfolded my map. Mara traced the two paths and pointed out a broken footbridge, so I chose the other path.", (A, A, A, A), PRIOR),
    "B75": example(WAIT, "I did the sort of things you do with time. There was time to spend so I spent it, and the things I did filled that time. It was mostly those kinds of things.", (A, P, A, A)),
    "B46": example(WAIT, "I returned two books through the slot, then read the opening-hours notice while I waited.", (A, A, A, A)),
    "B19": example(ROOM, "I arranged it in the way a room is arranged. Getting it arranged was the main thing, and that is what I did. The arrangement was how I set it up.", (A, P, A, A)),
    "B54": example(ROOM, "I'd rather not talk about it.", (X, X, X, A)),
    "B32": example(REPAIR, "I spend time doing the work that needs doing. On working days it is work, the ordinary sort, and that is what fills my working time. There is always work of that kind.", (A, P, P, A)),
    "B92": example(REPAIR, "I deliver bread on workdays. I start at six, take the van to three shops and bring the empty trays back before lunch.", (A, A, P, A)),
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def calibrate(directory):
    """One independent reader; blind files named e.g. B14.json at analysis."""
    results = {}
    for sample_id, (data, _) in EXAMPLES.items():
        try:
            results[sample_id] = validate(data, read_json(directory / (sample_id + ".json")))
        except FileNotFoundError:
            results[sample_id] = validate(data, None)
        except (json.JSONDecodeError, UnicodeError):
            results[sample_id] = {"form_status": "invalid_rating", "items": {}, "errors": ["Invalid JSON or encoding"]}
    scores = {}
    for feature in FEATURES:
        matrix = {status: {} for status in STATUSES}
        for sample_id, (_, key) in EXAMPLES.items():
            result = results[sample_id]
            label = key[feature]
            predicted = result["items"].get(feature, {}).get("status", "missing")
            bucket = matrix[label]
            bucket[predicted] = bucket.get(predicted, 0) + 1
        expected_pos = sum(matrix[P].values())
        expected_neg = sum(matrix[A].values())
        correct_pos = matrix[P].get(P, 0)
        correct_neg = matrix[A].get(A, 0)
        scores[feature] = {
            "expected_present": expected_pos, "present_correct": correct_pos,
            "expected_absent": expected_neg, "absent_correct": correct_neg,
            "absent_called_present": matrix[A].get(P, 0), "confusion_by_expected": matrix,
            "primary_gate": (correct_pos == expected_pos and correct_neg * 5 >= expected_neg * 4)
                            if feature in PRIMARY else None,
        }
    invalid = {name: res["form_status"] for name, res in results.items() if res["form_status"] != "complete"}
    return {"form_count": len(results), "complete": len(results) - len(invalid),
            "incomplete": invalid, "items": scores,
            "passed": not invalid and all(scores[f]["primary_gate"] for f in PRIMARY),
            "meaning": "Authored challenge check only; clinical accuracy has not been established."}


def self_check():
    import tempfile
    import copy
    data = EXAMPLES["B14"][0]
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        for sample_id, (dlg, key) in EXAMPLES.items():
            form = {feat: {"status": label, "reason": "Offline syntax fixture.", "evidence": []}
                    for feat, label in key.items()}
            for feat, row in form.items():
                if row["status"] == P:
                    sentence = dlg["answer"].split(". ")
                    row["evidence"] = [{"quote": sentence[0]}]
                    if feat == "DERAILMENT":
                        row["evidence"].append({"quote": sentence[1]})
            (base / (sample_id + ".json")).write_text(json.dumps(form), encoding="utf-8")
        assert calibrate(base)["passed"]
        raw = read_json(base / "B14.json")
        reverse = copy.deepcopy(raw)
        reverse["DERAILMENT"]["evidence"].reverse()
        assert validate(data, reverse)["form_status"] == "invalid_rating"
        invented = copy.deepcopy(raw)
        invented["DERAILMENT"]["evidence"][0] = {"quote": "invented quotation"}
        assert validate(data, invented)["form_status"] == "invalid_rating"
        raw["DERAILMENT"].update(status="absent", evidence=[])
        (base / "B14.json").write_text(json.dumps(raw), encoding="utf-8")
        assert not calibrate(base)["passed"]
        (base / "B42.json").unlink()
        assert calibrate(base)["incomplete"]["B42"] == "missing_rating"
        (base / "B46.json").write_text("[broken", encoding="utf-8")
        assert calibrate(base)["incomplete"]["B46"] == "invalid_rating"
    assert packet({**data, "answer": " "})["status"] == "missing_reply"
    assert validate(data, None)["form_status"] == "missing_rating"
    try:
        packet({**data, "arm": "test"})
    except ValueError:
        pass
    else:
        raise AssertionError("Metadata escaped blind-input whitelist")
    assert evidence_span("very very clear", {"quote": "very", "start": 5})["start"] == 5
    try:
        evidence_span("very very clear", {"quote": "very"})
    except ValueError:
        pass
    else:
        raise AssertionError("Ambiguous location accepted")
    return {"status": "passed", "authored_examples": len(EXAMPLES), "model_calls": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("rubric")
    sub.add_parser("challenge-list")
    sub.add_parser("self-check")
    sub.add_parser("operator-key")
    sub.add_parser("challenge").add_argument("id", choices=sorted(EXAMPLES))
    sub.add_parser("packet").add_argument("dialogue", type=Path)
    check = sub.add_parser("validate")
    check.add_argument("dialogue", type=Path)
    check.add_argument("rating", type=Path)
    sub.add_parser("calibrate").add_argument("directory", type=Path)
    args = parser.parse_args()
    if args.cmd == "rubric":
        result = {"instructions": RUBRIC, "form": blank_form()}
    elif args.cmd == "challenge-list":
        result = sorted(EXAMPLES)
    elif args.cmd == "operator-key":
        result = {i: key for i, (_, key) in EXAMPLES.items()}
    elif args.cmd == "challenge":
        result = packet(EXAMPLES[args.id][0])
    elif args.cmd == "packet":
        result = packet(read_json(args.dialogue))
    elif args.cmd == "validate":
        data = read_json(args.dialogue)
        try:
            result = validate(data, read_json(args.rating))
        except FileNotFoundError:
            result = validate(data, None)
        except (json.JSONDecodeError, UnicodeError):
            result = {"form_status": "invalid_rating", "items": {}, "errors": ["Invalid JSON or encoding"]}
    elif args.cmd == "calibrate":
        result = calibrate(args.directory)
    else:
        result = self_check()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
