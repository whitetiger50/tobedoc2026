"""Verify frozen specifications, first-output provenance, masking and optional behavior annotations."""
from collections import Counter
import json
from pathlib import Path
import sys
import assess
import generation as g
from dispatch import HERE, digest, make_schedule, natural_path, now, read, write

SPEC=["generation-freeze.json","generation.py","cases.json","assess.py","controls.py","quota.py",
      "method/decisions.ko.md","method/design-receipt.json","behavior/guide.txt","key.json","dispatch.py"]
def freeze():
    record={p:digest(HERE/p) for p in SPEC}
    write(HERE/"method/prescore-hashes.json",record)
def audit():
    ap=HERE/"method/transport-amendment.json"
    amendments=read(ap) if ap.exists() else {}
    assert set(amendments)<={"generation-freeze.json","generation.py"}
    for f,sha in read(HERE/"method/prescore-hashes.json").items():
        if f in amendments:
            assert sha==amendments[f]["old"]
            sha=amendments[f]["new"]
        if digest(HERE/f)!=sha:
            raise RuntimeError(f"Review frozen specification: {f}")
    cases={c["id"]:c for c in read(HERE/"cases.json")}
    ids=make_schedule()
    natural=[k for k in ids if k["arm"] in ("B","T0","T1")]
    sessions=set()
    outputs=Counter()
    blind_hashes={}
    for k in ids:
        f=HERE/"blind"/(k["id"]+".json")
        if not f.exists():continue
        blind=read(f); assess.packet(blind)
        case=cases[k["case"]]
        assert blind["profile"]==case["profile"] and [t["question"] for t in blind["dialogue"]]==case["questions"]
        blind_hashes[k["id"]]=digest(f)
    for k in natural:
        c,a,uid=k["case"],k["arm"],k["id"]
        previous=[]; active_session=None
        for i in range(1,13):
            f=natural_path(c,a,i)
            if not f.exists():continue
            row=g.verify_result(f.parent)
            packet=g.messages(cases[c],a,i,previous)
            assert g.load(f.parent/"request.json")==packet and digest(f.parent/"events.jsonl")==row["trace_sha256"]
            assert row["turn"]==i and row["arm"]==a and row["case"]==c and row["visible_tool_events"]==0
            if a=="B" and i>1:
                assert active_session==row["session"]
            else:
                assert row["session"] not in sessions
                sessions.add(row["session"]);active_session=row["session"]
            previous.append((row["question"],row["raw"]))
            if uid in blind_hashes:
                blind=read(HERE/"blind"/(uid+".json"))
                assert row["raw"]==blind["dialogue"][i-1]["answer"]
            outputs[c[0]+"/"+a]+=1
    result=assess.analyze()
    summary={"checked_utc":now(),"validated_first_turn_outputs":sum(outputs.values()),
             "turns_by_split_and_arm":dict(sorted(outputs.items())),"generation_sessions":len(sessions),
             "masked_inputs":len(blind_hashes),"masked_input_sha256":blind_hashes,
             "reader_sessions_with_first_forms":result["unique_sessions"],
             "reader_status":{m:x["status_counts"] for m,x in result["readers"].items()},
             "heldout_cross_reader_exact":result["heldout_cross_reader_exact_same_round"]}
    (HERE/"verification.json").write_text(json.dumps(summary,indent=2)+"\n")
    print({k:v for k,v in summary.items() if k!="masked_input_sha256"})
if __name__=="__main__":
    {"freeze":freeze,"audit":audit}[sys.argv[1]]()
