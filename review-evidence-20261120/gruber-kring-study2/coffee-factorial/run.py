"""Run the fixed Study 2 rubric on a 2×2 insertion/deletion of GK05 sentences."""
from hashlib import sha256
from itertools import permutations
import os
from pathlib import Path
from secrets import SystemRandom, token_hex
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "card-detail-pilot"
PREV = HERE.parent / "core-peripheral-repeat"
sys.path.insert(0, str(BASE))
import read_pilot as pilot

r = pilot.reader
pilot.HERE = r.HERE = HERE
pilot.N = 8
r.BLIND = HERE / "blind.json"
r.ROOT = HERE / "readers"
r.FROZEN = r.ROOT / "freeze.json"
PLAN = HERE / "plan.json"


def inputs():
    prior = r.read(PREV/"analysis.json")
    archive = r.read(PREV/"plan.json")
    previous_spec = r.read(PREV/"readers/freeze.json")["spec"]
    assert r.digest(PREV/"plan.json") == previous_spec["plan_sha256"]
    assert r.digest(PREV/"scores.json") == prior["scores_sha256"]
    assert r.digest(BASE/"scores.json") == prior["source_sha256"]["original"]["scores.json"]
    assert r.digest(BASE/"blind.json") == prior["source_sha256"]["original"]["blind.json"]
    detail_scores = HERE.parent/"detail-versus-repeat"/"scores.json"
    assert r.digest(detail_scores) == prior["source_sha256"]["previous"]["scores.json"]
    by_kind = {i["kind"]:i for i in archive["items"] if i["case"] == "GK05"}
    source, = [x for x in r.read(BASE/"blind.json") if x["uid"] == by_kind["repeat"]["old_uid"]]
    first, last = source["answer"].split(". ")
    assert first == "I grind coffee by hand every morning"
    assert last == "That’s a regular part of my morning routine."
    assert source["question"] == "Can you describe what you usually do in the morning?"
    repeat, mug = (by_kind[k]["insert"] for k in ("repeat","peripheral"))
    items = {}
    for rid, mid, key in [(False,False,"original"), (True,False,"repeat"),
                          (False,True,"mug"), (True,True,"both")]:
        middle = [s for use,s in ((rid,repeat),(mid,mug)) if use]
        answer = " ".join([first+".", *middle, last])
        assert len(answer.split()) == 15 + 10*len(middle)
        items[key] = {"question":source["question"], "answer":answer}
    assert items["original"]["answer"] == source["answer"]
    for key, kind in (("repeat","repeat"),("mug","peripheral")):
        old = by_kind[kind]
        assert items[key] == {k:old[k] for k in ("question","answer")}
        for u,s in archive["slots"].items():
            if s["item"] == old["id"]:
                assert sha256(r.packet_bytes(items[key])).hexdigest() == previous_spec["payload_sha256"][u]
    sources = [PREV/"scores.json", PREV/"plan.json", PREV/"analysis.json", BASE/"scores.json",
               BASE/"blind.json", detail_scores, HERE.parent/"nonmeal-retest"/"scores.json"]
    return items, {str(p.relative_to(HERE.parent)):r.digest(p) for p in sources}


def make_plan(items, hashes):
    rng = SystemRandom()
    possible = list(permutations(items))
    ids = [{key:"U"+token_hex(12) for key in items} for _ in range(2)]
    orders = {}
    for engine in r.ENGINES:
        first = rng.choice(possible)
        possible.remove(first)
        second = rng.choice([s for s in possible if all(a!=b for a,b in zip(first,s))])
        possible.remove(second)
        orders[engine] = [[ids[n][key] for key in seq] for n,seq in enumerate((first,second))]
    slots = {u:{"item":key,"round":n} for n,m in enumerate(ids,1) for key,u in m.items()}
    return {"items":items,"source_sha256":hashes,"slots":slots,"orders":orders}


def manifest(cases):
    p = r.read(PLAN)
    items, hashes = inputs()
    assert (items, hashes) == (p["items"], p["source_sha256"])
    assert r.fixed.hashes() == r.fixed.read(r.fixed.MANIFEST)["sha256"]
    assert {u:items[s["item"]] for u,s in p["slots"].items()} == cases
    orders = []
    for pair in p["orders"].values():
        names = []
        for n,seq in enumerate(pair,1):
            assert len(seq)==4 and all(p["slots"][u]["round"]==n for u in seq)
            keys = tuple(p["slots"][u]["item"] for u in seq)
            assert set(keys)==set(items)
            names.append(keys)
        assert all(a!=b for a,b in zip(*names))
        orders.extend(names)
    assert len(set(orders)) == 4
    return {"orders":{e:a+b for e,(a,b) in p["orders"].items()},
            "payload_sha256":{u:sha256(r.packet_bytes(d)).hexdigest() for u,d in cases.items()},
            "blind_sha256":r.digest(r.BLIND), "plan_sha256":r.digest(PLAN),
            "design_sha256":r.digest(HERE/"DESIGN.ko.md"), "runner_sha256":r.digest(Path(__file__)),
            "driver_sha256":{m.__name__:r.digest(Path(m.__file__)) for m in (r,pilot)}}


r.inputs_manifest = manifest


def freeze():
    if not PLAN.exists():
        r.save(PLAN,make_plan(*inputs()))
    p = r.read(PLAN)
    r.save(r.BLIND,[{"uid":u,**p["items"][s["item"]]} for u,s in sorted(p["slots"].items())])
    if not r.FROZEN.exists():
        r.save(r.FROZEN,{"frozen_utc":r.now(),"spec":manifest(pilot.masked_inputs())})
    r.load_frozen()
    print("Four versions verified and two rounds frozen for each reader.")


if __name__ == "__main__":
    os.umask(0o077)
    action, = sys.argv[1:]
    if action in r.ENGINES:
        pilot.collect_and_lock(action,1)
    else:
        {"freeze":freeze,"export":pilot.export}[action]()
