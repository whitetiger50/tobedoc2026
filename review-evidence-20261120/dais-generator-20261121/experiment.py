"""DAIS-C first-question experiment. Network inference is confined to generate."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import random
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

HERE = Path(__file__).resolve().parent
EV = HERE.parent
PRIVATE = HERE / "private"
sys.path.insert(0, str(EV / "dais-paired-20261121"))
import run as paired
from collect import module, digest

PROFILE_DIR = EV.parent / "tobedoc2026/docs/2026-11-20-english-clinical-profile"
builder = module("prompt_builder", PROFILE_DIR / "generation.py")
study = module("case_profiles", PROFILE_DIR / "study.py")
prior_gpt = module("isolated_gpt", EV / "boundary-calibration-20261121/gpt/collect.py")
SOURCE = EV.parent / "persona-audit-20261120T072413385108Z"
ARMS = ("developed", "base", "short")
MODEL = "gpt-6.1-sol"
SHORT_LINE = "Keep your reply brief and vague."


def dump(path, content):
    if path.is_file():
        if json.loads(path.read_text()) != content:
            raise ValueError("Immutable file differs: "+path.name)
        return
    path.parent.mkdir(exist_ok=True, parents=True, mode=0o700)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex)
    temp.write_text(json.dumps(content, ensure_ascii=False, indent=2)+"\n")
    os.replace(temp, path)


def data_cases():
    groups, _, tasks = paired.load_cases()
    return groups, {p: t[0] for p,t in tasks["type"].EXAMPLES.items()}


def prepare():
    groups, dialogues = data_cases()
    cards = json.loads((HERE/"cards.json").read_text())
    assert len(cards)==14 and len({c["id"] for c in cards})==14
    random.Random("DAIS-C-v1-independent-cards").shuffle(cards)
    profiles = {}
    for group in ("Q2", "Q3"):
        people = sorted(p for p in groups if groups[p]==group)
        styles = ["usual"]*3 + ["associative"]*2 + ["low_elaboration"]*2
        random.Random("DAIS-C-v1-profiles-"+group).shuffle(styles)
        profiles.update(zip(people,styles))
    jobs, inputs, systems = [], {}, {}
    triples = [(p,arm,rep) for p in sorted(groups) for arm in ARMS for rep in (1,2,3)]
    random.Random("DAIS-C-v1-generation-interleaved").shuffle(triples)
    assignment = dict(zip(sorted(groups),cards))
    for idx, (person,arm,rep) in enumerate(triples,1):
        card = assignment[person]
        communication = study.case_input("C01",profiles[person])["communication"]
        communication.update(spontaneity="You are willing to speak freely about familiar subjects.",
                             guardedness="You are comfortable sharing these ordinary experiences.")
        dto = {"patient":{"case_id":card["id"], "partition":"development",
               "provenance":"independently_authored_fictional_english_case",
               "facts":[{"id":f"F{i}", "kind":"background","content":v,"patient_knows":True,
                         "disclosure":"on_topic"} for i,v in enumerate(card["facts"],1)],
               "self_understanding":card["self_understanding"]},"communication":communication}
        condition = "development_v02" if arm=="developed" else "role_only_ablation"
        packet = builder.render(SOURCE,dto,[],dialogues[person]["question"],condition,{})
        system, body = [m["content"] for m in packet["messages"]]
        if arm=="short":
            system = system.rstrip("\n")+"\n\n"+SHORT_LINE+"\n"
        ident = f"G{idx:03}"
        dump(PRIVATE/"messages"/(ident+".json"),{"system":system,"user":body})
        assert person not in inputs or inputs[person] == body
        assert arm not in systems or systems[arm] == system
        inputs[person],systems[arm]=body,system
        jobs.append({"job":ident,"person":person,"arm":arm,"rep":rep,"question":groups[person],
                     "style":profiles[person],"card":card["id"],"packet_sha256":digest(PRIVATE/"messages"/(ident+".json"))})
    assert len(jobs)==126 and systems["short"]==systems["base"].rstrip("\n")+"\n\n"+SHORT_LINE+"\n"
    dump(PRIVATE/"schedule.json",jobs)
    dump(HERE/"freeze.json",{"n":126,"model":MODEL,"same_DTOs":len(inputs),"history_turns":0,
         "cards_sha256":digest(HERE/"cards.json"),"schedule_sha256":digest(PRIVATE/"schedule.json"),
         "method_sha256":digest(HERE/"DESIGN.ko.md"),"system_sha256":{a:builder.sha(s.encode()) for a,s in systems.items()},
         "builder_sha256":digest(PROFILE_DIR/"generation.py"),"source_sha256":builder.SOURCE_SHA256,
         "source_module":builder.MODULE_VERSION,"reasoning_effort":"medium","repeats":3,
         "sampling":"Provider defaults; temperature and RNG seed not exposed."})
    print("Frozen balanced generation packets:",len(jobs),"paired inputs:",len(inputs))


def generate_one(job):
    ident = job["job"]
    destination = PRIVATE/"generated"/(ident+".json")
    if destination.exists():
        return
    path = PRIVATE/"messages"/(ident+".json")
    assert digest(path)==job["packet_sha256"]
    msg = json.loads(path.read_text())
    with tempfile.TemporaryDirectory(dir="/private/tmp",prefix="dais-gen-") as temp:
        scratch=Path(temp); work=scratch/"work"; work.mkdir()
        cfg=scratch/"config"; cfg.mkdir(mode=0o700)
        (cfg/"auth.json").symlink_to(Path.home()/".codex/auth.json")
        shutil.copyfile(Path.home()/".codex/models_cache.json",cfg/"models_cache.json")
        system = scratch/"system.txt"; system.write_text(msg["system"])
        last = scratch/"last.txt"
        env={k:os.environ[k] for k in ("PATH","HOME","USER","LOGNAME","TMPDIR","LANG") if k in os.environ}
        env["CODEX_HOME"]=str(cfg)
        cmd=["codex","--no-daemon","-a","never","exec","--ignore-user-config","--ignore-rules",
             "--ephemeral","--sandbox","read-only","--skip-git-repo-check","--model",MODEL,
             "--cd",str(work),"--color","never","--output-last-message",str(last),
             "--enable","skip_host_skill_discovery","--enable","omit_skill_descriptions",
             "-c",'web_search="disabled"',"-c","mcp_servers={}","-c","project_doc_max_bytes=0",
             "-c",'forced_login_method="chatgpt"',"-c",'model_reasoning_effort="medium"',
             "-c","model_instructions_file="+json.dumps(str(system))]
        for feature in prior_gpt.DISABLED:
            cmd+=["--disable",feature]
        stamp=datetime.now(timezone.utc).isoformat()
        call=subprocess.run(cmd+["-"],input=msg["user"],cwd=work,env=env,capture_output=True,text=True,timeout=190)
        def header(key):
            match=re.search(r"^"+re.escape(key)+r":\s*(.+?)\s*$",call.stderr,re.M)
            return match.group(1) if match else None
        raw=last.read_text() if last.is_file() else ""
        if not raw.strip():
            err=[line[:400] for line in call.stderr.splitlines() if re.match(r"^(ERROR:|Error:|Reconnecting\.\.\.)",line)]
            dump(PRIVATE/"failures"/(ident+"-"+str(time.time_ns())+".json"),
                 {"job":ident,"returncode":call.returncode,"errors":err[-3:]})
            raise RuntimeError(ident+" no provider answer; see private failure record")
        receipt={"job":ident,"raw":raw,"raw_sha256":builder.sha(raw.encode()),
                 "packet_sha256":job["packet_sha256"],"started_utc":stamp,"completed_utc":datetime.now(timezone.utc).isoformat(),
                 "model":header("model"),"reasoning":header("reasoning effort"),"session":header("session id"),
                 "exit_code":call.returncode,"visible_tool_events":sum(bool(re.match(r"^(?:exec|tool [^ ]+|web search)$",l)) for l in call.stderr.splitlines())}
        dump(destination,receipt)
        if (receipt["model"]!=MODEL or not receipt["session"] or receipt["reasoning"]!="medium"
            or call.returncode or receipt["visible_tool_events"]):
            raise RuntimeError("Review model receipt before consuming: "+ident)


def generate():
    freeze=json.loads((HERE/"freeze.json").read_text())
    assert digest(PRIVATE/"schedule.json")==freeze["schedule_sha256"]
    jobs=json.loads((PRIVATE/"schedule.json").read_text())
    pending=[j for j in jobs if not (PRIVATE/"generated"/(j["job"]+".json")).exists()]
    errors=0
    with ThreadPoolExecutor(max_workers=5) as pool:
        it=iter(pending); current=set()
        for _ in range(min(5,len(pending))):
            current.add(pool.submit(generate_one,next(it)))
        done=0
        while current:
            f=next(as_completed(current));current.remove(f)
            try:f.result()
            except Exception as exc:
                errors+=1
                print("generation failure:",type(exc).__name__,flush=True)
            done+=1
            if done%15==0 or done==len(pending):print("Attempts finished:",done,"/",len(pending),flush=True)
            nxt=next(it,None) if errors<3 else None
            if nxt:current.add(pool.submit(generate_one,nxt))
    if errors:raise RuntimeError("Incomplete requests; inspect restricted receipts before resuming")


def presentation(text):
    out=text.strip()
    out=re.sub(r'^(?:Patient|Speaker|Assistant)\s*:\s*','',out,flags=re.I)
    if len(out)>2 and (out[0],out[-1]) in [('"','"'),('“','”')]:
        out=out[1:-1]
    return " ".join(out.split())


def blind():
    groups,patients=data_cases()
    jobs=json.loads((PRIVATE/"schedule.json").read_text())
    rows=[]; sessions=set()
    for person,d in patients.items():
        rows.append((person,"patient",0,d["question"],presentation(d["answer"])))
    for j in jobs:
        item=json.loads((PRIVATE/"generated"/(j["job"]+".json")).read_text())
        assert item["packet_sha256"]==j["packet_sha256"] and item["raw_sha256"]==builder.sha(item["raw"].encode())
        assert item["model"]==MODEL and item["reasoning"]=="medium" and item["session"] and item["session"] not in sessions
        assert not item["visible_tool_events"] and item["exit_code"]==0
        sessions.add(item["session"])
        text=presentation(item["raw"])
        assert text.strip() and re.search("[A-Za-z]",text) and not re.search("[가-힣]",text)
        rows.append((j["person"],j["arm"],j["rep"],patients[j["person"]]["question"],text))
    assert len(rows)==140 and len(sessions)==126
    if not (PRIVATE/"blind-seed.json").exists():dump(PRIVATE/"blind-seed.json",secrets.randbits(192))
    rng=random.Random(json.loads((PRIVATE/"blind-seed.json").read_text()))
    rng.shuffle(rows)
    key=[]; packets=[]
    for person,arm,rep,question,answer in rows:
        uid="U"+f"{rng.getrandbits(60):015x}"
        packets.append({"uid":uid,"question":question,"answer":answer})
        words=len(re.findall(r"[a-z]+(?:'[a-z]+)*",answer.lower().replace("’","'")))
        key.append({"uid":uid,"person":person,"question":groups[person],"arm":arm,"rep":rep,"words":words})
    assert len({p["uid"] for p in packets})==140
    dump(PRIVATE/"key.json",key)
    dump(PRIVATE/"blind.json",packets)
    print("Mixed and source-masked:",len(packets),"unique generation sessions:",len(sessions))


if __name__=="__main__":
    os.umask(0o077);sys.dont_write_bytecode=True
    {"prepare":prepare,"generate":generate,"blind":blind}[sys.argv[1]]()
