"""Find illustrative matched fictional replies, using a fixed case/turn ordering."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def read(p):
    return json.loads(p.read_text())
def build():
    key={(r["case"],r["arm"]):r["id"] for r in read(HERE.parent/"key.json") if r["case"].startswith("H")}
    codes=read(HERE/"codes.json")
    examples={}
    for (case,arm),uid in sorted(key.items()):
        if arm!="T1":continue
        ids={a:key[case,a] for a in ("B","T0","T1")}
        docs={a:read(HERE/"input"/(i+".json")) for a,i in ids.items()}
        for turn in docs["T1"]["opportunities"]["ambiguous"]:
            yes={a:turn in codes[i]["clarify_yield"]["positive"] for a,i in ids.items()}
            uncertain=any(turn in codes[i]["clarify_yield"]["uncertain"] for i in ids.values())
            if uncertain:continue
            label="T1_only_vs_T0" if yes["T1"] and not yes["T0"] else "T0_only_vs_T1" if yes["T0"] and not yes["T1"] else "both" if yes["T0"] else "neither"
            if label in examples:continue
            examples[label]={"case":case,"turn":turn,"question":docs["T1"]["dialogue"][turn-1]["question"],
                             "answers":{a:d["dialogue"][turn-1]["answer"] for a,d in docs.items()},"yield":yes}
    (HERE/"examples.json").write_text(json.dumps(examples,ensure_ascii=False,indent=2)+"\n")
if __name__=="__main__":
    build()
