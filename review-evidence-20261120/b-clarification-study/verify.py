"""Verify the exported portable study from its synthetic first-response data without network access."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import runpy
import unicodedata

ROOT=Path(__file__).resolve().parent
IDS=tuple(f"C{n:02d}" for n in range(1,9))
ARMS=("B","BC","T2")
READERS=("gpt","opus")
CATEGORIES=("material","context_resolved","same_answer","clear")
REPS=("1","2")
def read(name):
    return json.loads((ROOT/name).read_bytes())
def check(ok,message):
    if not ok:raise ValueError(message)
def digest(raw):
    return hashlib.sha256(raw).hexdigest()
def normalize(text):
    return " ".join(unicodedata.normalize("NFC",text).translate(str.maketrans({
        "“":'"',"”":'"',"‘":"'","’":"'","—":"-","–":"-","…":"..."})).split())
def quote_ok(part,whole):
    if not isinstance(part,str) or not part.strip():return False
    if part in whole:return True
    part=normalize(part)
    if len(part)>2 and part[0]==part[-1] and part[0] in ('"',"'"):part=part[1:-1].strip()
    return bool(part and part in normalize(whole))

def verify_manifest():
    hashes=read("SHA256.json")
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    check(set(hashes)|{"SHA256.json"}==actual,"Unexpected or missing release member")
    for name,h in hashes.items():
        check(digest((ROOT/name).read_bytes())==h,"Changed release member: "+name)

def verify_coverage(cases,docs):
    summary=read("coverage/results.json");audit={};ref=read("opportunities.json")
    check(summary["first_forms"]==48,"Supplementary form count")
    categories={"cover_both","accurate_one","wrong_mixed","no_substantive","insufficient","missing"}
    valid_states={"supported","contradicted","untouched","unclear","missing"}
    keys={(c,a,rep,t) for c in IDS for a in ARMS for rep in REPS for t in cases[c]["opportunities"]["material"]}
    for j in READERS:
        rows=read("coverage/"+j+"-turns.json")
        ix={(r["case"],r["arm"],str(r["rep"]),r["turn"]):r for r in rows}
        check(set(ix)==keys and len(ix)==len(rows)==96,"Coverage subset or case/arm/replicate pairing unsuitable")
        audit[j]=ix
        for (c,a,rep,t),row in ix.items():
            check(ref[c][str(t)]["role"]=="material" and len(ref[c][str(t)]["interpretations"])==2,
                  "Coverage yield should concern two predeclared live meanings")
            desc=row["category"];ev=row.get("evidence") or {};answer=docs[c][a][rep][t-1]["answer"]
            check(desc in categories,"Unknown coverage class")
            if row.get("quote_match"):
                check(quote_ok(ev.get("quote"),answer),"Coverage overall answer quote falls outside current answer")
            states=row["states"];br=row["branch_quote_match"]
            for side in ("A","B"):
                check(states[side] in valid_states,"Unknown branch evaluation")
                if br.get(side):
                    check(quote_ok((ev.get(side) or {}).get("quote"),answer),"Coverage branch quote mismatch")
                if states[side] in ("supported","contradicted","unclear"):
                    check(br.get(side) and (ev.get(side) or {}).get("state")==states[side],"Branch claim lacks grounded citation")
            states=set(states.values())
            expected=("missing" if "missing" in states else "wrong_mixed" if "contradicted" in states
                      else "insufficient" if "unclear" in states else "cover_both" if states=={"supported"}
                      else "no_substantive" if states=={"untouched"} else "accurate_one")
            check(desc==expected,"Coverage decision differs from two source branch labels")
            if desc!="missing":
                check(row.get("quote_match") and isinstance(ev.get("reason"),str) and ev["reason"].strip(),
                      "Nonmissing supplementary decision without supporting answer")
        for a in ARMS:
            counts=Counter(row["category"] for (cid,arm,rep,t),row in ix.items() if arm==a)
            target=summary["readers"][j]["by_arm"][a]
            check(target["n"]==sum(counts.values())==32 and
                  all(counts[k]==target["counts"].get(k,0) for k in categories),"Coverage class count differs")
            for c in IDS:
                actual=Counter(v["category"] for (cid,arm,rep,t),v in ix.items() if cid==c and arm==a)
                target=summary["readers"][j]["by_case"][c][a]
                check(target["n"]==sum(actual.values())==4 and
                      all(actual[k]==target["counts"].get(k,0) for k in categories),"Case-specific coverage counts differ")
    for a in ARMS:
        joint=Counter()
        for key in keys:
            if key[1]==a:
                left=audit["gpt"][key]["category"];right=audit["opus"][key]["category"]
                joint[left+"|"+right]+=1
        target=summary["cross_reader_by_arm"][a]
        valid=sum(n for k,n in joint.items() if "missing" not in k.split("|"))
        exact=sum(n for k,n in joint.items() if len(set(k.split("|")))==1 and "missing" not in k.split("|"))
        check(target["available"]==valid and target["exact"]==exact,"Coverage concordance summaries differ")
        check(all(joint[k]==v for k,v in target["matrix"].items()) and
              all(target["matrix"].get(k)==v for k,v in joint.items()),"Supplementary cross-reader matrix mismatch")
    print("Verified 96 supplementary two-interpretation probes per reader, first-outcome classes, citations and agreement matrices.")

def verify():
    verify_manifest()
    b=(ROOT/"prompts/B.txt").read_bytes()
    bc=(ROOT/"prompts/BC.txt").read_bytes()
    check(bc.startswith(b) and bc[len(b):].strip()==(ROOT/"prompts/RULE.txt").read_bytes().strip(),
          "Candidate change does not isolate appended rule")
    cases={c["id"]:c for c in read("cases.json")}
    docs=read("interviews.json");scores=read("first_scores.json");score_summary=read("aggregate/primary.json")
    challenge=read("aggregate/defect_controls.json");decision=read("aggregate/decision.json")
    calculations=runpy.run_path(str(ROOT/"analysis/decision.py"))
    check(set(cases)==set(docs)==set(IDS) and set(scores)==set(READERS),"Unexpected cases/readers")
    check(score_summary["first_answers"]==576 and score_summary["total_interviews"]==48 and
          score_summary["reader_sessions"]==192,"Incorrect study sample counts")
    for c in IDS:
        expected=cases[c]["questions"]
        check(len(expected)==12 and len(set(expected))==12 and set(docs[c])==set(ARMS),"Case/question count")
        for arm in ARMS:
            check(set(docs[c][arm])==set(REPS),"Interview missing a replicate")
            for rep in REPS:
                d=docs[c][arm][rep]
                check([t["question"] for t in d]==expected and all(isinstance(t["answer"],str) and t["answer"].strip()
                      for t in d),"Questions or first answers differ across arms")

    for j in READERS:
        status=Counter();preserved=[]
        for c in IDS:
            diffs=[]
            for arm in ARMS:
                for rep in REPS:
                    vals=scores[j][c][arm][rep]
                    check([v["round"] for v in vals]==[1,2],"First round labels")
                    for v in vals:
                        status[v["status"]]+=1
                        if v["status"]=="invalid_first_form":
                            check(v["score"] is None,"Invalid form has numeric score")
                            continue
                        check(v["status"]=="valid" and v["score"] in (1,2,3,4) and v["evidence"] and v["rationale"].strip(),"Score integrity")
                        for e in v["evidence"]:
                            t=e["turn"]
                            check(type(t) is int and 1<=t<=12 and e["quote"] and
                                  e["quote"] in docs[c][arm][rep][t-1]["answer"],"First rating citation changed")
                    check([x["score"] for x in vals]==score_summary["scores"][j][c][arm][rep],"Replicate score mismatch")
            for rep in REPS:
                for i in range(2):
                    v=scores[j][c]["BC"][rep][i]["score"];b0=scores[j][c]["B"][rep][i]["score"]
                    diffs.append(None if v is None or b0 is None else v-b0)
            if all(d is not None and d>=0 for d in diffs):preserved.append(c)
        check(status==Counter(score_summary["status"][j]) and sum(status.values())==96,"Reader rating completeness")
        pres=decision["readers"][j]["reality"]["contrasts"]["BC_vs_B"]["preserved_cases"]
        check(set(preserved)==set(pres) and len(preserved)==len(pres),"No-worse case count changed")
        errors=challenge[j]["pairs"]
        check(len(errors)==4 and all(len(x["error"])==len(x["original"])==2 for x in errors.values()), "Invalid error contrasts")
        wins=sum(all(type(y) is int and type(z) is int and y<z for y,z in zip(v["error"],v["original"])) for v in errors.values())
        check(wins==challenge[j]["stable_degradation"] and (wins>=3)==challenge[j]["qualified"],"Error-control downgrades")

        design={}
        for c in IDS:
            op=cases[c]["opportunities"]
            design[c]={n:label for label in CATEGORIES for n in op[label]}
            check(set(design[c])==set(range(1,13)),"Missing opportunity definition")
        allrows=read("behavior/"+j+"-turns.json")
        keys={(v["case"],v["arm"],str(v["rep"]),v["turn"]) for v in allrows}
        check(len(keys)==len(allrows)==576,"Repeated or missing behavior turns")
        counts={(a,g):Counter() for a in ARMS for g in CATEGORIES};prefixes=0
        for v in allrows:
            c,a,r,t=v["case"],v["arm"],str(v["rep"]),v["turn"]
            check(c in IDS and a in ARMS and r in REPS and t in range(1,13),"Unexpected behavior record")
            typ=design[c][t]
            check(typ==v["planned"] and v["followup"]==(t in cases[c]["opportunities"]["followup"]),"Behavior opportunity type")
            ctr=counts[a,typ];ctr["eligible"]+=1
            ctr["targeted"]+=v["action"]=="targeted_yield"
            ctr["specific_or_generic"]+=v["action"] in ("targeted_yield","generic_yield")
            ctr["all_waiting"]+=v["action"] in ("targeted_yield","generic_yield","incidental_yield")
            doc=docs[c][a][r][t-1]
            if v.get("event_citation_match"):
                check(quote_ok((v.get("event_evidence") or {}).get("quote"),doc["answer"]),"Behavior answer quote")
            if typ!="clear":
                prefixes+=1
                if v.get("prefix_citation_match"):
                    check(quote_ok((v.get("prefix_evidence") or {}).get("question_quote"),doc["question"]),"Prefix question quote")
        check(prefixes==192,"Prefix design denominator")
        for (a,typ),ct in counts.items():
            expected={"material":32,"context_resolved":16,"same_answer":16,"clear":128}[typ]
            reported=decision["readers"][j]["behavior"]["by_arm"][a][typ]
            check(ct["eligible"]==reported["eligible"]==expected,"Behavior denominator")
            check(reported["targeted"]==ct["targeted"] and reported["wait_any"]==ct["specific_or_generic"] and
                  reported["wait_including_incidental"]==ct["all_waiting"],"Behavior counts differ")
        rederived={"reality":calculations["reality"](score_summary["scores"][j]),
                   "behavior":calculations["behavior"](allrows),"calibration":challenge[j]}
        check(json.loads(json.dumps(rederived))==decision["readers"][j],"Full decision reanalysis disagrees")
        print(f"{j}: 96 first ratings; {len(preserved)}/8 cases with BC≥B in both replicates and ratings; {wins}/4 error-control downgrades; 576 turn actions, 192 prospective need evaluations.")
    reality=all(r["calibration"]["qualified"] and not r["reality"]["saturated"] and
                r["reality"]["contrasts"]["BC_vs_B"]["operational_preservation"] for r in decision["readers"].values())
    behavior=all(all(r["behavior"]["gates"].values()) for r in decision["readers"].values())
    check(decision["decision"]=={"realism":reality,"behavior":behavior,"joint_research_candidate":reality and behavior},
          "Final joint decision mismatch")
    verify_coverage(cases,docs)
    print("Verified 48 fictional English interviews and 576 first answers, all primary scores, control grades and condition-specific waiting counts.")

if __name__=="__main__":
    verify()
