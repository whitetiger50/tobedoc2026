"""Masked reconstruction of two authored facts per case from patient speech or interviewer questions alone."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import fcntl
import json
import os
from pathlib import Path
import random
import re
import secrets
import sys
import time

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
PRIVATE = HERE/"private"
sys.path.insert(0,str(STUDY))
import runner as study
import semantic

assess = study.assess
read, save, check = study.read, study.save, study.check
READERS = ("gpt", "opus")
LABELS = ("correct","foil","insufficient","conflict","invalid")
RESET_EPOCH = 1795215600
SYSTEM = ("Read only the supplied fictional interview material. Identify which option is supported by the "
          "specified speaker's own words. Use no external knowledge or tools. Return one JSON object.")
TASK = ("For each item report A, B, insufficient, or both_or_conflicting. Treat the alternatives symmetrically. "
        "Do not fill gaps by plausibility, clinical expectation, or what an interviewer may wish to elicit. "
        "Keep negation, uncertainty, time and whose experience is described intact. Use insufficient when "
        "neither specific alternative is established, and both_or_conflicting only when specific evidence "
        "actually supports both. For A/B give evidence for that alternative; for both_or_conflicting give "
        "evidence for each alternative, tagging each citation supports=A or supports=B. Quote short exact "
        "contiguous substrings and 1-based turn numbers. Provide a short reasoning sentence for each item. "
        "Return one JSON object keyed by the two supplied item identifiers. Each value has choice, reason "
        "and citations. Each citation has turn (integer), role (patient or interviewer), quote (exact text) "
        "and supports (A or B). Use an empty citations array when insufficient.")
MODES = {"full": "Use the patient's own words as evidence. The interviewer's statements alone do not establish "
         "the patient's answer. If relying on an elliptical yes/no or a similar short agreement/disagreement, "
         "quote both the exact patient reply and the question it answers from the same numbered turn, tagged "
         "with the same alternative. Explain the link. Retain ambiguity if the patient does not endorse the premise.",
         "questions": "Only interviewer questions are available. Treat a fact as recoverable only if a question "
         "explicitly states or presupposes the specific fact, even without a patient answer. Merely asking "
         "which of two things is true, asking whether a fact is true, or mentioning an example/possibility "
         "does not establish it. Cite only the interviewer."}
YES_NO = re.compile(r"(?:yes|yeah|yep|no|nope|right|correct|i do|i did|i don['’]t|i didn't|"
                    r"that['’]s right|that['’]s correct|i think so|i suppose so|pretty much)[.!?,\s]*",re.I)


def profile_strings(value):
    if isinstance(value,str):
        yield value
    elif isinstance(value,dict):
        for s in value.values():yield from profile_strings(s)
    elif isinstance(value,list):
        for s in value:yield from profile_strings(s)


def targets():
    rows=read(HERE/"targets.json");casebook=study.inputs()
    check(isinstance(rows,list) and len(rows)==8 and {r['case'] for r in rows}==set(study.IDS),"Need N01..N08")
    domains=None;out={}
    for row in rows:
        cid=row["case"];vv=row["targets"];mp={v["domain"]:v for v in vv}
        check(len(vv)==len(mp)==2,"Need exactly two distinct domains per case")
        if domains is None:domains=set(mp)
        check(set(mp)==domains,"Domain names differ across cases")
        fields=list(profile_strings(casebook[cid]["profile"]))
        for v in vv:
            check(all(isinstance(v.get(k),str) and v[k].strip() for k in ("stem","gold","foil","source_quote","domain")),
                  "Target fields must be nonempty strings")
            check(v["gold"].casefold().strip()!=v["foil"].casefold().strip(),"Alternatives identical")
            check(any(v["source_quote"] in f for f in fields),"Target quote not located in the case profile")
            q=v["opportunities"]
            check(isinstance(q,list) and q and len(set(q))==len(q) and all(type(t) is int and 1<=t<=12 for t in q),
                  "Invalid target opportunities")
        out[cid]=mp
    return out


def schedule():
    path=PRIVATE/"schedule.json"
    if path.exists():return read(path)
    candidates=targets();domains=sorted(next(iter(candidates.values())))
    base={k["id"]:(k["case"],k["arm"]) for k in study.key()};cells=[]
    first_a=set(random.SystemRandom().sample(list(study.IDS),4))
    for cid in study.IDS:
        ds=domains[:];random.SystemRandom().shuffle(ds)
        orientations={}
        for reader in READERS:
            orientations[reader]={}
            for idx,d in enumerate(ds,1):
                gold_a=(cid in first_a)==(d==domains[0])
                if reader=="opus":gold_a=not gold_a
                orientations[reader][f"item{idx}"]={"domain":d,"gold":"A" if gold_a else "B"}
        src=[(uid,arm) for uid,(c,arm) in base.items() if c==cid]
        for uid,arm in [*src,(None,"Q")]:
            cells.append({"id":"K"+secrets.token_hex(10),"case":cid,"arm":arm,"blind_source":uid,"layouts":orientations})
    random.SystemRandom().shuffle(cells);save(path,cells)
    return cells


def make_packet(cell,reader,candidates,cases):
    cid,arm=cell["case"],cell["arm"]
    items={}
    for alias,v in cell["layouts"][reader].items():
        target=candidates[cid][v["domain"]];gold=v["gold"]
        items[alias]={"question":target["stem"],gold:target["gold"],("B" if gold=="A" else "A"):target["foil"]}
        items[alias]={k:items[alias][k] for k in ("question","A","B")}  # field order cannot disclose gold
    if arm=="Q":
        mode="questions"
        dialogue=[{"turn":t,"interviewer":q} for t,q in enumerate(cases[cid]["questions"],1)]
    else:
        mode="full";data=read(STUDY/"blind"/(cell["blind_source"]+".json"))
        check([x["question"] for x in data["dialogue"]]==cases[cid]["questions"],"Wrong case/dialogue")
        dialogue=[{"turn":i,"interviewer":v["question"],"patient":v["answer"]} for i,v in enumerate(data["dialogue"],1)]
    return {"task":TASK,"evidence_rule":MODES[mode],"interview":dialogue,"items":items}


def prepare():
    study.verify_design();study.check_blind()
    cells=schedule(); candidates=targets();cases=study.inputs();hashes={}
    check(len(cells)==len({v["id"] for v in cells})==32,"Invalid schedule")
    check({(r["case"],r["arm"]) for r in cells}=={(c,a) for c in study.IDS for a in (*study.ARMS,"Q")},"Missing arm")
    first_layout={}
    for r in cells:
        check(all(r["layouts"]["gpt"][k]["gold"]!=v["gold"] and r["layouts"]["gpt"][k]["domain"]==v["domain"]
                  for k,v in r["layouts"]["opus"].items()),"Readers did not receive opposite orientations")
        check(r["layouts"]==first_layout.setdefault(r["case"],r["layouts"]),"Layout confounded with arm")
        for reader in READERS:
            file=PRIVATE/"packets"/reader/(r["id"]+".json")
            save(file,make_packet(r,reader,candidates,cases));hashes[reader+"/"+r["id"]]=study.sha(file)
    for reader in READERS:
        for domain in sorted(next(iter(candidates.values()))):
            count=sum(v["gold"]=="A" for layout in first_layout.values() for v in layout[reader].values() if v["domain"]==domain)
            check(count==4,"Gold position imbalance across domain")
    files=[Path(__file__),HERE/"targets.json",PRIVATE/"schedule.json",STUDY/"generation-freeze.json",STUDY/"blind-freeze.json",
           study.PRIOR/"assess.py",STUDY/"semantic.py",STUDY/"runner.py"]
    files.extend(p for p in (HERE/"DESIGN.ko.md",HERE/"DESIGN.md",HERE/"PROTOCOL.ko.md") if p.exists())
    save(HERE/"freeze.json",{"inputs":{os.path.relpath(p,HERE):study.sha(p) for p in files},"packets":hashes,
         "system":SYSTEM,"n_documents":32,"n_readers":2,"target_count_per_arm":16,"first_form":True,
         "unescaped_values":"Model receives numbered dialogue and items only; gold, profiles and schedule are never included."})
    print("Frozen 64 independently masked reconstruction packets",flush=True)


def frozen():
    record=read(HERE/"freeze.json")
    for key,digest in record["inputs"].items():
        check(study.sha(HERE/key)==digest,"Frozen file changed: "+key)
    return record


def body_for(reader,uid,freeze):
    path=PRIVATE/"packets"/reader/(uid+".json")
    check(study.sha(path)==freeze["packets"][reader+"/"+uid],"Frozen packet changed")
    return read(path)


def grade(raw,data,layout):
    fenced=re.fullmatch(r"\s*```(?:json)?\s*\n(.*?)\n```\s*",raw,re.S|re.I)
    try:obj=json.loads(fenced[1] if fenced else raw)
    except (ValueError,TypeError):obj={}
    if not isinstance(obj,dict):obj={}
    full="patient" in data["interview"][0]
    out={}
    for alias,v in layout.items():
        ans=obj.get(alias)
        record={"status":"invalid","choice":None,"reason":None,"evidence":[]}
        try:
            check(isinstance(ans,dict),"Missing target")
            choice=ans["choice"];record["choice"]=choice
            check(choice in ("A","B","insufficient","both_or_conflicting"),"Unrecognized choice")
            reason=ans["reason"]
            check(isinstance(reason,str) and reason.strip(),"Reason missing")
            record["reason"]=reason
            citations=ans["citations"]
            check(isinstance(citations,list),"Missing citation array")
            if choice=="insufficient":
                check(not citations,"Unexpected decisive citation(s) for insufficient")
                record["status"]="insufficient"
            else:
                allowed={"A","B"} if choice=="both_or_conflicting" else {choice}
                for e in citations:
                    t,role,quote,support=e["turn"],e["role"],e["quote"],e["supports"]
                    check(type(t)is int and 1<=t<=len(data["interview"]) and role in ("interviewer","patient") and
                          support in allowed,"Wrong citation location/alternative")
                    phrase=data["interview"][t-1].get(role)
                    matched=semantic.citation(quote,phrase) if isinstance(phrase,str) else None
                    check(matched,"Citation not located")
                    record["evidence"].append({"turn":t,"role":role,"quote":quote,"supports":support,"match":matched})
                for alternative in allowed:
                    proofs=[e for e in record["evidence"] if e["supports"]==alternative]
                    attributable=[e for e in proofs if e["role"]==("patient" if full else "interviewer")]
                    check(attributable,"No attributable evidence for selected alternative")
                    if full and all(YES_NO.fullmatch(semantic.normal(e["quote"]).strip('"')) for e in attributable):
                        check(any(e["role"]=="interviewer" and any(p["turn"]==e["turn"] for p in attributable)
                                  for e in proofs),"Elliptical answer lacks exact same-turn question")
                record["status"]="conflict" if choice=="both_or_conflicting" else ("correct" if choice==v["gold"] else "foil")
        except (ValueError,KeyError,TypeError) as e:record["problem"]=str(e)
        out[alias]=record
    return out


def accepted(reader,cell,freeze):
    uid=cell["id"];folder=HERE/"ratings"/reader/uid;r=read(folder/"first.json")
    attempt=folder/r["attempt"];data=body_for(reader,uid,freeze);raw=(attempt/"raw.txt").read_bytes()
    receipt=read(attempt/"provider.json")
    check(r["id"]==uid and r["reader"]==reader and r["session"]==receipt["session"] and
          r["packet_sha256"]==assess.digest(assess.encode(data))==read(attempt/"start.json")["packet_sha256"] and
          r["system_sha256"]==assess.digest(SYSTEM.encode())==read(attempt/"start.json")["system_sha256"] and
          r["raw_sha256"]==assess.digest(raw) and r["provider_sha256"]==study.sha(attempt/"provider.json") and
          r["items"]==grade(raw.decode(),data,cell["layouts"][reader]),"First form provenance mismatch")
    return r


def collect(reader,cell,freeze):
    uid=cell["id"];folder=HERE/"ratings"/reader/uid
    folder.mkdir(parents=True,exist_ok=True)
    if (folder/"first.json").exists():return accepted(reader,cell,freeze)
    data=body_for(reader,uid,freeze);body=assess.encode(data);sig=assess.digest(body);systemsha=assess.digest(SYSTEM.encode())
    previous=sorted(folder.glob("attempt-*"))
    for attempt in previous:
        f=attempt/"failure.json";raw=attempt/"raw.txt"
        check(f.exists() and read(f)["status"] in ("quota_rejected","pre_response_transport")
              and not(raw.exists() and raw.stat().st_size) and read(attempt/"start.json")["packet_sha256"]==sig,
              "Unresolved prior dispatch: inspect original response offline")
    attempt=folder/f"attempt-{len(previous)+1:02}";attempt.mkdir()
    save(attempt/"start.json",{"utc":assess.now(),"packet_sha256":sig,"system_sha256":systemsha})
    try:
        if reader=="opus":assess.verify_overage_lock()
        rec=(assess.gpt_run if reader=="gpt" else assess.opus_run)(body,attempt)
    except Exception as err:
        save(attempt/"failure.json",{"utc":assess.now(),"status":str(err) if isinstance(err,ConnectionError) else "unknown_completion"})
        raise
    raw=(attempt/"raw.txt").read_bytes()
    save(folder/"first.json",{"utc":assess.now(),"attempt":attempt.name,"id":uid,"reader":reader,
         "session":rec["session"],"packet_sha256":sig,"system_sha256":systemsha,"provider_sha256":study.sha(attempt/"provider.json"),
         "raw_sha256":assess.digest(raw),"items":grade(raw.decode(),data,cell["layouts"][reader])})


def budget_guard(reader,i):
    q=study.quota.read_quota();w=q["primary"]
    check(q["limitId"]=="codex" and w["windowDurationMins"]==10080 and isinstance(w["usedPercent"],(int,float)),"Missing weekly counter")
    with (HERE/"budget.jsonl").open("a") as f:
        f.write(json.dumps({"utc":assess.now(),"reader":reader,"batch":i,"used":w["usedPercent"],"resetsAt":w["resetsAt"]})+"\n")
    check(w["usedPercent"]<66,"Codex weekly reserve reached")
    if reader!="opus":return
    check(time.time()>=RESET_EPOCH,f"Claude five-hour window is protected until epoch {RESET_EPOCH}")
    semantic.budget("opus")
    paths=sorted((HERE/"ratings/opus").glob("*/attempt-*/provider.json"),key=lambda p:p.stat().st_mtime_ns)
    for p in paths:
        rates=read(p)["rate_events"]
        if not rates and (p.parent/"failure.json").exists() and read(p.parent/"failure.json")["status"]=="pre_response_transport":continue
        check(rates and all(assess.org_blocks_overage(r) for r in rates),"Claude overage protection unverified")
    if paths:
        rates=read(paths[-1])["rate_events"]
        if rates:
            windows=rates[-1]["unifiedWindows"]
            for name,cap in (("seven_day",.66),("five_hour",.96)):
                w=windows[name]
                check(w["resetsAt"]<=time.time() or (w["status"]!="rejected" and w["utilization"]<cap),
                      f"Claude {name} hold until epoch {w['resetsAt']}")


def run(reader):
    fr=frozen();cells=schedule();assess.SYSTEM=SYSTEM
    cells=sorted(cells,key=lambda r:r["id"])
    random.Random("unprompted-reconstruction-v1-"+reader).shuffle(cells)
    jobs=[r for r in cells if not (HERE/"ratings"/reader/r["id"]/"first.json").exists()]
    for i in range(0,len(jobs),3):
        budget_guard(reader,i//3+1)
        with ThreadPoolExecutor(max_workers=3) as pool:
            list(pool.map(lambda cell:collect(reader,cell,fr),jobs[i:i+3]))
        print(reader,min(i+3,len(jobs)),"/",len(jobs),flush=True)


def tab(values):
    c=Counter(values)
    return {**{k:c[k] for k in LABELS},"n":len(values)}


def summarize():
    fr=frozen(); cells=schedule()
    domains=sorted(next(iter(targets().values())))
    readers={};seen=set()
    for reader in READERS:
        rows={c:{a:{} for a in (*study.ARMS,"Q")} for c in study.IDS};citations=Counter();invalid=Counter()
        for cell in cells:
            p=HERE/"ratings"/reader/cell["id"]/"first.json"
            if not p.exists():
                for d in domains:rows[cell["case"]][cell["arm"]][d]="missing_form"
                continue
            r=accepted(reader,cell,fr)
            check(r["session"] not in seen,"Duplicate source session");seen.add(r["session"])
            for alias,obj in r["items"].items():
                domain=cell["layouts"][reader][alias]["domain"]
                rows[cell["case"]][cell["arm"]][domain]=obj["status"]
                citations.update(e["match"] for e in obj["evidence"])
                if obj["status"]=="invalid":invalid[obj.get("problem","unknown")]+=1
        keep=[(c,d) for c in study.IDS for d in domains if rows[c]["Q"][d] in ("insufficient","foil","conflict")]
        control_correct=[(c,d) for c in study.IDS for d in domains if rows[c]["Q"][d]=="correct"]
        unresolved=[(c,d) for c in study.IDS for d in domains if rows[c]["Q"][d] in ("invalid","missing_form")]
        def counts(lst):
            result=tab(lst);result["missing_form"]=lst.count("missing_form");return result
        def analyze_pairs(selected):
            by_arm={a:counts([rows[c][a][d] for c,d in selected]) for a in (*study.ARMS,"Q")}
            by_domain={d:{a:counts([rows[c][a][d] for c,dom in selected if dom==d])
                          for a in (*study.ARMS,"Q")} for d in domains}
            contrasts={}
            for l,r in (("T2","B"),("T2","T1"),("T1","B")):
                by_case={};direction=Counter()
                for c in study.IDS:
                    found=[d for x,d in selected if x==c]
                    if not found:continue
                    left=[rows[c][l][d] for d in found]; right=[rows[c][r][d] for d in found]
                    diff=left.count("correct")-right.count("correct")
                    lower=diff-right.count("invalid")-right.count("missing_form")
                    upper=diff+left.count("invalid")+left.count("missing_form")
                    by_case[c]={"eligible":len(found),"difference":diff,"possible":[lower,upper]}
                    direction["more" if lower>0 else "fewer" if upper<0 else "equal" if lower==upper==0 else "indeterminate"]+=1
                contrasts[l+"_vs_"+r]={"by_case":by_case,"counts":dict(direction)}
            return {"by_arm":by_arm,"by_domain":by_domain,"contrasts":contrasts,"eligible_targets":len(selected)}
        readers[reader]={"by_case":rows,"all":analyze_pairs([(c,d) for c in study.IDS for d in domains]),
                         "excluding_control_correct":analyze_pairs(keep),"control_recoverable":control_correct,
                         "unassessable_controls_excluded":unresolved,"citation_match":dict(citations),"invalid_reasons":dict(invalid)}
    existing={read(p)["session"] for p in (STUDY/"ratings").glob("*/r*/*/accepted.json")}
    existing.update(read(p)["session"] for p in (STUDY/"semantic").glob("*/*/accepted.json"))
    check(not seen.intersection(existing),"Reused primary or semantic session")
    results={"forms":len(seen),"planned_forms":64,"planned_targets_per_arm_per_reader":16,
             "independent_units":"8 cases; two targets per case reused across arms and rating readers",
             "description":"Full vs questionnaire-only controls. Descriptive paired differences in sufficient attributable correct answers. "
             "Control-adjusted sample excludes correct Q recoveries and controls with missing or invalid evidence; failures to recover "
             "in a single question-only reading do not prove absence of clues. Text matching verifies attribution and turn, not entailment.",
             "readers":readers}
    assess.write(HERE/"results.json",results);print("Verified reconstruction forms",len(seen),"/ 64")


if __name__=="__main__":
    os.umask(0o077);cli=argparse.ArgumentParser(description=__doc__)
    sub=cli.add_subparsers(dest="cmd",required=True)
    sub.add_parser("prepare");sub.add_parser("summarize");sub.add_parser("run").add_argument("reader",choices=READERS)
    args=cli.parse_args()
    if args.cmd=="prepare":prepare()
    elif args.cmd=="summarize":summarize()
    else:
        with (study.PRIVATE/("judge-"+args.reader+".lock")).open("a") as f:
            fcntl.flock(f,fcntl.LOCK_EX);run(args.reader)
