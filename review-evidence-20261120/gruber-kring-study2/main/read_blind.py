"""Collect the original two blinded readings. The only experimental data input is blind.json."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import random
import re
from statistics import mean
import subprocess
import sys
import time
from types import SimpleNamespace
import uuid

HERE = Path(__file__).resolve().parent
BOUNDARY = HERE.parent / "boundary"
sys.path.insert(0, str(BOUNDARY))
import calibrate as fixed

BLIND = HERE / "blind.json"
ROOT = HERE / "readers"
FROZEN = ROOT / "freeze.json"
ENGINES = ("opus", "gpt")
SCALES = ("elaboration", "meaning_clarity")
SEED = "GK-study2-main-reader-order-v1"


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def save(path, obj):
    encoded = (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode()
    if path.exists():
        if encoded != path.read_bytes():
            raise RuntimeError("Existing record differs: " + str(path))
        return
    path.parent.mkdir(exist_ok=True, parents=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex)
    temp.write_bytes(encoded)
    os.replace(temp, path)


def open_inputs():
    rows = read(BLIND)
    assert isinstance(rows, list) and len(rows) == 360
    assert all(set(row) == {"uid", "question", "answer"} and
               all(isinstance(v, str) and v.strip() for v in row.values()) and
               re.fullmatch(r"[A-Za-z0-9_-]+", row["uid"]) for row in rows)
    mapping = {row["uid"]: {"question": row["question"], "answer": row["answer"]} for row in rows}
    assert len(mapping) == 360
    return mapping


def packet_bytes(dialogue):
    return (json.dumps(fixed.packet(dialogue), ensure_ascii=False, indent=2) + "\n").encode()


def inputs_manifest(cases):
    assert fixed.hashes() == fixed.read(fixed.MANIFEST)["sha256"]
    orders = {}
    for engine in ENGINES:
        ids = sorted(cases)
        random.Random(SEED + "/" + engine).shuffle(ids)
        orders[engine] = ids
    return {"blind_sha256": digest(BLIND), "rubric_module_sha256": digest(Path(fixed.__file__)),
            "transport_sha256": {e: digest(p) for e,p in fixed.TRANSPORTS.items()},
            "order_seed": SEED, "orders": orders,
            "payload_sha256": {uid: sha256(packet_bytes(d)).hexdigest() for uid,d in cases.items()}}


def source_module(engine):
    spec = importlib.util.spec_from_file_location(engine + "_reader_transport", fixed.TRANSPORTS[engine])
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def same(path, left):
    if path.read_bytes() != left:
        raise RuntimeError("Raw payload differs: " + str(path))


def verified_response(engine, attempt, uid, payload, frozen):
    original_txt = attempt / "raw" / (uid + ".txt")
    if engine == "gpt":
        rec = read(attempt / "meta" / (uid + ".json"))
        same(attempt / "packets" / (uid + ".json"), payload)
        assert rec["case"] == uid and rec["requested_model"] == rec["cli_model"] == "gpt-6.1-sol"
        assert rec["provider"] == "openai" and rec["sandbox"].startswith("read-only")
        assert rec["reasoning_effort"] == "medium" and rec["tool_events_cli"] == []
        assert rec["process_id_isolation"].startswith("fresh process")
        assert all(m.startswith("gpt-6.1-sol") for m in rec["service_response_models"])
        raw = original_txt
        session = rec["cli_session_id"]
        models = rec["service_response_models"]
    else:
        raw = attempt / "raw" / (uid + ".jsonl")
        rec = read(attempt / "receipts" / (uid + ".json"))
        assert rec["case_id"] == uid and rec["init_model"] == "claude-opus-5-5"
        assert rec["assistant_models"] == ["claude-opus-5-5"] and rec["turns"] == 1
        assert rec["result_subtype"] == "success" and not rec["is_error"]
        assert not any(rec[k] for k in ("tools","mcp_servers","skills","plugins","tool_blocks","hook_events"))
        assert not any((rec["server_tool_use"] or {}).values())
        events = [json.loads(l) for l in raw.read_text().splitlines() if l.strip()]
        end, = [ev for ev in events if ev["type"] == "result"]
        assert end["subtype"] == "success" and not end["is_error"]
        assert not any(ev.get("rate_limit_info",{}).get("isUsingOverage") for ev in events)
        same(original_txt, end["result"].encode())
        session = rec["session_id"]
        models = rec["assistant_models"]
    assert rec["exit_code"] == 0 and rec["packet_sha256"] == sha256(payload).hexdigest()
    assert rec["raw_sha256"] == digest(raw) and session
    assert datetime.fromisoformat(frozen) <= datetime.fromisoformat(rec["started_utc"])
    raw_text = original_txt.read_text()
    fence = re.fullmatch(r"\s*```(?:json)?\s*\n(.*?)\n```\s*", raw_text, re.S | re.I)
    canonical = fence[1] if fence else raw_text
    assert (attempt / "forms" / (uid + ".json")).read_text() in (raw_text, canonical)
    return canonical, session, models


def first_score(uid, engine, content):
    row = {"uid": uid, "reader": engine, "status":"technical_missing",
           "elaboration": None, "meaning_clarity": None, "events":[]}
    try:
        form = json.loads(content)
        events = form["events"]
        status = form["status"]
        if not isinstance(events, list) or status not in ("rated", "no_narrative") or bool(events) != (status == "rated"):
            return row
        for event in events:
            for s in SCALES:
                if type(event[s]) is not int or not 1 <= event[s] <= 3:
                    return row
                if not isinstance(event[s + "_reason"], str) or not event[s + "_reason"].strip():
                    return row
    except (ValueError, TypeError, KeyError):
        return row
    row.update(status=status, events=events)
    for s in SCALES:
        row[s] = mean(v[s] for v in events) if events else None
    return row


def failure_kind(engine, attempt, uid, exc):
    message = str(exc)
    if (attempt / "raw" / (uid + ".txt")).exists():
        return "first_output_needs_verification", None
    if engine == "gpt":
        for p in (attempt / "meta").glob("*.transport-failure-*.json"):
            message += " " + " ".join(read(p).get("errors", []))
    else:
        trace = attempt / "raw" / (uid + ".jsonl")
        if trace.is_file():
            for line in trace.read_text().splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if event.get("type") == "result":
                    if event.get("subtype") == "success" and not event.get("is_error"):
                        return "first_output_needs_verification", None
                    message += " " + str(event.get("result",""))
                info = event.get("rate_limit_info",{})
                if info.get("status") == "rejected" and info.get("resetsAt"):
                    return "subscription_limit", info["resetsAt"]
    if re.search(r"usage.limit|hit your limit|quota|429|rate.limit|resets? (?:at|in)|usage cap", message, re.I):
        hint = re.search(r"(?:try again (?:at|in|after)|resets? (?:at|in))\s+([^\n]{2,70})", message, re.I)
        return "subscription_limit", hint[1] if hint else None
    # A killed subprocess can hide a completed response. Do not repeat it automatically.
    if isinstance(exc, subprocess.TimeoutExpired):
        return "unknown_completion", None
    return "no_output_transport", None


def collect_one(engine, uid, dialogue, runtime, frozen):
    parent = ROOT / engine / uid
    parent.mkdir(parents=True, exist_ok=True)
    receipt = parent / "accepted.json"
    if receipt.exists():
        return
    previous = sorted(parent.glob("attempt-*"))
    payload = packet_bytes(dialogue)
    for p in previous:
        if (p / "forms" / (uid + ".json")).exists():
            verified_response(engine, p, uid, payload, frozen)
            save(receipt, {"attempt":p.name})
            return
        if not (p / "failure.json").exists() or read(p/"failure.json")["kind"] in ("first_output_needs_verification","unknown_completion"):
            raise RuntimeError(engine + ": interrupted/incomplete first response " + uid)
    attempt = parent / f"attempt-{len(previous)+1:03}"
    attempt.mkdir()
    for kind in ("packets","meta","receipts","forms","raw"):
        (attempt / kind).mkdir()
    t = source_module(engine)
    reader = SimpleNamespace(EXAMPLES={uid:(dialogue,)}, RUBRIC=fixed.RUBRIC,
                             packet=fixed.packet, blank_form=fixed.form)
    try:
        if engine == "opus":
            t.HERE = attempt
            t.record(uid, reader, *runtime[:2])
        else:
            t.OUTPUT = attempt
            t.rate(reader, uid)
    except (OSError, subprocess.TimeoutExpired, RuntimeError, ValueError) as exc:
        kind, reset = failure_kind(engine, attempt, uid, exc)
        save(attempt/"failure.json", {"kind":kind,"reset_hint":reset,"utc":now(),"error_type":type(exc).__name__})
        raise RuntimeError(f"{engine} {uid}: {kind}; reset={reset}") from None
    verified_response(engine, attempt, uid, payload, frozen)
    save(receipt, {"attempt":attempt.name})


def load_frozen():
    cases = open_inputs()
    loaded = read(FROZEN)
    assert loaded["spec"] == inputs_manifest(cases)
    return cases, loaded


def collect(engine, workers):
    cases, frozen = load_frozen()
    target = ROOT / engine
    target.mkdir(exist_ok=True)
    with (target/"worker.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        t = source_module(engine)
        runtime = t.runtime() if engine == "opus" else None
        if engine == "opus":
            meta = {"version":runtime[3],"account":runtime[2],"requested":t.MODEL}
        else:
            meta = {"version":subprocess.check_output(["codex","--version"],text=True).strip(),
                    "requested":t.MODEL,"login_method":"chatgpt"}
        save(target/"runtime.json",meta)
        ids = frozen["spec"]["orders"][engine]
        todo = iter([u for u in ids if not (target/u/"accepted.json").is_file()])
        with ThreadPoolExecutor(max_workers=workers) as pool:
            def dispatch(uid):
                return pool.submit(collect_one,engine,uid,cases[uid],runtime,frozen["frozen_utc"])
            pending = {dispatch(u) for _,u in zip(range(workers),todo)}
            while pending:
                done, pending = wait(pending,return_when=FIRST_COMPLETED)
                for task in done:
                    task.result()
                for _ in done:
                    u = next(todo,None)
                    if u is not None:
                        pending.add(dispatch(u))


def export():
    cases, frozen = load_frozen()
    scores, sessions = [],set()
    audits = {}
    for e in ENGINES:
        stats = Counter()
        failure_counts = Counter()
        receipts = {}
        for uid in frozen["spec"]["orders"][e]:
            job = ROOT/e/uid
            ok = read(job/"accepted.json")
            attempt = job/ok["attempt"]
            payload = packet_bytes(cases[uid])
            assert frozen["spec"]["payload_sha256"][uid] == sha256(payload).hexdigest()
            content, session, service = verified_response(e,attempt,uid,payload,frozen["frozen_utc"])
            assert session not in sessions
            sessions.add(session)
            score = first_score(uid,e,content)
            scores.append(score)
            stats[score["status"]] += 1
            stats["server_model_ids_available"] += bool(service)
            receipt_file = attempt/("meta" if e=="gpt" else "receipts")/(uid+".json")
            receipts[uid] = digest(receipt_file)
            failure_counts.update(read(p)["kind"] for p in job.glob("attempt-*/failure.json"))
        audits[e] = {"counts":dict(stats),"transport_failures":dict(failure_counts),"receipt_hashes":receipts}
    assert len(sessions) == len(scores) == 720
    save(HERE/"scores.json",scores)
    save(HERE/"reader-verification.json",{"n_cases":len(cases),"first_outputs":len(scores),
        "unique_sessions":len(sessions),"reader_results":audits,"blind_sha256":digest(BLIND),
        "reader_freeze_sha256":digest(FROZEN),"scores_sha256":digest(HERE/"scores.json"),
        "same_item_payload_each_reader":True,"tools_used":0,"first_outputs_replaced":0,
        "model_identity":"Claude service assistant ID. GPT official CLI selected/requested ID; separate response ID available only where reported."})
    print({e: a["counts"] for e,a in audits.items()},flush=True)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("freeze","gpt","opus","export","check"))
    parser.add_argument("--workers",type=int,choices=range(1,7),default=5)
    args=parser.parse_args()
    if args.action == "check":
        assert fixed.hashes() == fixed.read(fixed.MANIFEST)["sha256"]
        assert set(fixed.packet({"question":"q","answer":"a"})) == {"instructions","form","dialogue"}
        print("Frozen rubric, form and transports verified.")
    elif args.action == "freeze":
        ROOT.mkdir(exist_ok=True)
        if FROZEN.is_file():
            load_frozen()
        else:
            save(FROZEN,{"frozen_utc":now(),"spec":inputs_manifest(open_inputs())})
    elif args.action == "export":
        export()
    else:
        collect(args.action,args.workers)


if __name__ == "__main__":
    main()
