"""Validate raw readings and aggregate paired states without publishing interview text."""
from collections import Counter
import json
import os
import sys
from pathlib import Path
import re

import run

sys.dont_write_bytecode = True
from summarize import check_receipt, validated_type

MISSING = "technical_missing"
DEFINITE = {"present", "absent"}
CLIN = run.prior.module("frozen_clinical", run.prior.READER)
ROLE = run.prior.module("frozen_type", run.prior.TYPE_READER)
FIELDS = ["type", *CLIN.FEATURES]


def read_set(round_number, engine, sources, sessions, errors, fixes):
    cases = {}
    for task, source in sources.items():
        directory = run.HERE / "private" / f"pass{round_number}" / engine / task
        for case, (d,) in source.EXAMPLES.items():
            sid = check_receipt(engine, directory, case, source.packet(d))
            assert sid not in sessions
            sessions.add(sid)
            raw = (directory / "raw" / (case+".txt")).read_text()
            fence = re.fullmatch(r"\s*```(?:json)?\s*\n(.*?)\n```\s*", raw, re.DOTALL | re.I)
            fields = ["type"] if task == "type" else list(CLIN.FEATURES)
            result = cases.setdefault(case, {})
            try:
                initial = json.loads(fence[1] if fence else raw)
                assert json.loads((directory / "forms" / (case+".json")).read_text()) == initial
            except (json.JSONDecodeError, UnicodeError):
                result.update(dict.fromkeys(fields, MISSING))
                errors.append([round_number, engine, case, task, "JSON decoding"])
                continue
            for field in fields:
                row = initial if task == "type" else initial.get(field)
                def check(candidate):
                    if field == "type":
                        return validated_type(ROLE, candidate, d["answer"])
                    return CLIN.validate_row(field, candidate, d["answer"])
                try:
                    valid = check(row)
                except (ValueError, KeyError, TypeError) as exc:
                    correction = directory / "anchors" / (case+"-"+field+".json")
                    if correction.is_file():
                        repaired = json.loads(correction.read_text())
                        assert repaired["reason"] == row["reason"]
                        assert {k:v for k,v in repaired.items() if k != "evidence"} == {k:v for k,v in row.items() if k != "evidence"}
                        valid = check(repaired)
                        fixes.append([round_number, engine, case, field])
                    else:
                        result[field] = MISSING
                        errors.append([round_number, engine, case, field, str(exc)])
                        continue
                result[field] = valid["type" if field == "type" else "status"]
                if field == "type":
                    result["alternatives"] = valid["alternatives"]
                    result["also_requests_clarification"] = valid["also_requests_clarification"]
    return cases


def summary(keys, rows):
    return {field: dict(Counter(rows[i][field] for i in keys)) for field in FIELDS}


def compare(keys, left, right):
    result = {}
    for field in FIELDS:
        pairs = [(left[i][field], right[i][field]) for i in keys]
        valid = [(a,b) for a,b in pairs if MISSING not in (a,b)]
        cross = {}
        for a,b in pairs:
            cross.setdefault(a, Counter())[b] += 1
        cells = {"matrix": cross, "matched": sum(a == b for a,b in valid),
                 "paired": len(valid), "total": len(pairs)}
        if field != "type":
            cells["left_definite"] = sum(a in DEFINITE for a,b in pairs)
            cells["right_definite"] = sum(b in DEFINITE for a,b in pairs)
            cells["both_definite"] = sum(a in DEFINITE and b in DEFINITE for a,b in pairs)
            cells["same_assessability"] = sum((a in DEFINITE) == (b in DEFINITE) for a,b in valid)
        result[field] = cells
    return result


def main():
    os.umask(0o077)
    groups, _, sources = run.load_cases()
    splits = {"all": list(groups), **{q:[c for c in groups if groups[c]==q] for q in ("Q2","Q3")}}
    errors, fixes, sessions = [], [], set()
    ratings = {str(r):{m:read_set(r,m,sources,sessions,errors,fixes) for m in run.ENGINES} for r in run.ROUNDS}
    assert len(sessions) == 112
    out = {"sessions":len(sessions), "anchor_repairs":len(fixes), "invalid_fields":len(errors),
           "counts":{}, "between":{}, "within":{}}
    for r, modelrows in ratings.items():
        out["counts"][r] = {m:{q:summary(ids,rows) for q,ids in splits.items()} for m,rows in modelrows.items()}
        out["between"][r] = {q:compare(ids,modelrows["opus"],modelrows["gpt"]) for q,ids in splits.items()}
    out["within"] = {m:{q:compare(ids,ratings["1"][m],ratings["2"][m]) for q,ids in splits.items()} for m in run.ENGINES}
    out["ambiguous_types"] = {r:{m:[{"group":groups[c],"alternatives":res["alternatives"]} for c,res in rows.items()
                              if res["type"]=="ambiguous"] for m,rows in mrows.items()} for r,mrows in ratings.items()}
    private = run.HERE / "private"
    (private / "rows.json").write_text(json.dumps(ratings,indent=2)+"\n")
    (private / "validation.json").write_text(json.dumps({"errors":errors,"anchor_repairs":fixes},indent=2)+"\n")
    (run.HERE / "aggregate.json").write_text(json.dumps(out,indent=2)+"\n")
    print("Verified sessions",len(sessions),"invalid fields",len(errors),"anchor repairs",len(fixes))
    for q in splits:
        print(q, "first types",*[out["counts"]["1"][m][q]["type"] for m in run.ENGINES])
        for f,c in out["between"]["1"][q].items():
            print(f, c.get("left_definite"), c.get("right_definite"), "matched",c["matched"], "/",c["paired"])
    for m in run.ENGINES:
        print(m,"within",[(f,c["matched"],c["paired"]) for f,c in out["within"][m]["all"].items()])


if __name__ == "__main__":
    main()
