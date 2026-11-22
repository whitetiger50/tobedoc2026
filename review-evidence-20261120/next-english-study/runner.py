"""Run the frozen three-condition English study. All provider work uses existing subscriptions."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from itertools import islice
import fcntl
from pathlib import Path
import json
import os
import random
import secrets
import sys
import time

HERE = Path(__file__).resolve().parent
PRIOR = HERE.parent / "english-12turn-run"
PRIVATE = HERE / "private"
ARMS = ("B", "T1", "T2")
IDS = tuple(f"N{i:02}" for i in range(1, 9))
KEY = PRIVATE / "key.json"
sys.dont_write_bytecode = True
sys.path.insert(0, str(PRIOR))
import generation as gen
import assess
import quota

sha = lambda path: gen.digest(path.read_bytes())
read = gen.load
save = gen.save
check = gen.require
upstream_sources = gen.sources


@lru_cache
def sources():
    systems, core = upstream_sources()
    return {**systems, "T2": (HERE / "T2.txt").read_text()}, core


# Only the source registry, identifier/arm set and destinations change.
# Native profile mapping, message construction, generation transport, blind packet
# and all score/provenance validators remain upstream functions.
gen.sources = sources
gen.HERE = HERE
gen.GEN = PRIVATE / "generation"
gen.CASES = HERE / "cases.json"
gen.FREEZE = HERE / "generation-freeze.json"
gen.ARMS = ARMS
gen.CASE_IDS = set(IDS)
assess.HERE = HERE


def key():
    if not KEY.exists():
        cells = [{"id": "I" + secrets.token_hex(10), "case": c, "arm": a} for c in IDS for a in ARMS]
        random.SystemRandom().shuffle(cells)
        save(KEY, cells)
    cells = read(KEY)
    check(len(cells) == len({r["id"] for r in cells}) == 24, "Incomplete blind identifiers")
    check({(r["case"], r["arm"]) for r in cells} == {(c, a) for c in IDS for a in ARMS}, "Invalid key")
    return cells


def inputs():
    cases = read(gen.CASES)
    check(len(cases) == 8 and {c["id"] for c in cases} == set(IDS), "Need independent N01..N08")
    check(sorted(Counter(c["stratum"] for c in cases).values()) == [2, 2, 2, 2], "Unbalanced strata")
    return {c["id"]: c for c in cases}


def freeze():
    cases = inputs()
    key()
    first = {}
    for cid, case in cases.items():
        questions = case["questions"]
        check(len(questions) == len(set(questions)) == 12, "Non-unique or incomplete questions")
        pairs = [(q, "History integrity marker " + str(i)) for i, q in enumerate(questions[:-1], 1)]
        for arm in ARMS:
            start = gen.messages(case, arm, 1, [])
            end = gen.messages(case, arm, 12, pairs)
            if arm == "B":
                recorded = [(q["content"], a["content"]) for q, a in zip(end[1:-1:2], end[2:-1:2])]
            else:
                hist = json.loads(end[1]["content"])["history"]
                recorded = [(q["text"], a["text"]) for q, a in zip(hist[::2], hist[1::2])]
            check(recorded == pairs, "Native history mismatch")
            first[cid + "-" + arm] = gen.digest(gen.encode(start))
        for i in range(1, 13):
            t1, t2 = [gen.messages(case, a, i, pairs[:i-1]) for a in ("T1", "T2")]
            check(t1[1] == t2[1] and t1[0] != t2[0], "Team comparison does not isolate prompt")
    tracked = [Path(__file__), gen.CASES, HERE/"T2.txt", KEY, HERE/"method/design-receipt.json",
               PRIOR/"generation.py", PRIOR/"assess.py", PRIOR/"quota.py", assess.RUBRIC, *gen.SOURCE_HASHES,
               assess.PRIOR/"gpt/collect.py", assess.PRIOR/"opus/run.py"]
    tracked += [p for p in (HERE/"DESIGN.ko.md", HERE/"DESIGN.md", HERE/"method/decisions.ko.md") if p.is_file()]
    hashes = {os.path.relpath(p, HERE): sha(p) for p in tracked}
    old = read(PRIOR/"method/prescore-hashes.json")
    updated = read(PRIOR/"method/transport-amendment.json")
    for f in ("generation.py", "assess.py", "quota.py"):
        check(sha(PRIOR/f) == updated.get(f, {}).get("new", old[f]), "Original implementation changed: " + f)
    save(gen.FREEZE, {"cases_sha256": sha(gen.CASES), "generator_sha256": sha(PRIOR/"generation.py"),
                      "first_message_sha256": first, "hashes": hashes, "model": gen.MODEL, "effort": "medium",
                      "cases": 8, "turns": 12, "generation_calls": 288, "blind_interviews": 24,
                      "ratings": 96, "arms": list(ARMS), "primary_scale_sha256": assess.GOLD_HASH,
                      "condition_system_hashes": {a: gen.digest(sources()[0][a].encode()) for a in ARMS},
                      "history": "native B session; each team system with identical original JSON builder and its own full history"})
    print("Frozen 8 cases, 24 interviews and 288 turns", flush=True)


def verify_design():
    frozen = read(gen.FREEZE)
    for name, expected in frozen["hashes"].items():
        check(sha(HERE/name) == expected, "Frozen source changed: " + name)


def quota_check(op, idx):
    current = quota.read_quota()
    w = current["primary"]
    check(current["limitId"] == "codex" and w["windowDurationMins"] == 10080 and
          isinstance(w["usedPercent"], (int,float)), "Missing Codex weekly meter")
    with (HERE/"method/budget.jsonl").open("a") as f:
        f.write(json.dumps(dict(time=gen.now(), operation=op, batch=idx, percent=w["usedPercent"],
                                reset=w["resetsAt"])) + "\n")
    check(w["usedPercent"] < 66, f"Codex budget stop: weekly use {w['usedPercent']}%")


def claude_check():
    assess.verify_overage_lock()
    rates = read(HERE/"method/design-receipt.json")["rate"]
    receipts = sorted((HERE/"ratings/opus").glob("r*/*/attempt-*/provider.json"),
                      key=lambda p:p.stat().st_mtime_ns)
    if receipts:
        latest = read(receipts[-1])["rate_events"]
        if latest:
            rates = latest
    rate = rates[-1]
    w = rate.get("unifiedWindows") or {}
    for name, threshold in (("seven_day", .66), ("five_hour", .96)):
        window = w.get(name,{})
        check(isinstance(window.get("utilization"), (int,float)) and isinstance(window.get("resetsAt"), (int,float)),
              "Missing Claude " + name + " usage window")
        if window["resetsAt"] > time.time():
            check(window.get("status") != "rejected" and window["utilization"] < threshold,
                  f"Claude {name} pause until {window['resetsAt']} (utilization {window['utilization']})")


def batches(op, jobs, worker, size):
    jobs = iter(jobs)
    done = 0
    while batch := list(islice(jobs, size)):
        quota_check(op, done // size + 1)
        if op == "opus":
            claude_check()
        with ThreadPoolExecutor(max_workers=size) as pool:
            futures = [pool.submit(worker, job) for job in batch]
            for future in futures:
                future.result()
        done += len(batch)
        print(op, done, flush=True)


def generate():
    verify_design()
    for turn in range(1,13):
        cells = sorted(key(), key=lambda r:(r["case"],r["arm"]))
        random.Random(f"next-english-cells-{turn}").shuffle(cells)
        jobs = [(cell["case"],cell["arm"],turn) for cell in cells
                if not (gen.turn_dir(cell["case"],cell["arm"],turn)/"result.json").is_file()]
        batches("generate", jobs, lambda job: gen.one(*job), 6)
        print("Complete through turn", turn, flush=True)


def checked_dialogue(case, arm):
    cid = case["id"]
    pairs, sessions = [], []
    for t in range(1,13):
        folder = gen.turn_dir(cid,arm,t)
        packet = gen.messages(case,arm,t,pairs)
        r = gen.verify_result(folder, gen.digest(gen.encode(packet)))
        check(read(folder/"request.json") == packet and r["case"] == cid and r["arm"] == arm and
              r["turn"] == t and r["question"] == case["questions"][t-1], "Packet mismatch")
        check(sha(folder/"events.jsonl") == r["trace_sha256"] and r["visible_tool_events"] == 0 and
              r["exit_code"] == 0, "Changed raw generator trace")
        check((folder/"last.txt").read_text() in (r["raw"],r["raw"]+"\n"), "First-output mismatch")
        pairs.append((r["question"],r["raw"]))
        sessions.append(r["session"])
        expected_trace = pairs if arm=="B" else [(packet[-1]["content"],r["raw"])]
        native = [(role, value) for q,a in expected_trace for role,value in (("user_message",q),("agent_message",a))]
        check(gen.digest(gen.encode(native))==r["native_transcript_sha256"],"Native transcript hash mismatch")
    check(len(set(sessions)) == (1 if arm=="B" else 12), "Session overlap or broken native history")
    return {"profile":case["profile"], "dialogue":[dict(question=q,answer=a) for q,a in pairs]}, set(sessions)


def mask():
    verify_design()
    cases = inputs()
    sessions, hashes = set(), {}
    for r in key():
        body, sample_sessions = checked_dialogue(cases[r["case"]], r["arm"])
        check(not sessions.intersection(sample_sessions), "Generation session reused across interviews")
        sessions.update(sample_sessions)
        assess.packet(body)
        path = HERE/"blind"/(r["id"]+".json")
        save(path,body)
        hashes[r["id"]] = sha(path)
    check(len(sessions) == 200, "Expected 8 B + 192 fresh team sessions")
    save(HERE/"blind-freeze.json", {"hashes":hashes,"generation_sessions":len(sessions),"answers":288})
    print("Masked and checked 24 interviews", flush=True)


def check_blind():
    frozen = read(HERE/"blind-freeze.json")
    check(set(frozen["hashes"]) == {r["id"] for r in key()}, "Incomplete mask")
    for uid, expected in frozen["hashes"].items():
        check(sha(HERE/"blind"/(uid+".json")) == expected, "Blind input changed")


def judge(reader):
    verify_design()
    check_blind()
    for round_num in (1,2):
        uids = sorted(r["id"] for r in key())
        random.Random(f"next-english-ratings-{reader}-{round_num}").shuffle(uids)
        jobs = [uid for uid in uids if not (assess.destination(reader,round_num,uid)/"accepted.json").exists()]
        batches(reader,jobs,lambda uid: assess.collect(reader,round_num,uid),3)


def verify():
    mask()
    records = key()
    sessions = set()
    reader_results = {}
    engine_rows = {}
    for engine in ("gpt","opus"):
        expr = {cid:{} for cid in IDS}
        status = Counter()
        for cell in records:
            scores = []
            for run in (1,2):
                r = assess.load_rating(engine,run,cell["id"])
                status[r["status"]] += 1
                check(r["status"]!="missing","Pending first-form receipt")
                check(r["session"] not in sessions,"Duplicate reader session")
                sessions.add(r["session"])
                scores.append(r["score"])
            expr[cell["case"]][cell["arm"]] = scores
        tests = {}
        for left,right in (("T2","T1"),("T2","B"),("T1","B")):
            v = {cid:assess.compare(expr[cid][left],expr[cid][right]) for cid in IDS}
            tests[left+"_vs_"+right] = {"by_case":v,"counts":dict(Counter(v.values()))}
        engine_rows[engine] = expr
        repeated = [pair for arms in expr.values() for pair in arms.values() if None not in pair]
        flat = [s for arms in expr.values() for pair in arms.values() for s in pair]
        reader_results[engine]={"by_case":expr,"contrasts":tests,"status":dict(status),
            "score_distribution":assess.distribution(flat),"repeat_exact":{"agree":sum(a==b for a,b in repeated),
            "available":len(repeated),"scheduled":24}}
    cross = [(engine_rows["gpt"][c][a][i],engine_rows["opus"][c][a][i]) for c in IDS for a in ARMS for i in range(2)]
    common = [(x,y) for x,y in cross if None not in (x,y)]
    check(len(sessions)==96, "Need 96 completed first assessment sessions")
    save(HERE/"results.json",{"generation_turns":288,"interviews":24,"reader_sessions":len(sessions),
         "readers":reader_results, "cross_reader_exact":{"agree":sum(x==y for x,y in common),
         "available":len(common),"scheduled":48},"unit":"8 independent paired fictional cases; repetitions nested"})
    print("Verified 288 first answers, 24 masked files, 96 isolated first readings", flush=True)


if __name__=="__main__":
    os.umask(0o077)
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="action",required=True)
    for task in ("freeze","generate","mask","verify"):
        sub.add_parser(task)
    sub.add_parser("judge").add_argument("reader",choices=("gpt","opus"))
    args=parser.parse_args()
    PRIVATE.mkdir(parents=True,exist_ok=True)
    lockname=args.action+(("-"+args.reader) if args.action=="judge" else "")
    with (PRIVATE/(lockname+".lock")).open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if args.action=="judge":
            judge(args.reader)
        else:
            {"freeze":freeze,"generate":generate,"mask":mask,"verify":verify}[args.action]()
