"""Local scheduling, subscription guard and source masking for the 12-turn study."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time
from quota import read_quota

HERE = Path(__file__).resolve().parent
def read(path):
    return json.loads(path.read_text())
def write(path,obj):
    data = json.dumps(obj,ensure_ascii=False,indent=2)+"\n"
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if path.read_text()!=data:
            raise ValueError("Frozen content changed: "+str(path))
    else:
        with path.open("x") as f:
            f.write(data)
def now():
    return datetime.now(timezone.utc).isoformat()
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def natural_path(case,arm,i):
    return HERE/"private/generation"/case/arm/f"{i:02d}"/"result.json"
def guard():
    quota=read_quota()
    week=quota["primary"]
    if week["windowDurationMins"]!=10080 or week["resetsAt"]!=1795512455 or not isinstance(week["usedPercent"],(int,float)):
        raise RuntimeError("Weekly window changed or unavailable")
    with (HERE/"method/quota.jsonl").open("a") as f:
        f.write(json.dumps({"utc":now(),"used":week["usedPercent"],"window":week["resetsAt"]})+"\n")
    # First account read 44%; protect against integer rounding, in-flight sessions and report cost.
    if week["usedPercent"]>=52:
        raise RuntimeError("Research spending stop reached")
    return week["usedPercent"]
def invoke(args):
    p=subprocess.run([sys.executable,*map(str,args)],cwd=HERE,capture_output=True,text=True)
    if p.returncode:
        raise RuntimeError(str(args)+" "+(p.stderr+" "+p.stdout)[-1000:])
def make_schedule():
    cases=read(HERE/"cases.json")
    cells=[(c["id"],a) for c in cases for a in (("T0","Length","Error") if c["id"].startswith("D") else ("B","T0","T1"))]
    assert len(cells)==len(set(cells))==36
    path=HERE/"key.json"
    if path.exists():
        key=read(path)
        assert {(k["case"],k["arm"]) for k in key}==set(cells) and len({k["id"] for k in key})==36
    else:
        import secrets
        key=[dict(case=c,arm=a,id="I"+secrets.token_hex(7)) for c,a in cells]
        random.SystemRandom().shuffle(key)
        write(path,key)
    return key
def run_batches(jobs,size):
    done=0
    for start in range(0,len(jobs),size):
        used=guard()
        batch=jobs[start:start+size]
        errors=[]
        with ThreadPoolExecutor(max_workers=size) as pool:
            for f in as_completed([pool.submit(invoke,args) for args in batch]):
                try:f.result()
                except Exception as exc:errors.append(str(exc))
        done+=len(batch)
        print(f"{now()} {done}/{len(jobs)} requested, weekly used {used}%",flush=True)
        if errors:
            raise RuntimeError("\n".join(errors))
def generate(split):
    key=make_schedule()
    pairs=[(k["case"],k["arm"]) for k in key if k["case"].startswith(split) and k["arm"] in ("B","T0","T1")]
    for n in range(1,13):
        shuffled=sorted(pairs)
        random.Random(f"interview-20261121-{split}-{n}").shuffle(shuffled)
        run_batches([["generation.py","one",c,a,n] for c,a in shuffled if not natural_path(c,a,n).exists()],min(6,len(shuffled)))
def mask(split):
    cases={c["id"]:c for c in read(HERE/"cases.json")}
    for k in make_schedule():
        c,a,i=k["case"],k["arm"],k["id"]
        if not c.startswith(split):continue
        q=cases[c]["questions"]
        if a in ("Length","Error"):
            answers=read(HERE/"controls"/(c+"-"+a+".json"))["answers"]
        else:
            records=[read(natural_path(c,a,j)) for j in range(1,13)]
            assert [r["question"] for r in records]==q
            answers=[r["raw"] for r in records]
        assert len(q)==len(answers)==12 and all(isinstance(s,str) and s.strip() for s in answers)
        blind={"profile":cases[c]["profile"],"dialogue":[{"question":x,"answer":y} for x,y in zip(q,answers)]}
        write(HERE/"blind"/(i+".json"),blind)
        if split=="H":
            write(HERE/"behavior"/"input"/(i+".json"),{**blind,"opportunities":cases[c]["opportunities"]})
def judge(split):
    inputs=make_schedule()
    ids=sorted(k["id"] for k in inputs if k["case"].startswith(split))
    jobs=[]
    for r in (1,2):
        columns=[]
        for reader in ("gpt","opus"):
            order=ids[:]
            random.Random(f"{reader}-independent-{split}-{r}-20261121").shuffle(order)
            columns.append([["assess.py","one",reader,str(r),i] for i in order if not (HERE/"ratings"/reader/f"r{r}"/i/"accepted.json").exists()])
        import itertools
        jobs.extend(x for row in itertools.zip_longest(*columns) for x in row if x)
    run_batches(jobs,4)
if __name__=="__main__":
    os.umask(0o077)
    action,split=sys.argv[1:]
    assert split in ("D","H")
    {"generate":generate,"mask":mask,"judge":judge}[action](split)
