"""Prepare and validate pre-score Opus audit of controlled edits; contains fictional cases only."""
import json
from pathlib import Path
import random
import re
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from dispatch import read, write, natural_path
from controls import words
mapping={f"N{i}":f"D{n:02}" for i,n in enumerate([2,3,4,1],1)}
def prepare():
    cases={c["id"]:c for c in read(HERE.parent/"cases.json")}
    data=[]
    for i,(label,c) in enumerate(mapping.items()):
        original=[read(natural_path(c,"T0",n))["raw"] for n in range(1,13)]
        variant=read(HERE.parent/"controls"/(c+"-Length.json"))["answers"]
        a,b=(original,variant) if i%2==0 else (variant,original)
        data.append({"pair":label,"dialogue":[{"turn":n,"question":q,"A":x,"B":y} for n,(q,x,y) in enumerate(zip(cases[c]["questions"],a,b),1)]})
    txt="""Assess whether each pair of independently presented fictional interview versions preserves important facts, uncertainty, affect/stance, willingness, repair and conversational function on all twelve turns, well enough to interpret a score difference as primarily a length effect. Ignore trivial diction. Judge neutrality independently from any realism rating. A clear alteration of one substantive fact, degree of commitment, or turn function disqualifies the pair. If unsure flag the case rather than treating it as neutral. Give the decisive turn, both phrases, and a short concrete reason for a failure or uncertainty. In a strict JSON object with keys N1 N2 N3 N4 each value must be {"equivalence":"preserved|changed|uncertain","turn":integer or null,"reason":"concise explanation"}. No other output. There are no patient records in this packet.\n"""
    (HERE/"neutrality.txt").write_text(txt+json.dumps(data,ensure_ascii=False))
def finalize():
    rec=read(HERE/"neutrality-receipt.json")
    obj=json.loads(re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$","",rec["result"]))
    assert obj.keys()==mapping.keys()
    counts={r["case"]:r for r in read(HERE.parent/"controls/length-counts.json")}
    decisions={}
    for label,c in mapping.items():
        assert obj[label]["equivalence"] in ("preserved","changed","uncertain")
        decisions[c]=obj[label]["equivalence"]=="preserved" and counts[c]["target_range_met"]
    write(HERE.parent/"controls/neutrality.json",decisions)
    write(HERE.parent/"controls/neutrality-reasons.json",{c:obj[l] for l,c in mapping.items()})
    print(decisions)
if __name__=="__main__":
    {"prepare":prepare,"finalize":finalize}[sys.argv[1]]()
