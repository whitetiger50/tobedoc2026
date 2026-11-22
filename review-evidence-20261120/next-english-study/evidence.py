"""Inspect agreed, contested, and otherwise high-consequence flags on synthetic interviews."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text())
def main():
    cells=sorted(read(HERE/"private/key.json"),key=lambda x:(x["case"],x["arm"]))
    outputs=[]
    for cell in cells:
        uid=cell["id"]
        forms={r:read(HERE/"semantic"/r/uid/"accepted.json") for r in ("gpt","opus")}
        body=read(HERE/"blind"/(uid+".json"))
        for m in ("avoidable_recap","consequential_invention","unsupported_stereotype","evasive","concrete_example","clarify_yield"):
            for n in range(1,13):
                t=str(n); events={}
                for r,f in forms.items():
                    b=f["metrics"][m]
                    if b["labels"].get(t) in ("positive","uncertain"):events[r]={"label":b["labels"][t],"detail":b["events"][t]}
                if not events:continue
                outputs.append({"case":cell["case"],"arm":cell["arm"],"turn":n,"metric":m,"events":events,
                                "question":body["dialogue"][n-1]["question"],"answer":body["dialogue"][n-1]["answer"]})
    (HERE/"synthetic-evidence.json").write_text(json.dumps(outputs,ensure_ascii=False,indent=2)+"\n")
if __name__=="__main__":main()
