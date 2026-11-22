"""Reproduce the two-replicate study using the original native generators and masked PATIENTSIM reader."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import fcntl
from functools import lru_cache
import importlib.util
import json
import os
from pathlib import Path
import random
import secrets
import sys
import time

HERE = Path(__file__).resolve().parent
PRIVATE = HERE / "private"
PRIOR = HERE.parent / "english-12turn-run"
PREVIOUS = HERE.parent / "next-english-study"
IDS = tuple(f"C{n:02}" for n in range(1, 9))
ARMS = ("B", "BC", "T2")
REPS = (1, 2)
KEY = PRIVATE / "key.json"
FREEZE = HERE / "generation-freeze.json"
CASES = HERE / "cases.json"
GEN_SOURCE = PRIOR / "generation.py"
RECENT_RATE = PREVIOUS / "method/interpretation-receipt.json"

# Reuse the trace-validated WS reconnect repair and the unmodified base transports.
sys.dont_write_bytecode = True
sys.path.insert(0, str(PREVIOUS))
import resume_generation
import runner as historical

gen = historical.gen
assess = historical.assess
quota = historical.quota
assess.HERE = HERE
read, save, check, sha = gen.load, gen.save, gen.require, historical.sha
os.environ["PATH"] = str(Path.home()/".local/bin") + os.pathsep + os.environ.get("PATH", "")


def inputs():
    rows = read(CASES)
    check(len(rows) == 8 and {c["id"] for c in rows} == set(IDS), "Unexpected cases")
    check(sorted(Counter(c["stratum"] for c in rows).values()) == [2,2,2,2], "Strata changed")
    for c in rows:
        check(len(c["questions"]) == len(set(c["questions"])) == 12 and
              all(isinstance(q, str) and q.strip() for q in c["questions"]), "Incomplete English interview")
    return {c["id"]: c for c in rows}


def key():
    rows = read(KEY)
    expected = {(c,a,r) for c in IDS for a in ARMS for r in REPS}
    check(len(rows) == len({x["id"] for x in rows}) == 48 and
          {(x["case"],x["arm"],x["rep"]) for x in rows} == expected, "Incomplete blind key")
    return rows


def generation_arm(arm):
    # Encapsulation preserves the exact original ('B') native resume branch
    # for both B-based prompts. Its provenance lives in arm-specific folders.
    return "B" if arm == "BC" else arm


def turn_dir(case, arm, rep, turn):
    return PRIVATE/"generation"/f"rep{rep}"/case/arm/f"{turn:02}"


@lru_cache(maxsize=None)
def engine(arm, rep):
    check(arm in ARMS and rep in REPS, "Unplanned interview cell")
    spec = importlib.util.spec_from_file_location(f"native_{arm}_{rep}", GEN_SOURCE)
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    original, core = g.sources()
    internal = generation_arm(arm)
    prompts = {**original, internal:(HERE/(arm+".txt")).read_text()}
    g.sources = lambda: (prompts, core)
    g.ARMS = (internal,)
    g.CASE_IDS = set(IDS)
    g.CASES = CASES
    g.FREEZE = PRIVATE/"runtime"/f"rep{rep}"/(arm+".json")
    g.turn_dir = lambda c,a,t: turn_dir(c, arm, rep, t)
    g.fallback_notices = resume_generation.validate
    return g


def freeze():
    cases = inputs()
    if not KEY.is_file():
        cells=[dict(case=c,arm=a,rep=r,id="I"+secrets.token_hex(12)) for c in IDS for a in ARMS for r in REPS]
        random.SystemRandom().shuffle(cells)
        save(KEY,cells)
    key()
    original=gen.B_FILE.read_bytes()
    base=(HERE/"B.txt").read_bytes()
    candidate=(HERE/"BC.txt").read_bytes()
    rule=(HERE/"RULE.txt").read_bytes().strip()
    historical_hashes=read(PREVIOUS/"generation-freeze.json")["hashes"]
    check(base==original and sha(HERE/"T2.txt")==sha(PREVIOUS/"T2.txt"),"Original B or T2 changed")
    check(candidate.startswith(base) and candidate[len(base):].strip()==rule and b"\n" not in rule
          and rule and rule not in base,"Candidate must only append the one specified sentence")
    save(HERE/"method/design-receipt.json", {"source":"Last organization billing state observed in the prior study",
                                            "rate":read(RECENT_RATE)["rate"]})
    check(all(assess.org_blocks_overage(r) for r in read(RECENT_RATE)["rate"]),"Claude billing lock unverified")
    manifest={}
    for a in ARMS:
        g=engine(a,1); internal=generation_arm(a)
        first={}
        for cid, c in cases.items():
            prev=[]
            for t in range(1,13):
                m=g.messages(c,internal,t,prev)
                if t==1:
                    first[cid+"-"+internal]=gen.digest(gen.encode(m))
                if a in ("B","BC"):
                    other=engine("B",1).messages(c,"B",t,prev)
                    check(other[1:]==m[1:] and len(m)==2*t and m[0]["content"].encode()==
                          other[0]["content"].encode()+(candidate[len(base):] if a=="BC" else b""),
                          "Candidate changes native role messages or profile")
                    check([(v["content"],w["content"]) for v,w in zip(m[1:-1:2],m[2:-1:2])]==prev and
                          m[-1]=={"role":"user","content":c["questions"][t-1]}, "Native history probe failed")
                else:
                    standard=historical.gen.messages(c,"T2",t,prev)
                    check(m==standard,"Historical T2 input changed")
                prev.append((c["questions"][t-1],f"Offline history check {t}"))
        fh={"generator_sha256":sha(GEN_SOURCE),"cases_sha256":sha(CASES),"first_message_sha256":first}
        for rep in REPS:
            path=engine(a,rep).FREEZE
            save(path,fh)
            manifest[str(path.relative_to(HERE))]=sha(path)
    files=[Path(__file__),HERE/"B.txt",HERE/"BC.txt",HERE/"RULE.txt",HERE/"T2.txt",KEY,CASES,
           HERE/"DESIGN.ko.md",HERE/"method/design-receipt.json",RECENT_RATE,PREVIOUS/"T2.txt",
           PREVIOUS/"runner.py",PREVIOUS/"resume_generation.py",GEN_SOURCE,PRIOR/"assess.py",PRIOR/"quota.py",
           assess.RUBRIC,assess.PRIOR/"gpt/collect.py",assess.PRIOR/"opus/run.py",*gen.SOURCE_HASHES]
    for p in files:
        rel=os.path.relpath(p,PREVIOUS)
        if rel in historical_hashes:
            check(sha(p)==historical_hashes[rel],"Unexpected historical source change: "+p.name)
    manifest.update({os.path.relpath(p,HERE):sha(p) for p in files})
    save(FREEZE,{"hashes":manifest,"conditions":list(ARMS),"replicates":list(REPS),"case_count":8,
                 "primary_ratings":192,"turns_per_interview":12,"first_answers":576,
                 "source_system_sha256":{a:sha(HERE/(a+".txt")) for a in ARMS},"single_rule":rule.decode(),
                 "history":"B and BC use the original B native session collector; T2 uses the original JSON history collector."})
    print("Frozen 8 cases × 3 arms × 2 independent generations × 12 turns.",flush=True)


def verify_design():
    for p,h in read(FREEZE)["hashes"].items():
        check(sha(HERE/p)==h,"Frozen source differs: "+p)


def quota_check(op,batch):
    q=quota.read_quota(); w=q["primary"]
    check(q["limitId"]=="codex" and w["windowDurationMins"]==10080 and isinstance(w["usedPercent"],(float,int)),
          "No verified Codex week counter")
    with (HERE/"method/budget.jsonl").open("a") as f:
        f.write(json.dumps(dict(time=gen.now(),operation=op,batch=batch,percent=w["usedPercent"],reset=w["resetsAt"]))+"\n")
    check(w["usedPercent"]<66, f"Weekly usage threshold: {w['usedPercent']}%")


def claude_check():
    assess.verify_overage_lock()
    rates=read(HERE/"method/design-receipt.json")["rate"]
    # All acquired receipts, including unsuccessful batches, share the subscription.
    for p in sorted(HERE.glob("**/opus/**/attempt-*/provider.json"),key=lambda path:path.stat().st_mtime_ns):
        seen=read(p).get("rate_events",[])
        if not seen and (p.parent/"failure.json").exists() and read(p.parent/"failure.json").get("status")=="pre_response_transport":
            continue
        check(seen and all(assess.org_blocks_overage(v) for v in seen),"Claude organization billing evidence missing")
        rates=seen
    for k,threshold in (("seven_day",.66),("five_hour",.96)):
        w=rates[-1]["unifiedWindows"][k]
        check(w["resetsAt"]<=time.time() or (w["status"]!="rejected" and w["utilization"]<threshold),
              f"Claude {k} quota hold until {w['resetsAt']}")


def batches(jobs,fn,size,kind):
    for i in range(0,len(jobs),size):
        quota_check(kind,i//size+1)
        if kind=="opus":
            claude_check()
        with ThreadPoolExecutor(max_workers=size) as pool:
            list(pool.map(fn,jobs[i:i+size]))
        print(kind,min(i+size,len(jobs)),"/",len(jobs),flush=True)


def generate():
    verify_design()
    for t in range(1,13):
        jobs=[v for v in key() if not (turn_dir(v["case"],v["arm"],v["rep"],t)/"result.json").exists()]
        random.Random(f"b-plus-generate-{t}").shuffle(jobs)
        def collect(v):
            return engine(v["arm"],v["rep"]).one(v["case"],generation_arm(v["arm"]),t)
        batches(jobs,collect,8,"generate")
        print("Completed turn",t,flush=True)


def checked_dialogue(c,a,rep):
    g=engine(a,rep);internal=generation_arm(a);cid=c["id"]
    pairs=[]; sessions=set()
    for t in range(1,13):
        folder=turn_dir(cid,a,rep,t)
        packet=g.messages(c,internal,t,pairs)
        r=g.verify_result(folder,gen.digest(gen.encode(packet)))
        check(read(folder/"request.json")==packet and r["case"]==cid and r["arm"]==internal and
              r["turn"]==t and r["question"]==c["questions"][t-1],"Changed interview question or arm")
        check(sha(folder/"events.jsonl")==r["trace_sha256"] and r["visible_tool_events"]==r["exit_code"]==0 and
              (folder/"last.txt").read_text() in (r["raw"],r["raw"]+"\n"),"First generated output differs")
        pairs.append((r["question"],r["raw"]))
        actual=pairs if internal=="B" else [(packet[-1]["content"],r["raw"])]
        native=[(role,val) for q,ans in actual for role,val in (("user_message",q),("agent_message",ans))]
        check(gen.digest(gen.encode(native))==r["native_transcript_sha256"],"Provider native history hash differs")
        sessions.add(r["session"])
    check(len(sessions)==(1 if internal=="B" else 12),"Wrong native session count")
    return {"profile":c["profile"],"dialogue":[{"question":q,"answer":v} for q,v in pairs]},sessions


def mask():
    verify_design();cases=inputs(); sessions=set(); hashes={}
    for x in key():
        doc,ss=checked_dialogue(cases[x["case"]],x["arm"],x["rep"])
        check(sessions.isdisjoint(ss),"Two independent interview conditions reused the same native session")
        sessions.update(ss)
        assess.packet(doc)
        path=HERE/"blind"/(x["id"]+".json")
        save(path,doc);hashes[x["id"]]=sha(path)
    check(len(sessions)==224,"Expected 32 native B-based and 192 ephemeral T2 sessions")
    save(HERE/"blind-freeze.json",{"hashes":hashes,"generation_sessions":len(sessions),"first_answers":576})
    print("Masked 48 interviews; verified 576 first replies and 224 generation sessions.",flush=True)


def check_blind():
    f=read(HERE/"blind-freeze.json")
    check(set(f["hashes"])=={x["id"] for x in key()},"Incomplete mask")
    for uid,h in f["hashes"].items():
        check(sha(HERE/"blind"/(uid+".json"))==h,"Blind packet changed")


def judge(reader):
    verify_design(); check_blind()
    for round_num in (1,2):
        jobs=[x["id"] for x in key() if not (assess.destination(reader,round_num,x["id"])/"accepted.json").exists()]
        random.Random(f"b-plus-primary-{reader}-{round_num}").shuffle(jobs)
        batches(jobs,lambda uid:assess.collect(reader,round_num,uid),4,reader)
        print(reader,"round",round_num,"complete",flush=True)


def verify():
    mask(); expr={}; sessions=set();status={}
    for j in ("gpt","opus"):
        xs={c:{a:{} for a in ARMS} for c in IDS}; st=Counter()
        for cell in key():
            pair=[]
            for rnd in (1,2):
                r=assess.load_rating(j,rnd,cell["id"])
                check(r["status"]!="missing" and r["session"] not in sessions,"Missing first rating or reused session")
                p=assess.destination(j,rnd,cell["id"])/r["attempt"]
                check(read(p/"start.json")["system_sha256"]==assess.digest(assess.SYSTEM.encode()),"Rating system changed")
                sessions.add(r["session"]);st[r["status"]]+=1;pair.append(r["score"])
            xs[cell["case"]][cell["arm"]][str(cell["rep"])]=pair
        expr[j]=xs;status[j]=dict(st)
    check(len(sessions)==192,"Expected 192 first ratings")
    body={"first_answers":576,"total_interviews":48,"generation_sessions":224,"reader_sessions":192,
          "scores":expr,"status":status,"structure":"reader -> case -> arm -> replicate 1/2 -> round scores 1,2"}
    save(HERE/"primary-results.json",body)
    print("Verified all 192 first ratings; valid vs invalid status",status,flush=True)


if __name__=="__main__":
    os.umask(0o077)
    cli=argparse.ArgumentParser(description=__doc__)
    sub=cli.add_subparsers(dest="action",required=True)
    for cmd in ("freeze","generate","mask","verify"):sub.add_parser(cmd)
    sub.add_parser("judge").add_argument("reader",choices=("gpt","opus"))
    args=cli.parse_args()
    PRIVATE.mkdir(parents=True,exist_ok=True)
    lock=args.action+("-"+args.reader if args.action=="judge" else "")
    with (PRIVATE/(lock+".lock")).open("a") as f:
        fcntl.flock(f,fcntl.LOCK_EX)
        if args.action=="judge":judge(args.reader)
        else:{"freeze":freeze,"generate":generate,"mask":mask,"verify":verify}[args.action]()
