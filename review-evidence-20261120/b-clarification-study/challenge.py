"""Read the archived fictional defect controls in fresh source-blind sessions."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import random
import secrets
import sys
import time
import fcntl

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "challenge"
PRIOR = ROOT.parent / "next-english-study"
sys.path.insert(0, str(ROOT.parent / "english-12turn-run"))
import assess
import quota

os.environ['PATH'] = str(Path.home()/'.local/bin')+os.pathsep+os.environ['PATH']
assess.HERE = BASE
read, write, check = assess.read, assess.write, assess.require

def prep():
    source = PRIOR/"calibration"
    old = read(source/"freeze.json")
    keyfile = BASE/"mapping.json"
    if keyfile.exists(): return
    rows = []
    for v in read(source/"key.json"):
        name = v["id"]+".json"
        raw = (source/"blind"/name).read_bytes()
        check(hashlib.sha256(raw).hexdigest()==old[name],"Changed calibration source")
        uid = "C"+secrets.token_hex(10)
        (BASE/"blind").mkdir(parents=True,exist_ok=True)
        (BASE/"blind"/(uid+".json")).write_bytes(raw)
        rows.append({**v,"id":uid,"sha256":old[name]})
    write(BASE/"method/design-receipt.json",{"rate":read(PRIOR/"method/interpretation-receipt.json")["rate"]})
    write(keyfile,rows)

def read_controls():
    rows=read(BASE/"mapping.json")
    check(len(rows)==8 and len({r["id"] for r in rows})==8,"Control count")
    for r in rows:
        check(hashlib.sha256((BASE/"blind"/(r["id"]+".json")).read_bytes()).hexdigest()==r["sha256"],"Control hash")
    return rows

def collect(reader):
    rows=read_controls()
    for n in (1,2):
        ids=sorted(r["id"] for r in rows)
        random.Random(f"clarification-{reader}-{n}").shuffle(ids)
        for i in range(0,len(ids),3):
            jobs=[u for u in ids[i:i+3] if not (assess.destination(reader,n,u)/"accepted.json").exists()]
            if not jobs:continue
            w=quota.read_quota()["primary"]
            check(w["windowDurationMins"]==10080 and w["usedPercent"]<66,"Subscription usage guard")
            if reader=="opus":
                paths=sorted((BASE/"ratings/opus").glob("r*/*/attempt-*/provider.json"),key=lambda p:p.stat().st_mtime_ns)
                rate=read(paths[-1])["rate_events"][-1] if paths else read(BASE/"method/design-receipt.json")["rate"][-1]
                check(assess.org_blocks_overage(rate),"Subscription only")
                for k,t in (("five_hour",.96),("seven_day",.66)):
                    v=rate["unifiedWindows"][k]
                    check(v["resetsAt"]<=time.time() or v["utilization"]<t,"Claude usage guard")
            with ThreadPoolExecutor(max_workers=3) as pool:
                list(pool.map(lambda u:assess.collect(reader,n,u),jobs))
    print(reader, "16 control first forms", flush=True)

def summarize():
    result={};seen=set()
    for j in ("gpt","opus"):
        pairs={}
        for v in read_controls():
            vals=[assess.load_rating(j,n,v["id"]) for n in (1,2)]
            for e in vals:
                check(e["status"]!="missing" and e["session"] not in seen,"Missing or duplicate assessment")
                seen.add(e["session"])
            pairs.setdefault(v["i"],{})[v["kind"]]=[e["score"] for e in vals]
        wins=sum(assess.compare(v["error"],v["original"])=="loss" for v in pairs.values())
        result[j]={"pairs":pairs,"stable_degradation":wins,"qualified":wins>=3}
    write(BASE/"results.json",result);print(result)
if __name__=='__main__':
    os.umask(0o077)
    arg=argparse.ArgumentParser();arg.add_argument('cmd',choices=['prepare','gpt','opus','summarize'])
    action=arg.parse_args().cmd
    BASE.mkdir(exist_ok=True)
    with (BASE/(action+'.lock')).open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if action=='prepare':prep()
        elif action=='summarize':summarize()
        else:collect(action)
