"""New masked corruption pairs on the previous development corpus; never edits prior outputs."""
from pathlib import Path
import random
import secrets
import sys
import runner as r

BASE=r.HERE/"calibration"
CASES=(("H01","B"),("H02","T1"),("H03","B"),("H04","T1"))

def prepare():
    previous={(v["case"],v["arm"]):v["id"] for v in r.read(r.PRIOR/"key.json")}
    kp=BASE/"key.json"
    if not kp.exists():
        r.save(kp,[{"i":i,"kind":k,"id":"I"+secrets.token_hex(9)} for i in range(4) for k in ("original","error")])
    key=r.read(kp)
    for v in key:
        i=v["i"]; body=r.read(r.PRIOR/"blind"/(previous[CASES[i]]+".json"))
        if v["kind"]=="error":
            ans=[t["answer"] for t in body["dialogue"]]
            if i==0:ans=ans[4:]+ans[:4]
            if i==1:ans=[s if j%2 else s+" I already put the receipt in that tray. I already put the receipt in that tray." for j,s in enumerate(ans,1)]
            if i==2:ans=[s if j not in (2,5,8,11) else "As your interviewer, what would you like your treatment team to know?" for j,s in enumerate(ans,1)]
            if i==3:ans=["Subjective patient report recorded as follows. "+s+" End of entry." for s in ans]
            for row,s in zip(body["dialogue"],ans):row["answer"]=s
        r.assess.packet(body)
        r.save(BASE/"blind"/(v["id"]+".json"),body)
    r.save(BASE/"method/design-receipt.json",r.read(r.HERE/"method/design-receipt.json"))
    r.save(BASE/"freeze.json",{p.name:r.sha(p) for p in sorted((BASE/"blind").glob("*.json"))})

def rate(reader):
    r.assess.HERE=BASE
    for n in (1,2):
        jobs=sorted(r.read(BASE/"key.json"),key=lambda v:v["id"])
        random.Random(f"calibration-{reader}-{n}").shuffle(jobs)
        pending=[v["id"] for v in jobs if not (r.assess.destination(reader,n,v["id"])/"accepted.json").exists()]
        r.batches(reader,pending,lambda uid:r.assess.collect(reader,n,uid),2)

def summarize():
    r.assess.HERE=BASE
    out={}
    for reader in ("gpt","opus"):
        pairs={i:{} for i in range(4)}
        for v in r.read(BASE/"key.json"):
            scores=[r.assess.load_rating(reader,i,v["id"])["score"] for i in (1,2)]
            pairs[v["i"]][v["kind"]]=scores
        dirs=[r.assess.compare(p["error"],p["original"]) for p in pairs.values()]
        out[reader]=dict(original_error_rounds=pairs,stable_degradation=dirs.count("loss"),
                         valid=sum(s is not None for p in pairs.values() for pair in p.values() for s in pair),
                         qualifies=dirs.count("loss")>=3)
    r.save(BASE/"results.json",out);print(out)
if __name__=="__main__":
    if sys.argv[1]=="prepare":prepare()
    elif sys.argv[1]=="summarize":summarize()
    else:rate(sys.argv[1])
