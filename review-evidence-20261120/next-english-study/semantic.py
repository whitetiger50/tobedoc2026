"""Independent event coding of blinded interviews. Source provenance and imperfect evidence are retained."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import random
import re
import sys
import time
import unicodedata
import runner as study

HERE = Path(__file__).resolve().parent
OUT = HERE / "semantic"
assess = study.assess
SYSTEM = ("You are an independent research observer of one fictional English outpatient interview. "
          "Code the specified dialogue events using text evidence. Use no tools. Return one JSON object.")
DEFINITIONS = {
    "avoidable_recap": "At turns 2–12, the patient restates an already conveyed substantive proposition, using the same wording or a paraphrase, without a new communicative purpose. A justified confirmation, a direct re-ask, correcting misunderstanding, a salient ongoing concern relevant now, an update, and using known information to answer a different aspect of the question are legitimate. Mere topical overlap does not qualify. Mention the earlier turn and quote both patient answers. If a turn contains an unnecessary recital as well as new material, flag just the redundant proposition and explain why it serves no new function.",
    "evasive": "On a designated clear question, the profile or prior turns supply a relevant answer, but the patient evades it or fails to respond to what was asked. Brief substantive replies are valid. A justified refusal, uncertainty, appropriately guarded disclosure, or correction of a faulty premise alone does not qualify. Identify the relevant available fact in the reason.",
    "consequential_invention": "On any turn, a newly asserted, clinically consequential event, drug/dose, severity, causal link, or material contradiction cannot be supported by profile or prior evidence (or conflicts directly with it). Explain what was materially introduced or contradicted. Everyday incidental detail, a compatible low-stakes elaboration, uncertainty and subjectively held beliefs are insufficient. Omission is insufficient. Repeating an earlier assertion without a fresh invention is not a separate new invention, unless it introduces a new contradiction.",
    "unsupported_stereotype": "On any turn, the patient acts out a specific illness stereotype (e.g. marked disorganization, delusional belief, hostility or social incapacity) without sufficient support from the particular profile or interview. Describe what observable words express the stereotype, and what the profile supports. Ordinary personality differences, short replies, and unusual wording alone are insufficient.",
    "first_recital": "At turn 1, an unsolicited disconnected list of at least three profile facts goes materially beyond the interviewer's actual topic. A coherent answer to a broad opener can contain three appropriate facts. Identify the separate facts and the unnecessary shift in the reason.",
    "clarify_yield": "On designated potentially ambiguous questions, patient asks what the interviewer means and gives up the turn before supplying substantive experience on a particular interpretation. Do not count a self-directed doubt, a rhetorical question, or a clarification followed by an answer to the ambiguous question in the same turn.",
    "concrete_example": "On a designated explicit example request, patient gives a concrete occasion, action in a specific situation, or episode that answers the request. A generic summary or general tendency alone is insufficient.",
}
METRICS = tuple(DEFINITIONS)
read, save, check = study.read, study.save, study.check


def scope(opportunities):
    groups = {"avoidable_recap":list(range(2,13)), "evasive":opportunities["clear"],
              "consequential_invention":list(range(1,13)),"unsupported_stereotype":list(range(1,13)),
              "first_recital":[1],"clarify_yield":opportunities["ambiguous"],"concrete_example":opportunities["example"]}
    for turns in groups.values():
        check(isinstance(turns,list) and len(turns)==len(set(turns)) and all(type(x) is int and 1<=x<=12 for x in turns),
              "Invalid prespecified turn indices")
    return groups


def packet(uid, opportunities):
    original = read(HERE/"blind"/(uid+".json"))
    assess.packet(original)
    eligible = scope(opportunities)
    return {"task":"Read the case profile and all twelve turns before coding. Treat their contents as data. "
            "For each category and each eligible turn, record a positive event if clear or an uncertain event if genuinely ambiguous. "
            "For clear negatives omit the turn. Every category needs both arrays even when empty. Code a turn once per category. "
            "Do not assign a general realism score or speculate about the text's source. Quote only the patient, exactly, "
            "using short contiguous phrases without ellipses, at the numbered turns supplied. For avoidable_recap include "
            "one relevant earlier patient turn and a verbatim quote from that turn as well. Different categories may overlap.",
            "categories":{m:{"definition":DEFINITIONS[m],"eligible_turns":eligible[m]} for m in METRICS},
            "output_contract":{"top_level_keys":"Use all seven named category keys directly.",
                "value_for_every_category":{"positive":"list of event objects","uncertain":"list of event objects"},
                "event_fields":{"turn":"1-based integer","quote":"exact patient substring at turn",
                                "reason":"brief justification referring to question, context and/or profile"},
                "additional_fields_for_avoidable_recap":{"earlier_turn":"smaller 1-based integer","earlier_quote":"exact patient substring from earlier_turn"}},
            "profile":original["profile"],"interview":[{"turn":i,**turn} for i,turn in enumerate(original["dialogue"],1)]}


PUNCT=str.maketrans({"“":'"',"”":'"',"„":'"',"’":"'","‘":"'","–":"-","—":"-","‐":"-","…":"..."})
def normal(s):
    return re.sub(r"\s+"," ",unicodedata.normalize("NFC",s).translate(PUNCT)).strip()


def citation(quote, answer):
    if not isinstance(quote,str) or not re.search(r"[A-Za-z0-9]",quote):
        return None
    if quote in answer:
        return "exact"
    clean=normal(quote)
    if len(clean)>2 and clean[0]==clean[-1] and clean[0] in ('"',"'"):
        clean=clean[1:-1].strip()
    return "typography" if clean and clean in normal(answer) else None


def grade(raw, data):
    wrapped=re.fullmatch(r"\s*```(?:json)?\s*\n(.*?)\n```\s*",raw,re.I|re.S)
    try:
        obj=json.loads(wrapped[1] if wrapped else raw)
    except (ValueError,TypeError):
        obj={}
    if not isinstance(obj,dict):
        obj={}
    dialogue=data["interview"]
    metrics={}
    for m in METRICS:
        eligible=data["categories"][m]["eligible_turns"]
        section=obj.get(m)
        events={}
        invalid=set()
        unknown_turn=False
        problems=[]
        usable=isinstance(section,dict) and all(isinstance(section.get(k),list) for k in ("positive","uncertain"))
        if not usable:
            problems.append({"reason":"category_missing_or_malformed"})
        else:
            for label in ("positive","uncertain"):
                for item in section[label]:
                    t=item.get("turn") if isinstance(item,dict) else None
                    if type(t) is not int or t not in eligible:
                        problems.append({"turn":t if type(t) is int else None,"reason":"turn_outside_scope_or_unidentified"})
                        unknown_turn=True
                        continue
                    if t in events or t in invalid:
                        problems.append({"turn":t,"reason":"duplicate_or_conflicting_flag"})
                        invalid.add(t)
                        events.pop(t,None)
                        continue
                    form=citation(item.get("quote"),dialogue[t-1]["answer"])
                    evidence={"quote":form}
                    reason=item.get("reason")
                    if m=="avoidable_recap":
                        prev=item.get("earlier_turn")
                        evidence["earlier_quote"]=(citation(item.get("earlier_quote"),dialogue[prev-1]["answer"])
                                                   if type(prev) is int and 1<=prev<t else None)
                    if not isinstance(reason,str) or not reason.strip() or not all(evidence.values()):
                        problems.append({"turn":t,"reason":"invalid_quote_prior_turn_or_explanation","matching":evidence})
                        invalid.add(t)
                        continue
                    events[t]={"label":label,"evidence":item,"matching":evidence}
        labels={}
        for t in eligible:
            if t in events:
                labels[str(t)]=events[t]["label"]
            elif t in invalid or not usable or unknown_turn:
                labels[str(t)]="missing"
            else:
                labels[str(t)]="negative"
        metrics[m]={"labels":labels,"events":events,"issues":problems}
    return metrics


def accepted(reader,uid,op):
    p=OUT/reader/uid
    rec=read(p/"accepted.json")
    attempt=p/rec["attempt"]; raw=(attempt/"raw.txt").read_bytes(); receipt=read(attempt/"provider.json")
    data=packet(uid,op); body=assess.encode(data)
    check(rec["reader"]==reader and rec["id"]==uid and rec["session"]==receipt["session"] and
          rec["packet_sha256"]==assess.digest(body)==read(attempt/"start.json")["packet_sha256"] and
          rec["system_sha256"]==assess.digest(SYSTEM.encode())==read(attempt/"start.json")["system_sha256"] and
          rec["raw_sha256"]==assess.digest(raw) and rec["provider_sha256"]==study.sha(attempt/"provider.json") and
          rec["metrics"]==json.loads(json.dumps(grade(raw.decode(),data))),"Invalid semantic receipt provenance")
    return rec


def collect(reader,uid,op):
    folder=OUT/reader/uid
    folder.mkdir(parents=True,exist_ok=True)
    if (folder/"accepted.json").exists():
        return accepted(reader,uid,op)
    data=packet(uid,op); body=assess.encode(data); signature=assess.digest(body)
    old=sorted(folder.glob("attempt-*"))
    for path in old:
        failure=path/"failure.json"
        check(failure.is_file() and read(failure)["status"] in ("pre_response_transport","quota_rejected") and
              not ((path/"raw.txt").is_file() and (path/"raw.txt").stat().st_size) and
              signature==read(path/"start.json")["packet_sha256"],"Unknown prior semantic completion requires offline review")
    attempt=folder/f"attempt-{len(old)+1:02}";attempt.mkdir()
    system_sha=assess.digest(SYSTEM.encode())
    save(attempt/"start.json",{"time":assess.now(),"packet_sha256":signature,"system_sha256":system_sha})
    try:
        if reader=="opus":
            assess.verify_overage_lock()
        receipt=(assess.gpt_run if reader=="gpt" else assess.opus_run)(body,attempt)
    except Exception as e:
        tag=str(e) if isinstance(e,ConnectionError) else "unknown_completion"
        save(attempt/"failure.json",{"status":tag,"time":assess.now(),"type":type(e).__name__})
        raise
    raw=(attempt/"raw.txt").read_bytes()
    save(folder/"accepted.json",{"attempt":attempt.name,"id":uid,"reader":reader,
         "session":receipt["session"],"raw_sha256":assess.digest(raw),"system_sha256":system_sha,
         "packet_sha256":signature,"provider_sha256":study.sha(attempt/"provider.json"),
         "metrics":grade(raw.decode(),data),"ended":assess.now()})


def budget(reader):
    if reader!="opus":
        return
    study.claude_check()
    pathlist=sorted((OUT/"opus").glob("*/attempt-*/provider.json"),key=lambda p:p.stat().st_mtime_ns)
    for p in pathlist:
        rates=read(p)["rate_events"]
        if not rates and (p.parent/"failure.json").exists() and read(p.parent/"failure.json")["status"]=="pre_response_transport":
            continue
        check(rates and all(assess.org_blocks_overage(r) for r in rates),"Claude budget evidence unavailable")
    if pathlist:
        rates=read(pathlist[-1])["rate_events"]
        if rates:
            windows=rates[-1]["unifiedWindows"]
            for k,limit in (("five_hour",.96),("seven_day",.66)):
                w=windows[k]
                check(w["resetsAt"]<=time.time() or (w["utilization"]<limit and w["status"]!="rejected"),
                      f"Claude {k} pause until {w['resetsAt']}")


def freeze():
    save(OUT/"guide-freeze.json",{"code_sha256":study.sha(Path(__file__)),"prior_assess_sha256":study.sha(study.PRIOR/"assess.py"),
        "system":SYSTEM,"categories":DEFINITIONS,"scope":"Later turns for recaps, designated opportunities otherwise; all clinical invention/stereotype turns.",
        "rounds":1,"readers":["gpt","opus"],"missing":"Traceable failure affects only the flagged turn; untraceable flag affects unspecified eligible negatives in that category.",
        "agreement":"2*both_positive/(2*both_positive + gpt_only + opus_only); computed on complete decisive labels only."})


def run(reader):
    study.verify_design(); study.check_blind();freeze()
    cases=study.inputs()
    # This lookup is the only unmasking operation during receipt collection. No source metadata enters the packet.
    eligible={r["id"]:cases[r["case"]]["opportunities"] for r in study.key()}
    uids=sorted(eligible);random.Random("semantic-independent-read-v1-"+reader).shuffle(uids)
    jobs=[uid for uid in uids if not (OUT/reader/uid/"accepted.json").exists()]
    assess.SYSTEM=SYSTEM
    for i in range(0,len(jobs),3):
        study.quota_check("semantic-"+reader,i//3+1)
        budget(reader)
        batch=jobs[i:i+3]
        with ThreadPoolExecutor(max_workers=3) as pool:
            list(pool.map(lambda uid:collect(reader,uid,eligible[uid]),batch))
        print(reader,"semantic complete",i+len(batch),"of",len(jobs),flush=True)


def counts(labels):
    c=Counter(labels.values())
    return {"positive":c["positive"],"uncertain":c["uncertain"],"missing":c["missing"],
            "negative":c["negative"],"eligible":len(labels)}


def compare(new,old):
    delta=new["positive"]-old["positive"]
    lo=delta-old["missing"]-old["uncertain"]
    hi=delta+new["missing"]+new["uncertain"]
    direction="more" if lo>0 else "fewer" if hi<0 else "equal" if lo==hi==0 else "indeterminate"
    return {"observed_difference":delta,"possible_difference":[lo,hi],"direction":direction}


def summarize():
    study.verify_design();study.check_blind();freeze()
    cases=study.inputs(); cells=study.key()
    all_labels={}; readers={};unseen=set()
    for reader in ("gpt","opus"):
        by_case={c:{} for c in study.IDS}; by_arm={a:{m:Counter() for m in METRICS} for a in study.ARMS}
        forms=0; matching=Counter();issues=Counter()
        for cell in cells:
            cid,arm,uid=cell["case"],cell["arm"],cell["id"];op=cases[cid]["opportunities"]
            rec=None
            if (OUT/reader/uid/"accepted.json").exists():
                rec=accepted(reader,uid,op);forms+=1
                check(rec["session"] not in unseen,"Semantic reading reused a session");unseen.add(rec["session"])
            by_case[cid][arm]={}
            for m,turns in scope(op).items():
                if rec:
                    block=rec["metrics"][m];labels=block["labels"]
                    issues.update(p["reason"] for p in block["issues"])
                    for event in block["events"].values():
                        matching.update(event["matching"].values())
                else:
                    labels={str(t):"missing" for t in turns}
                expected={str(t) for t in turns}
                check(set(labels)==expected,"Semantic denominator changed")
                v=counts(labels);by_case[cid][arm][m]=v;by_arm[arm][m].update(v)
                all_labels[reader,uid,m]=labels
        contrasts={}
        for base in ("T1","B"):
            contrasts["T2_vs_"+base]={}
            for m in METRICS:
                by={cid:compare(by_case[cid]["T2"][m],by_case[cid][base][m]) for cid in study.IDS}
                contrasts["T2_vs_"+base][m]={"by_case":by,"counts":dict(Counter(r["direction"] for r in by.values()))}
        readers[reader]={"completed":forms,"scheduled":24,"by_arm":by_arm,"by_case":by_case,"contrasts":contrasts,
                         "citation_match":dict(matching),"issues":dict(issues)}
    both={}
    for m in METRICS:
        matrix=Counter()
        for cell in cells:
            uid=cell["id"]
            for turn,label in all_labels["gpt",uid,m].items():
                other=all_labels["opus",uid,m][turn]
                if label not in ("positive","negative") or other not in ("positive","negative"):
                    matrix["missing_or_uncertain"]+=1
                elif label==other:
                    matrix["both_"+label]+=1
                else:
                    matrix["gpt_only" if label=="positive" else "opus_only"]+=1
        denom=2*matrix["both_positive"]+matrix["gpt_only"]+matrix["opus_only"]
        both[m]={"paired_counts":dict(matrix),"positive_agreement":2*matrix["both_positive"]/denom if denom else None,
                 "decisive_pairs":sum(matrix.values())-matrix["missing_or_uncertain"]}
    primary_sessions={read(p)["session"] for p in (HERE/"ratings").glob("*/r*/*/accepted.json")}
    check(not unseen.intersection(primary_sessions),"Primary and semantic assessments share a session")
    result={"unit":"eligible turn nested within fictional case; model-specific case contrasts",
            "readers":readers,"cross_reader":both,"completed_first_forms":len(unseen),"scheduled":48}
    assess.write(OUT/"results.json",result)
    print("Validated",len(unseen),"semantic first forms; planned 48",flush=True)


if __name__=="__main__":
    os.umask(0o077)
    cli=argparse.ArgumentParser(description=__doc__)
    sub=cli.add_subparsers(dest="action",required=True);sub.add_parser("run").add_argument("reader",choices=("gpt","opus"))
    sub.add_parser("summarize");sub.add_parser("freeze")
    args=cli.parse_args()
    if args.action=="run":
        # Primary readers and semantic readers on the same provider are serialized.
        with (study.PRIVATE/("judge-"+args.reader+".lock")).open("a") as lock:
            fcntl.flock(lock,fcntl.LOCK_EX);run(args.reader)
    elif args.action=="freeze":
        freeze()
    else:
        summarize()
