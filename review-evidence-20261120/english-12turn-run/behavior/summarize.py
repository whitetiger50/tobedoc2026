"""Join finalized masked turn annotations with the condition key for descriptive analysis."""
from collections import Counter
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
STUDY=HERE.parent
read=lambda p:json.loads(p.read_text())
scopes={"clarify_yield":"ambiguous","answer_then_check":"ambiguous","unnecessary_clarify":"clear",
        "give_example":"example","contradiction":None,"unanswered_repair":"ambiguous"}
def summarize():
    key={k["id"]:k for k in read(STUDY/"key.json") if k["case"].startswith("H")}
    codes=read(HERE/"codes.json")
    assert set(key)==set(codes) and len(key)==24
    counts={}; by_case={}; uncertainties={}
    for uid,record in codes.items():
        d=read(HERE/"input"/(uid+".json"))
        arm,c=key[uid]["arm"],key[uid]["case"]
        assert set(record)==set(scopes)|{"notes"}
        assert isinstance(record["notes"],list)
        for m,scope in scopes.items():
            allowed=set(d["opportunities"][scope]) if scope else set(range(1,13))
            s=record[m]
            assert set(s)=={"positive","uncertain"}
            pos,unc=[set(s[a]) for a in ("positive","uncertain")]
            assert len(pos)==len(s["positive"]) and len(unc)==len(s["uncertain"]) and not pos&unc and (pos|unc)<=allowed
            cites=[n for n in record["notes"] if n["metric"]==m]
            tagged={n["turn"] for n in cites if not n["reason"].startswith("Uncounted, reasonable")}
            assert tagged==pos|unc,(uid,m,"citation coverage")
            for n in cites:
                if n["turn"] not in pos|unc:
                    assert m=="unnecessary_clarify" and n["turn"] in allowed and n["reason"].startswith("Uncounted, reasonable")
                assert n["quote"].strip() and n["quote"] in d["dialogue"][n["turn"]-1]["answer"] and n["reason"].strip(),(uid,m,n)
            total=counts.setdefault(arm,{}).setdefault(m,Counter())
            total.update(positive=len(pos),uncertain=len(unc),opportunities=len(allowed))
            by_case.setdefault(c,{}).setdefault(arm,{})[m]=len(pos)
            uncertainties.setdefault(c,{}).setdefault(arm,{})[m]=len(unc)
    harms={}
    for base in ("B","T0"):
        harms["T1_vs_"+base]={m:{"increased_cases":[c for c in sorted(by_case) if by_case[c]["T1"][m]>by_case[c][base][m]],
                                    "cases_with_uncertainty":[c for c in sorted(by_case) if uncertainties[c]["T1"][m]+uncertainties[c][base][m]>0]}
                              for m in ("unnecessary_clarify","contradiction")}
    out=dict(arms=counts,by_case=by_case,uncertainties=uncertainties,contrast_harm=harms,
             source="separate blinded descriptive text audit; not a PATIENTSIM rating or an expert clinical reading")
    (HERE/"summary.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
    return out
if __name__=="__main__":
    print(json.dumps(summarize()["arms"],indent=2))
