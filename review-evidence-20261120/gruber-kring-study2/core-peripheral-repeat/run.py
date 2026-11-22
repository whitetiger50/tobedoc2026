"""Freeze a third, peripheral detail alongside the two archived manipulations."""
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
import os
from pathlib import Path
import secrets
import sys

HERE = Path(__file__).resolve().parent
PREV = HERE.parent / "detail-versus-repeat"
spec = spec_from_file_location("previous_detail_experiment", PREV / "run.py")
old = module_from_spec(spec)
spec.loader.exec_module(old)
pilot, r = old.pilot, old.r
pilot.HERE = r.HERE = HERE
pilot.N = 24
r.BLIND = HERE / "blind.json"
r.ROOT = HERE / "readers"
r.FROZEN = r.ROOT / "freeze.json"
PLAN = HERE / "plan.json"
PERIPHERAL = {
    "GK02": "The mailbox beside the driveway was painted green.",
    "GK05": "My coffee mug has a chip along its top edge.",
    "GK07": "The studio had a strip of yellow paint along the baseboard.",
    "GK12": "The drinking fountain stood next to the gate at that playground.",
}


def stimuli():
    archive = r.read(PREV / "plan.json")
    items, source_hashes = old.stimuli()
    assert items == archive["items"] and source_hashes == archive["source_sha256"]
    freeze = r.read(PREV / "readers/freeze.json")["spec"]
    verified = r.read(PREV / "reader-verification.json")
    hashes = {p: r.digest(PREV / p) for p in (
        "scores.json", "analysis.json", "RESULTS.ko.md", "plan.json", "blind.json",
        "readers/freeze.json", "reader-verification.json")}
    assert hashes["readers/freeze.json"] == verified["reader_freeze_sha256"]
    assert hashes["scores.json"] == verified["scores_sha256"] == r.read(PREV/"analysis.json")["scores_sha256"]
    assert hashes["plan.json"] == freeze["plan_sha256"]
    assert hashes["blind.json"] == freeze["blind_sha256"]
    by_id = {i["id"]: i for i in items}
    for uid, slot in archive["slots"].items():
        i = by_id[slot["item"]]
        payload = r.packet_bytes({k:i[k] for k in ("question","answer")})
        assert sha256(payload).hexdigest() == freeze["payload_sha256"][uid]
    result = []
    for key, addition in PERIPHERAL.items():
        detail = by_id[key+"-detail"]
        repeat = by_id[key+"-repeat"]
        answer = detail["answer"].replace(detail["insert"] + " ", addition + " ", 1)
        assert answer != detail["answer"]
        assert len(old.WORDS.findall(addition)) == detail["added_words"] == repeat["added_words"]
        assert len(old.WORDS.findall(answer)) == detail["words"] == repeat["words"]
        result.extend((detail, dict(detail, id=key+"-peripheral", kind="peripheral",
                                    insert=addition, answer=answer), repeat))
    return result, {"previous": hashes, "original": source_hashes}


def make_plan(items, hashes):
    ids = [i["id"] for i in items]
    maps = [{i:"U"+secrets.token_hex(12) for i in ids} for _ in range(2)]
    rng = secrets.SystemRandom()
    seen, orders = [], {}
    for engine in r.ENGINES:
        rounds = []
        for n in range(2):
            while True:
                seq = rng.sample(ids, len(ids))
                mixed = all(len({i.split("-")[1] for i in seq[j:j+6]}) == 3 for j in (0,6))
                if mixed and seq not in seen and (not n or all(a!=b for a,b in zip(seq,seen[-1]))):
                    break
            seen.append(seq)
            rounds.append([maps[n][i] for i in seq])
        orders[engine] = rounds
    return {"items":items, "source_sha256":hashes, "orders":orders,
            "slots":{uid:{"item":i,"round":n} for n,group in enumerate(maps,1) for i,uid in group.items()}}


def manifest(cases):
    plan = r.read(PLAN)
    items, hashes = stimuli()
    assert items == plan["items"] and hashes == plan["source_sha256"]
    assert r.fixed.hashes() == r.fixed.read(r.fixed.MANIFEST)["sha256"]
    bank = {i["id"]:{k:i[k] for k in ("question","answer")} for i in items}
    assert cases == {u:bank[s["item"]] for u,s in plan["slots"].items()}
    payloads = {uid:sha256(r.packet_bytes(dialogue)).hexdigest() for uid,dialogue in cases.items()}
    assert len(payloads) == 24 and len(set(payloads.values())) == 12
    for rounds in plan["orders"].values():
        assert len(rounds)==2 and set(rounds[0]+rounds[1])==set(cases)
        for n,order in enumerate(rounds,1):
            assert len(order)==12 and all(plan["slots"][u]["round"]==n for u in order)
            assert {plan["slots"][u]["item"] for u in order} == set(bank)
    return {"orders":{e:a+b for e,(a,b) in plan["orders"].items()}, "payload_sha256":payloads,
            "blind_sha256":r.digest(r.BLIND), "plan_sha256":r.digest(PLAN),
            "design_sha256":r.digest(HERE/"DESIGN.ko.md"), "runner_sha256":r.digest(Path(__file__)),
            "driver_sha256":{k:r.digest(Path(m.__file__)) for k,m in
                             (("previous",old),("pilot",pilot),("reader",r))}}


r.inputs_manifest = manifest


def freeze():
    items, hashes = stimuli()
    if not PLAN.is_file():
        r.save(PLAN, make_plan(items,hashes))
    plan = r.read(PLAN)
    bank = {i["id"]:{k:i[k] for k in ("question","answer")} for i in items}
    r.save(r.BLIND,[{"uid":u,**bank[s["item"]]} for u,s in sorted(plan["slots"].items())])
    if not r.FROZEN.is_file():
        r.save(r.FROZEN,{"frozen_utc":r.now(),"spec":manifest(pilot.masked_inputs())})
    r.load_frozen()
    print("Verified 12 stimuli and 24 blinded slots per reader.")


if __name__ == "__main__":
    os.umask(0o077)
    action, = sys.argv[1:]
    if action in r.ENGINES:
        pilot.collect_and_lock(action,1)
    else:
        {"freeze":freeze,"export":pilot.export}[action]()
