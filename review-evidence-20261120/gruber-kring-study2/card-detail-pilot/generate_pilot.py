"""Freeze the assigned slots, collect each first reply, then mask the English corpus."""
import fcntl
import json
import os
from pathlib import Path
import secrets
import sys

import prepare_plan as plan

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "main"))
import generate as previous

PRIVATE = HERE / "private"
SCHEDULE = PRIVATE / "schedule.json"
FREEZE = HERE / "freeze.json"
save = previous.save
load = plan.load
digest = plan.digest


def check_inputs():
    path = HERE / "plan.json"
    assert digest(path) == "6842bc038634f681ab5db7aeb3fb1625c45407bfa1123991b635a7b96b5e6cde"
    assert load(path) == plan.build()
    return load(path)


def freeze():
    inputs = check_inputs()
    private_orig = plan.MAIN / "private/messages"
    if not SCHEDULE.exists():
        rng = secrets.SystemRandom()
        items = inputs["items"].copy()
        rng.shuffle(items)
        slots = []
        for item in items:
            versions = ("core", "full") if rng.getrandbits(1) else ("full", "core")
            arms = plan.ARMS.copy()
            rng.shuffle(arms)
            for arm in arms:
                record = item["packets_sha256"][arm]
                for version in versions:
                    job = "P%03d" % (len(slots) + 1)
                    slots.append({"job": job, "uid": "U" + secrets.token_hex(12), "case": item["case"],
                                  "topic": item["topic"], "arm": arm, "version": version,
                                  "original_job": record["original_job"]})
        assert len(slots) == len({s["uid"] for s in slots}) == 72
        save(SCHEDULE, slots)
    slots = load(SCHEDULE)
    packages = {}
    for s in slots:
        row = next(i for i in inputs["items"] if i["case"] == s["case"])
        ref = row["packets_sha256"][s["arm"]]
        assert s["original_job"] == ref["original_job"] and s["topic"] == row["topic"]
        packet = load(private_orig / (s["original_job"] + ".json"))
        if s["version"] == "core":
            body = json.loads(packet["user"])
            body["patient"]["facts"] = body["patient"]["facts"][:1]
            packet["user"] = plan.canonical(body).decode()
        messages = [{"role": role, "content": packet[role]} for role in ("system", "user")]
        assert previous.cards.builder.sha(plan.canonical(messages)) == ref[s["version"]]
        path = PRIVATE / "messages" / (s["job"] + ".json")
        save(path, packet)
        packages[s["job"]] = digest(path)
    for i in range(0, 72, 6):
        group = slots[i:i+6]
        assert len({s["case"] for s in group}) == 1
        pairs = list(zip(group[::2], group[1::2]))
        assert {a["arm"] for a,b in pairs} == set(plan.ARMS)
        assert all(a["arm"] == b["arm"] and a["version"] != b["version"] for a,b in pairs)
        assert len({a["version"] for a,b in pairs}) == 1
    save(FREEZE, {"frozen_utc": load(FREEZE)["frozen_utc"] if FREEZE.exists() else
                  previous.datetime.now(previous.timezone.utc).isoformat(),
                  "schedule_sha256": digest(SCHEDULE), "protocol_sha256": digest(HERE / "DESIGN.ko.md"),
                  "plan_sha256": digest(HERE / "plan.json"), "packet_sha256": packages,
                  "slots": 72, "independent_card_coins": 12, "model": previous.transport.MODEL,
                  "reasoning": "medium", "one_empty_session_per_slot": True,
                  "sampling": "provider defaults", "order": "frozen adjacent pairs, serial launches"})


def jobs():
    frozen = load(FREEZE)
    assert frozen["schedule_sha256"] == digest(SCHEDULE)
    assert frozen["protocol_sha256"] == digest(HERE / "DESIGN.ko.md")
    assert frozen["plan_sha256"] == digest(HERE / "plan.json")
    return [{**s, "packet_sha256": frozen["packet_sha256"][s["job"]]} for s in load(SCHEDULE)]


def collect():
    for n, job in enumerate(jobs(), 1):
        dest = PRIVATE / "generated" / (job["job"] + ".json")
        marker = PRIVATE / "starts" / (job["job"] + ".json")
        if not dest.exists():
            if marker.exists():
                raise RuntimeError("Interrupted first call needs transport review: " + job["job"])
            save(marker, {"started_utc": previous.datetime.now(previous.timezone.utc).isoformat()})
            previous.transport.generate_one(job)
        previous.verify(job)
        if n % 6 == 0:
            print(f"Verified {n}/72 first replies", flush=True)
    mask()


def mask():
    _, questions = previous.cards.script()
    blind, sessions = [], set()
    for job in jobs():
        rec = previous.verify(job)
        assert rec["session"] not in sessions
        sessions.add(rec["session"])
        blind.append({"uid": job["uid"], "question": questions[job["topic"]][1], "answer": rec["raw"]})
    assert len(blind) == len(sessions) == 72
    save(HERE / "blind.json", sorted(blind, key=lambda r: r["uid"]))
    save(HERE / "generation-verification.json", {"raw_answers_verified": 72, "unique_sessions": 72,
         "blind_sha256": digest(HERE / "blind.json"), "model": previous.transport.MODEL,
         "reasoning": "medium", "tool_events": 0, "schedule_sha256": digest(SCHEDULE)})


if __name__ == "__main__":
    os.umask(0o077)
    PRIVATE.mkdir(exist_ok=True, mode=0o700)
    previous.PRIVATE = previous.transport.PRIVATE = PRIVATE
    previous.FREEZE = FREEZE
    with (PRIVATE / "generation.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        {"freeze": freeze, "generate": collect, "mask": mask}[sys.argv[1]]()
