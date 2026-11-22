"""Independent first readings of one frozen, source-blinded mixed input.

Usage: blind_read.py check | freeze | read ENGINE [CONCURRENCY] | verify
Freeze, read and verify access blind.json. No function loads a corpus, source key,
generator, other reader's output for rating, or previous case readings as context.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import random
import re
import secrets
import subprocess
import sys
from types import SimpleNamespace
import uuid

sys.dont_write_bytecode = True
os.umask(0o077)
HERE = Path(__file__).resolve().parent
PRIVATE = HERE / "private"
BLIND = PRIVATE / "blind.json"
BASE = PRIVATE / "blind-reader"
SHORT = HERE.parent / "short-replies-20261121"
sys.path.insert(0, str(SHORT))
import collect as prior
from summarize import check_receipt, validated_type

ENGINES = ("opus", "gpt")
TASKS = ("type", "clinical")
MISSING = "technical_missing"
FROZEN = json.loads((SHORT / "frozen-inputs.json").read_text())
TRANSPORT = {"opus": prior.PREVIOUS / "opus/run.py", "gpt": prior.PREVIOUS / "gpt/collect.py"}
for source in (prior.READER, prior.TYPE_READER, *TRANSPORT.values(), SHORT / "collect.py"):
    if prior.digest(source) != FROZEN[str(source.relative_to(HERE.parent.parent))]:
        raise RuntimeError("Previously frozen reader or transport changed: " + source.name)
CLIN = prior.module("frozen_clin", prior.READER)
ROLE = prior.module("frozen_role", prior.TYPE_READER)
os.environ["PATH"] = str(Path.home() / ".local/bin") + os.pathsep + os.environ["PATH"]


def save(path, value):
    tmp = path.with_name("." + path.name + "." + uuid.uuid4().hex)
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    os.replace(tmp, path)


def private_dirs():
    PRIVATE.mkdir(mode=0o700, exist_ok=True)
    if PRIVATE.stat().st_mode & 0o077:
        raise RuntimeError("private directory allows group or other access")
    BASE.mkdir(mode=0o700, exist_ok=True)


def cases():
    raw = json.loads(BLIND.read_text())
    if len(raw) != 140 or not isinstance(raw, list):
        raise ValueError("Expected 140 blind cases")
    result = {}
    for row in raw:
        if set(row) != {"uid", "question", "answer"} or not all(isinstance(v, str) and v.strip() for v in row.values()):
            raise ValueError("Expected only opaque uid and nonempty question and answer")
        if row["uid"] in result:
            raise ValueError("Duplicate blind uid")
        result[row["uid"]] = {"history": [], "question": row["question"], "answer": row["answer"]}
    return result


def type_packet(dialogue):
    return {"instructions": ROLE.TYPE_PROMPT, "dialogue": dialogue, "form": ROLE.TYPE_FORM}


def source(packet, alias):
    # Frozen transport serializes only this packet, never its local alias.
    return SimpleNamespace(EXAMPLES={alias:(packet["dialogue"],)}, RUBRIC=packet["instructions"],
                           blank_form=lambda:packet["form"], packet=lambda d:packet)


def packet_for(task, dialogue):
    return type_packet(dialogue) if task == "type" else CLIN.packet(dialogue)


def freeze():
    private_dirs()
    data = cases()
    manifest = BASE / "freeze.json"
    if manifest.exists():
        return load_manifest()[1]
    orders = {}
    for engine in ENGINES:
        names = list(data)
        random.SystemRandom().shuffle(names)
        # Different name/order per engine and form. Neither is in model input.
        orders[engine] = []
        for task in TASKS:
            ids = list(names)
            random.SystemRandom().shuffle(ids)
            orders[engine].extend({"uid":uid, "task":task, "alias":secrets.token_hex(10)} for uid in ids)
        random.SystemRandom().shuffle(orders[engine])
    obj = {"blind_sha256":prior.digest(BLIND), "source_hashes":{str(p.relative_to(HERE.parent.parent)):prior.digest(p)
           for p in (prior.READER, prior.TYPE_READER, *TRANSPORT.values(), SHORT / "summarize.py")},
           "orders":orders}
    save(manifest, obj)
    return obj


def load_manifest():
    private_dirs()
    obj = json.loads((BASE / "freeze.json").read_text())
    if obj["blind_sha256"] != prior.digest(BLIND):
        raise RuntimeError("Blinded input changed")
    for name, digest in obj["source_hashes"].items():
        if prior.digest(HERE.parent.parent / name) != digest:
            raise RuntimeError("Frozen dependency changed")
    data = cases()
    for order in obj["orders"].values():
        assert len(order) == 2*len(data) and len({x["alias"] for x in order}) == len(order)
        assert {(x["uid"], x["task"]) for x in order} == {(u,t) for u in data for t in TASKS}
    return data, obj


def quote_error(exc):
    return any(phrase in str(exc) for phrase in ("anchor", "quote", "Quote", "Evidence", "evidence"))


def decode(directory, alias):
    text = (directory / "raw" / (alias + ".txt")).read_text()
    fence = re.fullmatch(r"\s*```(?:json)?\s*\n(.*?)\n```\s*", text, re.I | re.S)
    content = fence[1] if fence else text
    assert (directory / "forms" / (alias + ".json")).read_text() in (text, content)
    try:
        obj = json.loads(content)
    except ValueError:
        return None
    return obj if isinstance(obj, dict) else None


def verified(engine, attempt, alias, expected):
    session = check_receipt(engine, attempt, alias, expected)
    path = attempt / ("receipts" if engine == "opus" else "meta") / (alias + ".json")
    rec = json.loads(path.read_text())
    if engine == "opus":
        assert rec["init_model"] == "claude-opus-5-5" and not rec["skills"] and rec["result_subtype"] == "success"
        events = [json.loads(s) for s in (attempt / "raw" / (alias + ".jsonl")).read_bytes().splitlines()]
        final, = [s for s in events if s["type"] == "result" and s.get("subtype") == "success"]
        assert final["result"] == (attempt / "raw" / (alias + ".txt")).read_text()
        limits = [s["rate_limit_info"] for s in events if s.get("type") == "rate_limit_event"]
        assert not any(event.get("isUsingOverage") for event in limits)
    else:
        assert rec["requested_model"] == rec["cli_model"] == "gpt-6.1-sol"
        assert rec["provider"] == "openai" and rec["sandbox"].startswith("read-only")
        assert rec["reasoning_effort"] == "medium" and rec["process_id_isolation"].startswith("fresh process")
        # Server model identification is optional in this CLI; never claim it if unavailable.
        assert all(model.startswith("gpt-6.1-sol") for model in rec["service_response_models"])
    return session, rec


def transport_error(exc, attempt, engine, alias):
    message = str(exc)
    if engine == "gpt":
        failures = list((attempt / "meta").glob("*.transport-failure-*.json"))
        for failure in failures:
            message += " " + " ".join(json.loads(failure.read_text()).get("errors", []))
        if (attempt / "raw" / (alias+".txt")).exists():
            return "verify_existing_output", None
    else:
        raw = attempt / "raw" / (alias+".jsonl")
        if raw.exists():
            reset_at = None
            for line in reversed(raw.read_text().splitlines()):
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if row.get("type") == "rate_limit_event":
                    details = row.get("rate_limit_info", {})
                    if details.get("status") == "rejected":
                        reset_at = details.get("resetsAt")
                elif row.get("type") == "result":
                    if row.get("subtype") == "success" and not row.get("is_error"):
                        return "verify_existing_output", None
                    message += " " + str(row.get("result", ""))
            if isinstance(reset_at, (int, float)) and reset_at > 0:
                return "subscription_limit", datetime.fromtimestamp(reset_at,timezone.utc).isoformat()
    if re.search(r"(usage.limit|hit your limit|rate.limit|quota|resets?\s|429|usage cap|usage_limit)", message, re.I):
        reset = re.search(r"(?:resets?\s+(?:at\s+)?|try again (?:after|at|in)\s+)([a-zA-Z0-9 :,./+()_-]{2,70})", message, re.I)
        return "subscription_limit", reset.group(1).strip() if reset else None
    if re.search(r"(connect|socket|timeout|timed out|temporary|service unavailable|server error|502|503|504|network)", message, re.I):
        return "transport_unavailable", None
    return "transport_error", None


class StopRead(Exception):
    pass


def collect_one(engine, job, packet, principal, runtime):
    alias = job["alias"]
    parent = BASE / engine / job["task"] / alias / principal
    parent.mkdir(parents=True, exist_ok=True)
    success = parent / "received.json"
    if success.exists():
        return parent / json.loads(success.read_text())["attempt"]
    previous = sorted(parent.glob("attempt-*"))
    for folder in previous:
        if (folder / "forms" / (alias+".json")).exists():
            verified(engine, folder, alias, packet)
            save(success, {"attempt":folder.name})
            return folder
        if not (folder / "failure.json").exists():
            raise StopRead("Incomplete attempt needs inspection")
        if json.loads((folder / "failure.json").read_text())["kind"] == "verify_existing_output":
            raise StopRead("First output needs inspection")
    attempt = parent / f"attempt-{len(previous)+1:03d}"
    attempt.mkdir()
    for name in ("forms", "raw", "packets", "meta", "receipts"):
        (attempt / name).mkdir()
    model = prior.module("isolated_transport", TRANSPORT[engine])
    reader = source(packet, alias)
    try:
        if engine == "opus":
            model.HERE = attempt
            model.record(alias, reader, runtime[0], runtime[1])
        else:
            model.OUTPUT = attempt
            model.rate(reader, alias)
    except (ValueError, RuntimeError, subprocess.TimeoutExpired, OSError) as exc:
        kind, reset = transport_error(exc, attempt, engine, alias)
        details = {"kind":kind, "reset_hint":reset, "utc":datetime.now(timezone.utc).isoformat(),
                   "exception_class":type(exc).__name__}
        save(attempt / "failure.json", details)
        raise StopRead(f"{kind} ({reset or 'no reset time supplied'})") from None
    verified(engine, attempt, alias, packet)
    save(success, {"attempt":attempt.name})
    return attempt


def first_rows(task, form):
    fields = ("type",) if task == "type" else CLIN.FEATURES
    if form is None or (task == "clinical" and set(form) - set(CLIN.FEATURES)):
        return dict.fromkeys(fields)
    return {"type":form} if task == "type" else {k:form.get(k) for k in fields}


def validate(field, row, answer):
    if field == "type":
        return validated_type(ROLE, row, answer)
    return CLIN.validate_row(field, row, answer)


def repair_packet(field, row, dialogue):
    words = list(re.finditer(r"\S+", dialogue["answer"]))
    index = {"type":"integer","minimum":0,"maximum":len(words)-1}
    schema = ROLE.obj({"spans":ROLE.arr(ROLE.obj({"first":index,"last":index}))})
    return {"instructions":ROLE.ANCHOR_PROMPT,
            "dialogue":{"question":dialogue["question"], "item":"response" if field=="type" else field,
                        "fixed_rating":row, "numbered_reply":[[i,w[0]] for i,w in enumerate(words)]},
            "form":schema}, words


def apply_spans(field, row, answer, result, words):
    if not isinstance(result,dict) or set(result) != {"spans"} or not isinstance(result["spans"],list):
        raise ValueError("Malformed anchor response")
    evidence = []
    for pair in result["spans"]:
        if not isinstance(pair,dict) or set(pair) != {"first","last"}:
            raise ValueError("Malformed anchor pair")
        a,b = pair["first"],pair["last"]
        if type(a) != int or type(b) != int or not 0 <= a <= b < len(words):
            raise ValueError("Invalid word indices")
        start,end=words[a].start(),words[b].end()
        evidence.append({"start":start,"quote":answer[start:end]})
    return validate(field, {**row,"evidence":evidence}, answer)


def score(engine, job, dialogue, runtime, verify_only=False):
    task, alias = job["task"], job["alias"]
    expected = packet_for(task, dialogue)
    checks = []
    def obtain(packet, principal):
        if verify_only:
            directory = BASE / engine / task / alias / principal
            receipt = json.loads((directory / "received.json").read_text())
            attempt = directory / receipt["attempt"]
        else:
            attempt = collect_one(engine, job, packet, principal, runtime)
        session, rec = verified(engine, attempt, alias, packet)
        checks.append((session, bool(rec.get("service_response_models")) if engine == "gpt" else True))
        return decode(attempt, alias)
    first = obtain(expected, "first")
    out, repaired, rejected = {}, [], []
    for field,row in first_rows(task,first).items():
        valid = None
        try:
            valid = validate(field, row, dialogue["answer"])
        except (KeyError, ValueError, TypeError) as exc:
            if (isinstance(row,dict) and isinstance(row.get("reason"),str)
                    and row["reason"].strip() and quote_error(exc)):
                anchor, words = repair_packet(field, row, dialogue)
                spans = obtain(anchor, "anchor-"+field)
                try:
                    valid = apply_spans(field, row, dialogue["answer"], spans, words)
                    repaired.append(field)
                except (ValueError, TypeError, KeyError):
                    pass
        if valid is None:
            rejected.append(field)
        if task == "type":
            out = {k:valid[k] for k in ("type","alternatives","also_requests_clarification")} if valid else {
                "type":MISSING,"alternatives":[],"also_requests_clarification":None}
        else:
            out[field] = valid["status"] if valid else MISSING
    return out, checks, repaired, rejected


def read(engine, workers):
    data, manifest = load_manifest()
    (BASE / engine).mkdir(exist_ok=True)
    with (BASE / engine / "worker.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        model = prior.module("runtime", TRANSPORT[engine])
        runtime = model.runtime() if engine == "opus" else None
        if engine == "opus":
            env_meta = {"version":runtime[3], "account":runtime[2], "requested":model.MODEL}
        else:
            env_meta = {"version":subprocess.check_output(["codex","--version"],text=True).strip(),
                        "requested":model.MODEL, "forced_login_method":"chatgpt"}
        save(BASE / engine / "runtime.json", env_meta)
        todo = [job for job in manifest["orders"][engine]
                if not (BASE / engine / job["task"] / job["alias"] / "score.json").exists()]
        print(engine, "remaining",len(todo), "concurrency",workers, flush=True)
        def do(job):
            out, checks, repaired, rejected = score(engine, job, data[job["uid"]], runtime)
            save(BASE / engine / job["task"] / job["alias"] / "score.json",
                 {"rating":out,"sessions":checks,"repaired":repaired,"invalid":rejected})
        # Submit one small wave at a time. A quota stop prevents any further waves.
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for i in range(0,len(todo),workers):
                list(pool.map(do, todo[i:i+workers]))
                if i//workers % 5 == 0:
                    print(engine, "completed",len(manifest["orders"][engine])-len(todo)+min(i+workers,len(todo)),flush=True)


def verify():
    data, manifest = load_manifest()
    ratings = {uid:{engine:{} for engine in ENGINES} for uid in data}
    sessions = set()
    counts = {eng:Counter() for eng in ENGINES}
    for engine in ENGINES:
        for job in manifest["orders"][engine]:
            path = BASE / engine / job["task"] / job["alias"] / "score.json"
            original = json.loads(path.read_text())
            row, checks, repaired, rejected = score(engine, job, data[job["uid"]], None, verify_only=True)
            assert (row, [list(pair) for pair in checks], repaired, rejected) == (
                original["rating"],original["sessions"],original["repaired"],original["invalid"])
            ratings[job["uid"]][engine][job["task"]] = row
            for sid, provider_model in checks:
                assert sid not in sessions
                sessions.add(sid)
                counts[engine]["sessions"] += 1
                counts[engine]["response_model_ids"] += int(provider_model)
            counts[engine]["first_forms"] += 1
            counts[engine]["anchor_attempts"] += len(checks)-1
            counts[engine]["anchor_success"] += len(repaired)
            counts[engine]["technical_missing"] += len(rejected)
        counts[engine]["unsuccessful_transport_attempts"] = len(list((BASE/engine).rglob("failure.json")))
    save(PRIVATE / "blind-ratings.json",ratings)
    verification = {"input_sha256":prior.digest(BLIND), "ratings_sha256":prior.digest(PRIVATE / "blind-ratings.json"),
        "cases":len(data),"distinct_successful_sessions":len(sessions),"verified":dict(counts),
        "submitted_source_metadata_fields":0,"detected_tool_calls":0,"frozen_files":manifest["source_hashes"],
        "pipeline_sha256":prior.digest(Path(__file__)),
        "models":{engine:json.loads((BASE/engine/"runtime.json").read_text()) for engine in ENGINES}}
    save(HERE / "blind-verification.json",verification)
    print(json.dumps(verification["verified"]))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("check","freeze","read","verify"))
    parser.add_argument("engine",nargs="?",choices=ENGINES)
    parser.add_argument("workers",nargs="?",type=int,choices=(1,2,3,4,5),default=2)
    args=parser.parse_args()
    if args.action == "check":
        for task in TASKS:
            d={"history":[],"question":"Which day?","answer":"Tuesday."}
            packet=packet_for(task,d)
            assert set(packet) == {"instructions","dialogue","form"} and packet["dialogue"] == d
        print("Verified frozen form and transport hashes; two local packet checks passed; no inference.")
    elif args.action == "freeze":
        freeze()
    elif args.action == "read" and args.engine:
        try:
            read(args.engine,args.workers)
        except StopRead as exc:
            print(args.engine, str(exc),flush=True)
            raise SystemExit(3)
    elif args.action == "verify":
        verify()
    else:
        parser.error("read requires an engine")


if __name__ == "__main__":
    main()
