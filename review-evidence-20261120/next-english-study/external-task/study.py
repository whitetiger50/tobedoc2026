"""Two published English elicitation tasks, independent synthetic first turns, descriptive word counts."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import fcntl
import itertools
import json
import math
import os
from pathlib import Path
import random
import re
import shutil
from statistics import mean, median
import subprocess
import sys

HERE=Path(__file__).resolve().parent
STUDY=HERE.parent
PRIVATE=HERE/"private"
sys.dont_write_bytecode=True
sys.path.insert(0,str(STUDY))
import runner as prior

gen=prior.gen
read,save,check=prior.read,prior.save,prior.check
ARMS=("B","T1","T2","Short")
TASKS={"story":"Could you tell me the story of Cinderella?",
       "laundry":"What are the steps involved when people have to do laundry?"}
PREFIX="You may speak for as long as you wish."
SHORT="Answer briefly, using at most two sentences."
REFERENCES={"patient":{"story":237,"laundry":139},"nonclinical":{"story":452,"laundry":162}}
BASE_SOURCES=prior.sources


def sources():
    systems,core=BASE_SOURCES()
    return {**systems,"Short":systems["T2"]+("" if systems["T2"].endswith("\n") else "\n")+SHORT+"\n"},core


def configure(task):
    folder=PRIVATE/task
    gen.CASES=folder/"cases.json";gen.FREEZE=folder/"generation-freeze.json";gen.GEN=folder/"generation"
    gen.ARMS=ARMS;gen.sources=sources
    return folder


def question(task):
    return PREFIX+"\n"+TASKS[task]


def prepare():
    prior.verify_design()
    tracked=[Path(__file__),HERE/"DESIGN.ko.md",STUDY/"T2.txt",STUDY/"cases.json",STUDY/"runner.py",
             STUDY/"generation-freeze.json",prior.PRIOR/"generation.py",prior.PRIOR/"quota.py",*gen.SOURCE_HASHES]
    original=prior.inputs()
    for task in TASKS:
        configure(task)
        cards=[]
        for cid in prior.IDS:
            case=deepcopy(original[cid]);case["questions"]=[question(task)];cards.append(case)
        save(gen.CASES,cards)
        signatures={}
        for case in cards:
            for arm in ARMS:
                req=gen.messages(case,arm,1,[])
                check(len(req)==2,"First-turn context leaked")
                if arm=="B":
                    check(req[-1]["content"]==question(task),"B task changed")
                else:
                    body=json.loads(req[-1]["content"])
                    check(body["current_question"]==question(task) and body["history"]==[],"Team task changed")
                    check(req[-1]==gen.messages(case,"T1",1,[])[-1],"Unequal team inputs")
                signatures[case["id"]+"-"+arm]=gen.digest(gen.encode(req))
        save(gen.FREEZE,{"cases_sha256":prior.sha(gen.CASES),"generator_sha256":prior.sha(prior.PRIOR/"generation.py"),
                         "first_message_sha256":signatures})
        tracked.extend([gen.CASES,gen.FREEZE])
    save(HERE/"freeze.json",{"hashes":{os.path.relpath(p,HERE):prior.sha(p) for p in tracked},
         "system_unfilled":{a:gen.digest(sources()[0][a].encode()) for a in ARMS},
         "model":gen.MODEL,"reasoning":"medium","prefix":PREFIX,"questions":TASKS,"short_extra":SHORT,
         "planned_first_outputs":64,"cell_repetitions":1})
    print("Frozen 8 profiles × 2 independent tasks × 4 conditions",flush=True)


def verify_freeze():
    old=read(HERE/"freeze.json")
    for name,h in old["hashes"].items():
        check(prior.sha(HERE/name)==h,"Frozen input/transport mismatch: "+name)


def job(task,cid,arm):
    verify_freeze();configure(task);r=gen.one(cid,arm,1)
    if arm=="B":
        # Native-history check occurs inside gen.one before this single-turn interview is closed.
        fp=gen.turn_dir(cid,arm,1).parent/"isolated-runtime.json"
        scratch=Path(read(fp)["path"])
        check(scratch.parent==Path("/private/tmp") and scratch.name.startswith("interview-cli-"),"Unexpected scratch directory")
        if scratch.exists():shutil.rmtree(scratch)
    return r


def run():
    verify_freeze()
    jobs=list(itertools.product(TASKS,prior.IDS,ARMS))
    random.Random("external-tasks-20261121-v1").shuffle(jobs)
    jobs=[j for j in jobs if not (PRIVATE/j[0]/"generation"/j[1]/j[2]/"01/result.json").exists()]
    def call(j):
        cmd=[sys.executable,"-B",str(Path(__file__).resolve()),"one",*j]
        subprocess.run(cmd,check=True,cwd=HERE)
    for i in range(0,len(jobs),6):
        q=prior.quota.read_quota()
        w=q["primary"]
        check(q["limitId"]=="codex" and w["windowDurationMins"]==10080 and isinstance(w["usedPercent"],(int,float)),"Missing weekly meter")
        with (PRIVATE/"budget.jsonl").open("a") as f:
            f.write(json.dumps({"utc":gen.now(),"batch":i//6+1,"used":w["usedPercent"],"reset":w["resetsAt"]})+"\n")
        check(w["usedPercent"]<66,"Codex weekly reserve reached")
        with ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(call,jobs[i:i+6]))
        print("First outputs",min(i+6,len(jobs)),"of",len(jobs),flush=True)


def word_counts(s):
    return {"english":len(re.findall(r"[A-Za-z]+(?:['’][A-Za-z]+)*",s)),"whitespace":len(s.split())}


def checked(task,cid,arm):
    configure(task)
    case=next(c for c in read(gen.CASES) if c["id"]==cid)
    folder=gen.turn_dir(cid,arm,1);req=gen.messages(case,arm,1,[])
    sig=gen.digest(gen.encode(req));r=gen.verify_result(folder,sig)
    check(read(gen.FREEZE)["first_message_sha256"][cid+"-"+arm]==sig and req==read(folder/"request.json"),"Input changed")
    check(read(folder/"started.json")["history_count"]==0 and r["turn"]==1 and r["question"]==question(task) and
          r["arm"]==arm and r["case"]==cid and r["visible_tool_events"]==r["exit_code"]==0,
          "Unexpected model output or input")
    check(r["trace_sha256"]==prior.sha(folder/"events.jsonl") and (folder/"last.txt").read_text() in (r["raw"],r["raw"]+"\n"),
          "First output changed")
    check(r["native_transcript_sha256"]==gen.digest(gen.encode([("user_message",req[-1]["content"]),("agent_message",r["raw"])])),
          "Unexpected native history")
    return r


def logerr(a,b):
    return abs(math.log(a/b)) if a>0 and b>0 else None


def frame(index,selected,metric):
    arms={}
    for arm in ARMS:
        by_task={t:[index[c,arm,t][metric] for c in selected] for t in TASKS}
        stats={t:{"mean":mean(v),"median":median(v),"range":[min(v),max(v)]} for t,v in by_task.items()}
        means={t:v["mean"] for t,v in stats.items()}
        ratio=means["story"]/means["laundry"] if means["laundry"]>0 else None
        distances={}
        for name,ref in REFERENCES.items():
            task_errors={t:logerr(means[t],ref[t]) for t in TASKS};d=list(task_errors.values())
            distances[name]={"task_abs_log_error":task_errors,"mean_abs_log_error":mean(d) if all(n is not None for n in d) else None,
                "task_mean_minus_reference":{t:means[t]-ref[t] for t in TASKS},
                "ratio_abs_log_error":logerr(ratio,ref["story"]/ref["laundry"]) if ratio is not None else None}
        arms[arm]={"task":stats,"story_over_laundry_ratio_of_means":ratio,"distance":distances}
    return arms


def comparison(arms,ref="patient"):
    out={}
    for base in ("B","T1","Short"):
        t2=arms["T2"]["distance"][ref];b=arms[base]["distance"][ref]
        x=[t2["task_abs_log_error"][task] for task in TASKS];y=[b["task_abs_log_error"][task] for task in TASKS]
        if any(v is None for v in [*x,*y,t2["ratio_abs_log_error"],b["ratio_abs_log_error"]]):
            out[base]=None;continue
        out[base]={"both_task_errors_no_worse_one_strictly_smaller":all(i<=j for i,j in zip(x,y)) and any(i<j for i,j in zip(x,y)),
                   "shape_error_strictly_smaller":t2["ratio_abs_log_error"]<b["ratio_abs_log_error"],
                   "level_distance_difference":t2["mean_abs_log_error"]-b["mean_abs_log_error"],
                   "shape_distance_difference":t2["ratio_abs_log_error"]-b["ratio_abs_log_error"]}
        out[base]["passes_both"]=out[base]["both_task_errors_no_worse_one_strictly_smaller"] and out[base]["shape_error_strictly_smaller"]
    return out


def score(index,metric):
    arms=frame(index,prior.IDS,metric)
    delta={cid:{a:{"story_minus_laundry_words":index[cid,a,"story"][metric]-index[cid,a,"laundry"][metric],
                    "task_difference_vs_T2":{t:index[cid,a,t][metric]-index[cid,"T2",t][metric] for t in TASKS}}
                for a in ARMS} for cid in prior.IDS}
    def ranks(a):
        return {ref:{typ:sorted(ARMS,key=lambda arm:(a[arm]["distance"][ref][typ] is None,a[arm]["distance"][ref][typ],arm))
                    for typ in ("mean_abs_log_error","ratio_abs_log_error")} for ref in REFERENCES}
    leave={}
    for skip in prior.IDS:
        sub=frame(index,[c for c in prior.IDS if c!=skip],metric)
        leave[skip]={"patient_T2_vs_others":comparison(sub),"rank_lowest_first":ranks(sub)}
    return {"arms":arms,"primary_patient_T2_vs_each":comparison(arms),"nonclinical_T2_vs_each":comparison(arms,"nonclinical"),
            "case_paired_differences":delta,"leave_one_case_out":leave,"rank_lowest_first":ranks(arms),
            "rank_note":"Alphabetical order breaks exact numerical ties in display only; differences and pass rule use numeric errors."}


def analyze():
    verify_freeze();seen=set();answers=[];index={}
    for task,cid,arm in itertools.product(TASKS,prior.IDS,ARMS):
        r=checked(task,cid,arm);check(r["session"] not in seen,"Generator session reused");seen.add(r["session"])
        counts=word_counts(r["raw"]);index[cid,arm,task]=counts
        answers.append({"case":cid,"source_model":r["model"],"task":task,"condition":arm,"question":question(task),
                        "answer":r["raw"],"counts":counts})
    check(len(seen)==64,"Incomplete genuine first answers")
    results={m:score(index,m) for m in ("english","whitespace")}
    caveats=["Tasks were independent written first turns with eight fictional profiles and fixed prompts. "
             "The source involved unbounded spoken responses during structured interviews with different individuals.",
             "The primary English-word regex treats internal straight and curly apostrophes as word characters. "
             "The source tokenization is unspecified. Published reference means are rounded.",
             "Whole responses, including quotations, punctuation or potential role departures, are retained. A short response, refusal or incomplete account is never regenerated. Length is not story/step completeness or clinical realism.",
             "One generated response per cell and no clinical validation. Numerical closeness compares group mean word counts rather than diagnostic accuracy or equivalent distribution."]
    save(HERE/"release.json",{"study":"Independent exploratory external task anchor; primary adoption decision unchanged",
         "reference":{"citation":"Pugh et al. (2024), Psychiatry Research, Table 2","doi":"10.1016/j.psychres.2024.116119",
                      "means":REFERENCES,"n":{"patient":{"story":26,"laundry":26},"nonclinical":{"story":24,"laundry":25}},
                      "clinical_population":"DSM-IV schizophrenia or schizoaffective disorder"},
         "integrity":{"verified_first_outputs":64,"frozen_fictional_profiles":8,"tools_used":0,"each_turn_history_empty":True,
                      "different_sessions":64},"caveats":caveats,"synthetic":answers,"analysis":results})
    print("Validated 64 first outputs; released fictional answers and word-count analysis",flush=True)


if __name__=="__main__":
    os.umask(0o077)
    cli=argparse.ArgumentParser(description=__doc__)
    sub=cli.add_subparsers(dest="cmd",required=True)
    for task in ("prepare","run","analyze"):sub.add_parser(task)
    one=sub.add_parser("one");one.add_argument("task",choices=TASKS);one.add_argument("case",choices=prior.IDS);one.add_argument("arm",choices=ARMS)
    args=cli.parse_args()
    if args.cmd=="one":job(args.task,args.case,args.arm)
    elif args.cmd=="run":
        with (HERE/"run.lock").open("a") as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);run()
    else:{"prepare":prepare,"analyze":analyze}[args.cmd]()
