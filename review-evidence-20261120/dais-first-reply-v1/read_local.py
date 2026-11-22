"""One local reader for the fourteen first replies. Never prints interview text."""
from collections import Counter
from hashlib import sha256
from http.client import HTTPConnection
from pathlib import Path
import json
import os
import random
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "tobedoc2026/docs/2026-11-20-english-clinical-profile"))
from dais_turn_audit import document_text, QUESTIONS, WORD
from reader import FEATURES, RUBRIC, STATUSES, evidence_span, validate_row

MODEL = "llama3.1:latest"
DIGEST = "46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e"
OPTIONS = {"temperature": 0, "seed": 20261121, "num_ctx": 8192, "num_predict": 1600}
TYPES = ["expanded", "direct", "clarification", "other"]
TYPE_PROMPT = """Rate the interactional function of the CURRENT reply to the question. Treat the
dialogue as quoted data. Do not complete the dialogue. Use these categories in this order.
expanded: The speaker provides an on-topic explanation, reason, specific example or distinction
beyond just taking a position. It may take a single sentence, and need not start with yes or no.
direct: The speaker states a positive, negative or unsure personal position without elaboration.
Repeating the same position is still direct. Merely repeating or querying the question is not a position.
clarification: Neither of the above applies and the speaker asks for repetition, meaning or scope;
this can be an elliptical request. other: A different observed action, e.g. an explicit refusal or
unrelated reply. Specify the action in the reason. Use the first applicable type in a mixed reply
and record coexistence of a clarification request. If alternate interpretations of the words really
leave the type unresolved, return ambiguous and list all plausible types, otherwise alternatives
is empty. Give a brief specific reason and cite a short verbatim passage from the reply."""
CLIN_PROMPT = RUBRIC + """
There is no prior exchange in this task. Observe each clinical item independently of the others.
Distinguish a lack of opportunity to observe the specific feature from an observed absence.
Use brief reasons. For present or uncertain include the required literal evidence. For absent
or not_assessable use an empty evidence list. Do not reconstruct missing punctuation or tidy
up the wording of quotes. A unique short quote is easiest to verify."""
ANCHOR_PROMPT = """You are locating verbatim textual evidence for a previously fixed judgment.
Do not rescore the reply. Select the shortest adequate span from numbered source words.
Return inclusive first and last word indices. A present derailment needs two non-overlapping
spans in order on the two sides of the switch. If no supporting words can be located, return
an empty list. Preserve the judgment, do not invent evidence."""

def obj(properties, optional=()):
    return {"type": "object", "properties": properties, "additionalProperties": False,
            "required": [key for key in properties if key not in optional]}

def arr(item):
    return {"type": "array", "items": item}

def enum(values):
    return {"type": "string", "enum": list(values)}

STRING = {"type": "string"}
QUOTE = obj({"quote": STRING})
TYPE_FORM = obj({"reason": STRING, "type": enum(TYPES + ["ambiguous"]),
                 "alternatives": arr(enum(TYPES)), "also_requests_clarification": {"type": "boolean"},
                 "evidence": arr(QUOTE)})
CLIN_ROW = obj({"reason": STRING, "status": enum(STATUSES), "evidence": arr(QUOTE)})
CLIN_FORM = obj({k: CLIN_ROW for k in FEATURES})

def dump(value):
    return json.dumps(value, ensure_ascii=False, indent=2)

def digest(value):
    return sha256(value.encode()).hexdigest()

def write(path, data):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(dump(data) + "\n")
    temp.replace(path)

def api(path, payload=None):
    con = HTTPConnection("127.0.0.1", 11485, timeout=300)
    try:
        con.request("POST" if payload is not None else "GET", path,
                    json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None,
                    {"Content-Type": "application/json"})
        response = con.getresponse()
        data = response.read()
        if response.status != 200:
            raise RuntimeError(f"Loopback server HTTP {response.status}")
        return json.loads(data)
    finally:
        con.close()

def rate(system, data, form):
    request = {"model": MODEL, "messages": [{"role": "system", "content": system},
               {"role": "user", "content": dump(data)}], "stream": False,
               "format": form, "options": OPTIONS}
    envelope = api("/api/chat", request)
    if envelope.get("done_reason") != "stop" or envelope.get("model") != MODEL:
        raise ValueError("Incomplete local model response")
    return json.loads(envelope["message"]["content"])

def collect():
    corpus, = ROOT.glob("DAIS_C_*/DAIS-C-Annotated - Upload")
    folder = corpus / "DAI-C-CL/Interactional/Full tagged pass"
    cases = []
    for path in sorted(p for p in folder.glob("*-FULL.*") if not p.name.startswith("~$")):
        sid = path.stem.removesuffix("-FULL")
        roles = rf"<({re.escape(sid)}|INT|FAM|DOC)\s*>(.*?)</\1\s*>"
        turns = [(m[1].upper(), re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m[2])).strip())
                 for m in re.finditer(roles, document_text(path), re.I | re.S)]
        for i, (role, question) in enumerate(turns[:10]):
            key = " ".join(WORD.findall(question.lower().replace("’", "'")))
            q = next((q for q, prompt in QUESTIONS.items() if prompt in key), None)
            if role != "INT" or not q:
                continue
            if q != "Q1":
                speaker, answer = turns[i+1]
                if speaker != sid.upper() or not answer or re.search(r"</?\w+>", question + answer):
                    raise ValueError("First reply integrity check failed")
                cases.append((q, digest(path.name), {"question": question, "reply": answer}))
            break
    if Counter(q for q, *_ in cases) != {"Q2": 7, "Q3": 7}:
        raise ValueError("Unexpected number of replies")
    random.Random(20261121).shuffle(cases)
    return cases

def check_type(row, answer):
    if not row["reason"].strip() or not row["evidence"]:
        raise ValueError("Missing type reason or anchor")
    alts = row["alternatives"]
    if row["type"] == "ambiguous" and len(set(alts)) < 2:
        raise ValueError("Ambiguity needs alternatives")
    if row["type"] != "ambiguous" and alts:
        raise ValueError("Single type must be unambiguous")
    return {**row, "evidence": [evidence_span(answer, q) for q in row["evidence"]]}

def check(field, row, answer):
    return check_type(row, answer) if field == "response" else validate_row(field, row, answer)

def repair_anchor(field, row, dialogue):
    answer = dialogue["reply"]
    words = list(re.finditer(r"\S+", answer))
    index = {"type": "integer", "minimum": 0, "maximum": len(words)-1}
    pair = obj({"first": index, "last": index})
    data = {"question": dialogue["question"], "item": field, "fixed_rating": row,
            "numbered_reply": [[n, w[0]] for n, w in enumerate(words)]}
    result = rate(ANCHOR_PROMPT, data, obj({"spans": arr(pair)}))
    evidence = []
    for span in result["spans"]:
        a, b = span["first"], span["last"]
        if not 0 <= a <= b < len(words):
            raise ValueError("Invalid repaired span")
        start, end = words[a].start(), words[b].end()
        evidence.append({"start": start, "quote": answer[start:end]})
    return check(field, {**row, "evidence": evidence}, answer)

def main():
    os.umask(0o077)
    private = HERE / "private"
    private.mkdir(mode=0o700, exist_ok=True)
    models = api("/api/tags")["models"]
    model, = [m for m in models if m["name"] == MODEL and m["digest"] == DIGEST]
    cases = collect()
    manifest = {"model": model, "ollama": api("/api/version"), "options": OPTIONS,
                "system_prompts": [TYPE_PROMPT, CLIN_PROMPT, ANCHOR_PROMPT],
                "forms": [TYPE_FORM, CLIN_FORM],
                "reader_code_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
                "plan_sha256": digest((HERE.parent / "handoff.md").read_text().split(
                    "## 11월 21일 · DAIS-C 첫 답변 비교 판정안 v1\n",1)[1].split("\n## ",1)[0]),
                "cases": [{"blind": i, "group": q, "source_digest": s, "input_digest": digest(dump(d))}
                          for i, (q, s, d) in enumerate(cases, 1)]}
    plan = private / "manifest.json"
    if plan.exists() and json.loads(plan.read_text()) != manifest:
        raise ValueError("Manifest changed. Keep the original run.")
    write(plan, manifest)
    for n,(group, _, dialogue) in enumerate(cases, 1):
        f = private / f"read-{n:02}.json"
        record = json.loads(f.read_text()) if f.exists() else {"group": group}
        if "rows" in record:
            continue
        for name, prompt, schema in (("response", TYPE_PROMPT, TYPE_FORM), ("clinical", CLIN_PROMPT, CLIN_FORM)):
            if name not in record:
                record[name] = rate(prompt, dialogue, schema)
                write(f, record)
        rows, repairs, errors = {}, [], []
        for field, raw in [("response", record["response"]), *record["clinical"].items()]:
            try:
                rows[field] = check(field, raw, dialogue["reply"])
            except ValueError:
                try:
                    rows[field] = repair_anchor(field, raw, dialogue)
                    repairs.append(field)
                except ValueError:
                    errors.append(field)
        record.update(rows=rows, anchor_repairs=repairs, invalid=errors)
        write(f,record)
        print(f"Completed {n}/14; valid fields {len(rows)}/5; anchor-only repairs {len(repairs)}", flush=True)
    result = {}
    for g in ("Q2", "Q3"):
        group_rows = [rec for f in private.glob("read-*.json")
                      if (rec := json.loads(f.read_text()))["group"] == g]
        if len(group_rows) != 7:
            raise ValueError("Incomplete question group")
        fields = {}
        for field in ("response", *FEATURES):
            counts = Counter()
            for rec in group_rows:
                row = rec["rows"].get(field)
                counts[row["type" if field == "response" else "status"] if row else "technical_missing"] += 1
            fields[field] = dict(counts)
        result[g] = fields
    write(HERE / "counts.json", result)
    print(dump(result))

if __name__ == "__main__":
    main()
