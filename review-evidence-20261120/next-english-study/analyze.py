"""Apply locked case-level decision criteria and report comparable exposure denominators."""
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
from statistics import median
import sys

HERE=Path(__file__).resolve().parent
PREV=HERE.parent/"english-12turn-run"
sys.path.insert(0,str(HERE/"patient-anchor"))
from anchor import score_dialogues
def read(path):return json.loads(path.read_bytes())
def save(path,x):path.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n")
def words(s):return re.findall(r"[A-Za-z]+(?:['’][A-Za-z]+)*",s)
def lexical(root,key):
    docs=defaultdict(list); lens={}
    for k in key:
        c,a=k["case"],k["arm"]
        p=read(root/"blind"/(k["id"]+".json"))["dialogue"]
        docs[a].append(p)
        lens.setdefault(c,{})[a]=sum(len(words(t["answer"])) for t in p)
    return ({a:{n:score_dialogues(ds,n=n) for n in (4,5,6)} for a,ds in docs.items()},lens)
def finish():
    scores=read(HERE/"results.json")
    sem=read(HERE/"semantic/results.json")
    ctrl=read(HERE/"calibration/results.json")
    cases=read(HERE/"cases.json")
    strata={c["id"]:c["stratum"] for c in cases}
    lex,lens=lexical(HERE,read(HERE/"private/key.json"))
    oldlex,oldlens=lexical(PREV,[k for k in read(PREV/"key.json") if k["case"].startswith("H")])
    save(HERE/"lexical.json",{"method":"same DAIS-C 5–12 turn windows, preceding three turns; report 4/5/6 word phrases separately",
         "current":lex,"previous":oldlex,"current_interview_words":lens,"previous_interview_words":oldlens})
    judges={}
    for reader,x in scores["readers"].items():
        q=ctrl[reader]["qualifies"]
        s=sem["readers"][reader]
        bx=x["contrasts"]["T2_vs_B"]
        tx=x["contrasts"]["T2_vs_T1"]
        bad=Counter(strata[c] for c,d in bx["by_case"].items() if d=="loss")
        nn=s["by_case"]
        def delta(c,m):return nn[c]["T2"][m]["positive"]-nn[c]["T1"][m]["positive"]
        def ranges(c,m):return s["contrasts"]["T2_vs_T1"][m]["by_case"][c]["possible_difference"]
        def agg(m):return s["by_arm"]["T2"][m]["positive"]-s["by_arm"]["T1"][m]["positive"]
        def bounds(m):return [sum(ranges(c,m)[j] for c in nn) for j in (0,1)]
        def harms(m):return [c for c in nn if delta(c,m)>0]
        def maybe(m):return [c for c in nn if ranges(c,m)[1]>0]
        repeat="avoidable_recap"
        decreased=[c for c in nn if delta(c,repeat)<0]
        increased=[c for c in nn if delta(c,repeat)>0]
        similar=[c for c in decreased if .8<=lens[c]["T2"]/lens[c]["T1"]<=1.25]
        r_bounds={c:ranges(c,repeat) for c in nn}
        harm={m:harms(m) for m in ("evasive","consequential_invention","unsupported_stereotype")}
        votes=bx["counts"].get("win",0)+bx["counts"].get("tie",0)
        basecomp=votes>=6 and max(bad.values(),default=0)<2
        main=tx["counts"].get("win",0)>tx["counts"].get("loss",0)
        mech=len(decreased)>len(increased) and agg(repeat)<0
        func={m:agg(m) for m in ("clarify_yield","concrete_example")}
        judges[reader]={"qualifies":q,"B_stable_win_or_tie":votes,"B_competitiveness":basecomp,
            "stable_B_losses_by_stratum":dict(bad),"T1_more_stable_wins_than_losses":main,
            "win_threshold_T2_vs_B":bx["counts"].get("win",0)>=5,
            "win_threshold_T2_vs_T1":tx["counts"].get("win",0)>=5,
            "pooled_score_saturation":x["score_distribution"]["saturation_ge80"],
            "recap_reduced_cases":decreased,"recap_increased_cases":increased,
            "recap_total_change":agg(repeat),"recap_supported_from_positive_counts":mech,
            "recap_total_possible_change":bounds(repeat),"recap_uncertainty_by_case":r_bounds,
            "recap_robust_to_all_unresolved":bounds(repeat)[1]<0 and sum(hi<0 for lo,hi in r_bounds.values())>sum(hi>0 for lo,hi in r_bounds.values()),
            "similar_length_reduced_cases":similar,"similar_length_check":len(similar)>=3,
            "functional_change":func,"functional_change_bounds":{m:bounds(m) for m in func},
            "observed_function_preserved":all(v>=-1 for v in func.values()),
            "harms_increased":harm,"possible_increased_cases":{m:maybe(m) for m in harm},
            "observed_harm_gate":all(len(v)<2 for v in harm.values()),
            "robust_function":all(bounds(m)[0]>=-1 for m in func),
            "robust_harm":all(len(maybe(m))<2 for m in harm),
            "comparative_harm":{k:{m:sum(v["observed_difference"]>0 for v in s["contrasts"][k][m]["by_case"].values())
                                     for m in harm} for k in ("T2_vs_T1","T2_vs_B")}}
    qualified=[r for r,j in judges.items() if j["qualifies"]]
    adopted=(len(qualified)==2 and all(j["B_competitiveness"] and j["T1_more_stable_wins_than_losses"]
             and j["recap_supported_from_positive_counts"] and j["observed_function_preserved"] and j["observed_harm_gate"]
             and not j["pooled_score_saturation"] for j in judges.values()))
    robust=all(j["recap_robust_to_all_unresolved"] and j["robust_function"] and j["robust_harm"] for j in judges.values())
    superior={k:len(qualified)==2 and all(j["win_threshold_"+k] and not j["pooled_score_saturation"] and
                     all(v<2 for v in j["comparative_harm"][k].values()) for j in judges.values())
              for k in ("T2_vs_T1","T2_vs_B")}
    conditional=bool(qualified) and all(judges[r]["B_competitiveness"] and judges[r]["T1_more_stable_wins_than_losses"] and
                                         not judges[r]["pooled_score_saturation"] for r in qualified)
    out={"qualified_readers":qualified,"by_reader":judges,"adopt_as_research_candidate":adopted and robust,
         "observed_adoption_gates":adopted,"conditional_competitive_signal":conditional,
         "panel_superiority":superior,"adoption_robust_to_uncertainty":adopted and robust,
         "length_medians":{a:median(v[a] for v in lens.values()) for a in ("B","T1","T2")},
         "note":"Literal counts are separate from discourse coding. Sensitivity bounds include uncertainty and missing evidence; no clinical adoption assessed."}
    save(HERE/"decision.json",out)
    return out
if __name__=="__main__":print(json.dumps(finish(),ensure_ascii=False,indent=2))
