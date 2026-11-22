"""Verify and repeat the original masked packets for nonmeal disagreements."""
from hashlib import sha256
import os
from pathlib import Path
import secrets
import sys

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "card-detail-pilot"
sys.path.insert(0, str(OLD))
import read_pilot as pilot

r = pilot.reader
pilot.HERE = r.HERE = HERE
pilot.N = 16
r.BLIND = HERE / "blind.json"
r.ROOT = HERE / "readers"
r.FROZEN = r.ROOT / "freeze.json"
PLAN = HERE / "plan.json"


def original():
    hashes = {s: r.digest(OLD / s) for s in
              ("blind.json", "scores.json", "analysis.json", "RESULTS.ko.md", "private/schedule.json",
               "readers/freeze.json")}
    check = r.read(OLD / "reader-verification.json")
    assert hashes["scores.json"] == check["scores_sha256"]
    assert hashes["blind.json"] == check["blind_sha256"]
    assert hashes["readers/freeze.json"] == check["reader_freeze_sha256"]
    assert hashes["analysis.json"] == r.read(OLD / "release-check.json")["analysis_sha256"]
    assert hashes["private/schedule.json"] == r.read(OLD / "generation-verification.json")["schedule_sha256"]
    bank = {row["uid"]: row for row in r.read(OLD / "blind.json")}
    scores = {(row["uid"],row["reader"]): row["elaboration"] for row in r.read(OLD / "scores.json")}
    jobs = r.read(OLD / "private/schedule.json")
    paired = {(j["case"], j["arm"], j["version"]): j for j in jobs}
    rows = []
    for job in jobs:
        uid = job["uid"]
        if job["topic"] == "meal" or scores[uid,"opus"] == scores[uid,"gpt"]:
            continue
        assert job["version"] == "core"
        control = paired[job["case"],job["arm"],"full"]
        assert bank[uid]["question"] == bank[control["uid"]]["question"]
        for item, group in ((job,"target"),(control,"control")):
            ref = item["uid"]
            baseline = [scores[ref,e] for e in r.ENGINES]
            assert baseline == [1,1] if group == "control" else baseline[0] > baseline[1]
            rows.append({"old_uid":ref,"group":group,"case":item["case"],"arm":item["arm"],
                         "topic":item["topic"],"original_scores":baseline})
    assert len(rows) == 8 and {i["case"] for i in rows} == {"GK02","GK05","GK07","GK12"}
    return sorted(rows, key=lambda i: (i["case"],i["group"])), bank, hashes


def freeze():
    items, bank, hashes = original()
    if not PLAN.exists():
        slots = [{i["old_uid"]: "U"+secrets.token_hex(12) for i in items} for _ in range(2)]
        groups = {i["old_uid"]:i["group"] for i in items}
        orders, arrays = {}, []
        for engine in r.ENGINES:
            orders[engine] = []
            for n in range(2):
                ids = list(groups)
                while True:
                    secrets.SystemRandom().shuffle(ids)
                    if (ids not in arrays and all(len({groups[u] for u in part})==2 for part in (ids[:4],ids[4:]))
                        and (not n or all(a!=b for a,b in zip(arrays[-1],ids)))):
                        break
                arrays.append(ids)
                orders[engine].append([slots[n][u] for u in ids])
        r.save(PLAN,{"items":items,"slots":{uid:{"old_uid":old,"round":n} for n,m in enumerate(slots,1)
                                            for old,uid in m.items()},"orders":orders,"source_sha256":hashes})
    plan = r.read(PLAN)
    assert plan["items"] == items and plan["source_sha256"] == hashes
    r.save(r.BLIND,[{**bank[slot["old_uid"]],"uid":uid} for uid,slot in sorted(plan["slots"].items())])
    if not r.FROZEN.exists():
        r.save(r.FROZEN,{"frozen_utc":r.now(),"spec":manifest(pilot.masked_inputs())})
    r.load_frozen()
    print("Verified eight original packets and two masked rounds per reader.")


def manifest(cases):
    plan = r.read(PLAN)
    items, _, hashes = original()
    assert plan["items"] == items and plan["source_sha256"] == hashes
    assert r.fixed.hashes() == r.fixed.read(r.fixed.MANIFEST)["sha256"]
    expected = r.read(OLD / "readers/freeze.json")["spec"]["payload_sha256"]
    payloads = {u:sha256(r.packet_bytes(d)).hexdigest() for u,d in cases.items()}
    assert len(cases) == 16 and len(set(payloads.values())) == 8
    assert all(val == expected[plan["slots"][u]["old_uid"]] for u,val in payloads.items())
    for rounds in plan["orders"].values():
        assert len(rounds)==2 and set(rounds[0]+rounds[1])==set(cases)
        for n, order in enumerate(rounds,1):
            assert len(order)==8 and all(plan["slots"][u]["round"]==n for u in order)
            assert {plan["slots"][u]["old_uid"] for u in order} == {i["old_uid"] for i in items}
    return {"orders":{e:rounds[0]+rounds[1] for e,rounds in plan["orders"].items()},
            "payload_sha256":payloads,"matched_old_payloads":8,"source_sha256":hashes,
            "blind_sha256":r.digest(r.BLIND),"plan_sha256":r.digest(PLAN),
            "design_sha256":r.digest(HERE/"DESIGN.ko.md"),"runner_sha256":r.digest(Path(__file__)),
            "driver_sha256":{p.name:r.digest(p) for p in (Path(pilot.__file__),Path(r.__file__))}}


r.inputs_manifest = manifest


if __name__ == "__main__":
    os.umask(0o077)
    action, = sys.argv[1:]
    if action in r.ENGINES:
        pilot.collect_and_lock(action, 1)
    else:
        {"freeze":freeze, "export":pilot.export}[action]()
