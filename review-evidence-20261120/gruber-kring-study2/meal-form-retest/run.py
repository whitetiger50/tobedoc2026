"""Randomize, collect isolated original ratings and verify the repeated meal experiment."""
from hashlib import sha256
import os
from pathlib import Path
import secrets
import sys

HERE = Path(__file__).resolve().parent
LEGACY = HERE.parent / "card-detail-pilot"
sys.path.insert(0, str(LEGACY))
import read_pilot as pilot

reader = pilot.reader
read = reader.read
save = reader.save
digest = reader.digest
PLAN = HERE / "plan.json"
QUESTION = "Can you tell me about the last meal you ate?"
MEMORY = " That’s mostly what I remember about it."
pilot.HERE = reader.HERE = HERE
pilot.N = 24
reader.ROOT = HERE / "readers"
reader.FROZEN = reader.ROOT / "freeze.json"
reader.BLIND = HERE / "blind.json"


def items():
    rows = []
    for food, dish in (("soup", "lentil soup"), ("tacos", "beef tacos")):
        compact = f"I had {dish} for lunch today."
        split = f"The last meal I ate was lunch today. I had {dish}."
        for form, base in (("compact", compact), ("dash", split.replace("today. I", "today—I")),
                           ("split", split)):
            for memory in (False, True):
                rows.append({"id": f"{food}-{form}-{int(memory)}", "food": food, "form": form,
                             "memory": memory, "answer": base + (MEMORY if memory else "")})
    return rows


def old_hashes():
    verification = read(LEGACY / "reader-verification.json")
    result = {name: digest(LEGACY / name) for name in ("blind.json", "scores.json", "analysis.json")}
    assert result["blind.json"] == verification["blind_sha256"]
    assert result["scores.json"] == verification["scores_sha256"]
    assert result["analysis.json"] == read(LEGACY / "release-check.json")["analysis_sha256"]
    return result


def make_plan():
    rows = items()
    uids = [{row["id"]: "U"+secrets.token_hex(12) for row in rows} for _ in range(2)]
    slots = {uid: {"item": item, "round": n} for n, group in enumerate(uids, 1)
             for item, uid in group.items()}
    schedule, orders = {}, []
    rng = secrets.SystemRandom()
    for engine in reader.ENGINES:
        schedule[engine] = []
        for idx in range(2):
            order = list(uids[idx])
            while True:
                rng.shuffle(order)
                if order not in orders and (idx == 0 or all(a != b for a,b in zip(order,orders[-1]))):
                    break
            orders.append(order)
            schedule[engine].append([uids[idx][item] for item in order])
    return {"items": rows, "question": QUESTION, "slots": slots, "schedule": schedule,
            "prior_sha256": old_hashes(), "design_sha256": digest(HERE / "DESIGN.ko.md")}


def manifest(cases):
    plan = read(PLAN)
    assert plan["items"] == items() and plan["prior_sha256"] == old_hashes()
    assert plan["question"] == QUESTION and plan["design_sha256"] == digest(HERE / "DESIGN.ko.md")
    assert reader.fixed.hashes() == reader.fixed.read(reader.fixed.MANIFEST)["sha256"]
    payloads = {uid: sha256(reader.packet_bytes(row)).hexdigest() for uid,row in cases.items()}
    assert len(set(payloads.values())) == 12
    for row in plan["items"]:
        ids = [u for u,s in plan["slots"].items() if s["item"] == row["id"]]
        assert len(ids) == 2 and {plan["slots"][u]["round"] for u in ids} == {1,2}
        assert all(cases[u] == {"question": QUESTION, "answer": row["answer"]} for u in ids)
        assert payloads[ids[0]] == payloads[ids[1]]
    orders = {}
    for engine, rounds in plan["schedule"].items():
        assert all(len(r) == 12 and all(plan["slots"][u]["round"] == idx for u in r)
                   for idx,r in enumerate(rounds,1))
        assert all(plan["slots"][a]["item"] != plan["slots"][b]["item"] for a,b in zip(*rounds))
        orders[engine] = rounds[0] + rounds[1]
        assert set(orders[engine]) == set(cases)
    return {"plan_sha256": digest(PLAN), "blind_sha256": digest(reader.BLIND), "orders": orders,
            "payload_sha256": payloads, "runner_sha256": digest(Path(__file__)),
            "parent_drivers": {path.name: digest(path) for path in (Path(reader.__file__),Path(pilot.__file__))},
            "rubric_transports_sha256": reader.fixed.hashes()}


reader.inputs_manifest = manifest


def freeze():
    if not PLAN.exists():
        save(PLAN, make_plan())
    plan = read(PLAN)
    lookup = {r["id"]:r["answer"] for r in plan["items"]}
    save(reader.BLIND, [{"uid":u, "question":QUESTION, "answer":lookup[s["item"]]}
                        for u,s in sorted(plan["slots"].items())])
    if not reader.FROZEN.exists():
        save(reader.FROZEN, {"frozen_utc": reader.now(), "spec":manifest(pilot.masked_inputs())})
    reader.load_frozen()
    print("Frozen 12 answers, 24 slots per reader, four distinct presentation orders.")


def export():
    pilot.export()
    results = read(HERE / "reader-verification.json")
    plan = read(PLAN)
    for engine, rounds in plan["schedule"].items():
        last = ""
        for uid in rounds[0] + rounds[1]:
            root = reader.ROOT / engine / uid
            attempt = root / read(root / "accepted.json")["attempt"]
            subdir = "receipts" if engine == "opus" else "meta"
            receipt = read(attempt / subdir / (uid+".json"))
            assert receipt["started_utc"] > last
            last = receipt["started_utc"]
    save(HERE / "verification.json", {**results, "plan_sha256": digest(PLAN),
         "prior_hashes_unchanged": plan["prior_sha256"] == old_hashes(),
         "ordered_starts_verified": True, "unique_question_answer_payloads": 12})


if __name__ == "__main__":
    os.umask(0o077)
    action, = sys.argv[1:]
    if action in reader.ENGINES:
        pilot.collect_and_lock(action, 1)
    else:
        {"freeze":freeze,"export":export}[action]()
