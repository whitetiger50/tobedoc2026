"""Freeze word-matched variants and run isolated blind readings using the prior rubric."""
import os
from pathlib import Path
import re
import secrets
import sys
from hashlib import sha256

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "card-detail-pilot"
PREVIOUS = HERE.parent / "nonmeal-retest"
sys.path.insert(0, str(OLD))
import read_pilot as pilot

r = pilot.reader
pilot.HERE = r.HERE = HERE
pilot.N = 16
r.BLIND = HERE / "blind.json"
r.ROOT = HERE / "readers"
r.FROZEN = r.ROOT / "freeze.json"
PLAN = HERE / "plan.json"
WORDS = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)*")
INSERTIONS = {
    "GK02": ("The dog stopped just before it reached me.",
             "I remember the dog charging right toward me."),
    "GK05": ("I stop grinding when the grounds look like coarse sand.",
             "Grinding coffee by hand is part of my morning routine."),
    "GK07": ("I realized my mistake when the instructor announced the class name.",
             "I realized I was in the wrong class at that studio."),
    "GK12": ("I’d mixed the exact shade of blue I was aiming for.",
             "I was pleased with how the mural I painted turned out."),
}


def stimuli():
    prior = r.read(PREVIOUS / "analysis.json")
    hashes = {name:r.digest(OLD / name) for name in prior["source_sha256"]}
    assert hashes == prior["source_sha256"]
    assert prior["new_scores_sha256"] == r.digest(PREVIOUS / "scores.json")
    hashes["retest_analysis"] = r.digest(PREVIOUS / "analysis.json")
    hashes["retest_scores"] = prior["new_scores_sha256"]
    bank = {x["uid"]: x for x in r.read(OLD / "blind.json")}
    items = []
    for row in prior["rows"]:
        if row["group"] != "target":
            continue
        cid = row["case"]
        source = bank[row["old_uid"]]
        first, separator, tail = source["answer"].partition(". ")
        assert separator and tail
        assert row["exact_rounds"] == 2 and row["opus_higher_rounds"] == 2
        additions = INSERTIONS[cid]
        assert len(WORDS.findall(additions[0])) == len(WORDS.findall(additions[1]))
        for kind, addition in zip(("detail","repeat"),additions):
            assert addition.endswith(".") and addition.count(".") == 1
            answer = first + separator + addition + " " + tail
            assert answer.replace(addition + " ", "", 1) == source["answer"]
            items.append({"id":cid+"-"+kind,"case":cid,"kind":kind,"old_uid":row["old_uid"],
                          "question":source["question"], "answer":answer,"insert":addition,
                          "added_words":len(WORDS.findall(addition)), "words":len(WORDS.findall(answer)),
                          "before":row["original_scores"]})
    assert len(items) == 8 and {i["case"] for i in items} == set(INSERTIONS)
    return items, hashes


def make_plan(items, hashes):
    ids = [i["id"] for i in items]
    maps = [{i:"U"+secrets.token_hex(12) for i in ids} for _ in range(2)]
    seen, orders = [], {}
    rng = secrets.SystemRandom()
    for e in r.ENGINES:
        orders[e] = []
        for n in range(2):
            while True:
                seq = rng.sample(ids,len(ids))
                mixed = all(len({i.split("-")[1] for i in seq[j:j+4]})==2 for j in (0,4))
                if mixed and seq not in seen and (not n or all(a!=b for a,b in zip(seq,seen[-1]))):
                    break
            seen.append(seq)
            orders[e].append([maps[n][item] for item in seq])
    return {"items":items, "source_sha256":hashes, "orders":orders,
            "slots":{u:{"item":item,"round":n} for n,g in enumerate(maps,1) for item,u in g.items()}}


def manifest(cases):
    plan = r.read(PLAN)
    items, hashes = stimuli()
    assert items == plan["items"] and hashes == plan["source_sha256"]
    assert r.fixed.hashes() == r.fixed.read(r.fixed.MANIFEST)["sha256"]
    by_id = {i["id"]:i for i in items}
    for uid, slot in plan["slots"].items():
        src = by_id[slot["item"]]
        assert cases[uid] == {"question":src["question"],"answer":src["answer"]}
    payloads = {u:sha256(r.packet_bytes(d)).hexdigest() for u,d in cases.items()}
    assert len(payloads) == 16 and len(set(payloads.values())) == 8
    for rounds in plan["orders"].values():
        assert len(rounds)==2 and set(rounds[0]+rounds[1])==set(cases)
        for n, order in enumerate(rounds,1):
            assert len(order)==8 and all(plan["slots"][u]["round"]==n for u in order)
            assert {plan["slots"][u]["item"] for u in order}==set(by_id)
    return {"orders":{e:x[0]+x[1] for e,x in plan["orders"].items()}, "payload_sha256":payloads,
            "blind_sha256":r.digest(r.BLIND), "plan_sha256":r.digest(PLAN),
            "design_sha256":r.digest(HERE/"DESIGN.ko.md"),"runner_sha256":r.digest(Path(__file__)),
            "driver_sha256":{p.name:r.digest(p) for p in (Path(pilot.__file__),Path(r.__file__))}}


r.inputs_manifest = manifest


def freeze():
    items, hashes = stimuli()
    if not PLAN.is_file():
        r.save(PLAN,make_plan(items,hashes))
    plan = r.read(PLAN)
    bank = {i["id"]:{"question":i["question"],"answer":i["answer"]} for i in items}
    r.save(r.BLIND,[{"uid":u,**bank[s["item"]]} for u,s in sorted(plan["slots"].items())])
    if not r.FROZEN.is_file():
        r.save(r.FROZEN,{"frozen_utc":r.now(),"spec":manifest(pilot.masked_inputs())})
    r.load_frozen()
    print("Frozen matched inputs:", [(i["id"],i["added_words"],i["words"]) for i in items])


if __name__ == "__main__":
    os.umask(0o077)
    action, = sys.argv[1:]
    if action in r.ENGINES:
        pilot.collect_and_lock(action,1)
    else:
        {"freeze":freeze,"export":pilot.export}[action]()
