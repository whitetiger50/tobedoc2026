"""Run the frozen English generation packets once, then build a masked corpus."""
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import random
import secrets
import sys

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
PRIVATE = HERE / "private"
sys.path.insert(0, str(STUDY / "cards"))
import prepare as cards

PRIOR = STUDY.parent / "dais-generator-20261121/experiment.py"
spec = importlib.util.spec_from_file_location("dais_generator", PRIOR)
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
transport.PRIVATE = PRIVATE

SEED = "GK-study2-main-generation-v1-20261121"
SCHEDULE = PRIVATE / "generation-schedule.json"
FREEZE = HERE / "generation-freeze.json"
THREADS = 8
read = cards.read
digest = cards.digest
save = transport.dump


def freeze():
    for name, text in cards.build().items():
        assert (STUDY / "cards" / name).read_text() == text
    persons = {c["id"]: c for c in read(STUDY / "cards/cards.json")}
    intro, questions = cards.script()
    audit = read(STUDY / "cards/audit.json")
    jobs = [(row, arm) for row in audit["entries"] for arm in cards.ARMS]
    random.Random(SEED).shuffle(jobs)
    if not (PRIVATE / "blind-seed.json").exists():
        save(PRIVATE / "blind-seed.json", secrets.randbits(192))
    rng = random.Random(read(PRIVATE / "blind-seed.json"))
    schedule = []
    for idx, (row, arm) in enumerate(jobs, 1):
        case, topic = row["id"], row["topic"]
        question = questions[topic][1]
        msgs = cards.packet_for(persons[case], topic, row["profile"], row["reverse_details"], intro+"\n\n"+question, arm)
        assert cards.builder.sha(cards.builder.canonical(msgs)) == row["messages_sha256"][arm]
        assert cards.builder.sha(msgs[1]["content"].encode()) == row["user_sha256_all_three"]
        ident = f"G{idx:03}"
        path = PRIVATE / "messages" / (ident+".json")
        save(path, {"system": msgs[0]["content"], "user": msgs[1]["content"]})
        schedule.append({"job": ident, "case": case, "topic": topic, "arm": arm,
                         "uid": f"U{rng.getrandbits(72):018x}", "packet_sha256": digest(path)})
    assert len(schedule) == len({j["uid"] for j in schedule}) == 360
    save(SCHEDULE, schedule)
    package = [STUDY / "DESIGN.ko.md", STUDY / "cards/cards.json", STUDY / "cards/audit.json", Path(__file__),
               STUDY / "cards/prepare.py", PRIOR, SCHEDULE, PRIVATE / "blind-seed.json",
               STUDY / "boundary/calibrate.py", STUDY / "clarity-retest/freeze.json"]
    record = {"n": 360, "model": transport.MODEL, "reasoning_effort": "medium", "tools_enabled": False,
              "one_session_per_output": True, "responses_per_cell": 1, "randomized_submission_seed": SEED,
              "concurrent_sessions": THREADS, "sampling": "identical CLI/provider defaults for every condition; no sampling seed exposed",
              "output_limit": "same CLI/provider default for all arms", "empty_context": True,
              "transport_timeout_seconds": 190, "frozen_utc": read(FREEZE)["frozen_utc"] if FREEZE.exists() else datetime.now(timezone.utc).isoformat(),
              "sha256": {str(p.relative_to(cards.ROOT)): digest(p) for p in package}}
    save(FREEZE, record)
    print("Frozen", len(schedule), "generation packets.", flush=True)


def verify(job):
    rec = read(PRIVATE / "generated" / (job["job"]+".json"))
    assert rec["job"] == job["job"] and rec["packet_sha256"] == job["packet_sha256"]
    assert rec["raw"].strip() and rec["raw_sha256"] == cards.builder.sha(rec["raw"].encode())
    assert rec["model"] == transport.MODEL and rec["reasoning"] == "medium" and rec["session"]
    assert not rec["exit_code"] and not rec["visible_tool_events"]
    assert rec["started_utc"] >= read(FREEZE)["frozen_utc"]
    return rec


def collect(job):
    transport.generate_one(job)
    verify(job)


def generate():
    freeze()
    jobs = read(SCHEDULE)
    pending = []
    for j in jobs:
        if (PRIVATE / "generated" / (j["job"]+".json")).exists():
            verify(j)
        else:
            pending.append(j)
    iterator = iter(pending)
    errors = []
    complete = len(jobs) - len(pending)
    with ThreadPoolExecutor(max_workers=THREADS) as pool:
        active = {pool.submit(collect, j): j for j in [next(iterator) for _ in range(min(len(pending), THREADS))]}
        while active:
            finished, _ = wait(active, return_when=FIRST_COMPLETED)
            for task in finished:
                j = active.pop(task)
                try:
                    task.result()
                    complete += 1
                    if complete % 24 == 0:
                        print("Completed first outputs", complete, "/ 360", flush=True)
                except Exception as exc:
                    errors.append((j["job"], type(exc).__name__, str(exc)[:250]))
                    print("Transport issue:", errors[-1], flush=True)
                if len(errors) < 3:
                    nxt = next(iterator, None)
                    if nxt:
                        active[pool.submit(collect, nxt)] = nxt
    if errors:
        raise RuntimeError(f"{len(errors)} jobs require transport review")
    mask()


def mask():
    jobs = read(SCHEDULE)
    assert digest(SCHEDULE) == read(FREEZE)["sha256"][str(SCHEDULE.relative_to(cards.ROOT))]
    _, questions = cards.script()
    masked, key, sessions = [], [], set()
    for job in sorted(jobs, key=lambda j: j["uid"]):
        rec = verify(job)
        assert rec["session"] not in sessions
        sessions.add(rec["session"])
        raw = rec["raw"]
        masked.append({"uid": job["uid"], "question": questions[job["topic"]][1], "answer": raw})
        key.append({**{k: job[k] for k in ("uid","case","topic","arm")}, "words": len(cards.words(raw))})
    assert len(masked) == len(sessions) == 360
    save(PRIVATE / "key.json", key)
    save(HERE / "blind.json", masked)
    save(HERE / "generation-verification.json", {"verified_first_outputs": len(masked),
         "unique_sessions": len(sessions), "tool_events": 0, "all_cli_model": transport.MODEL,
         "all_cli_reasoning": "medium", "model_identity_source":"official CLI session header",
         "unmodified_raw_answers_in_blind_input": True, "blind_sha256": digest(HERE / "blind.json"),
         "private_key_sha256": digest(PRIVATE / "key.json")})
    print("Verified and masked 360 genuine outputs.", flush=True)


if __name__ == "__main__":
    os.umask(0o077)
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (PRIVATE / "generation.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        {"freeze": freeze, "generate": generate, "mask": mask}[sys.argv[1]]()
