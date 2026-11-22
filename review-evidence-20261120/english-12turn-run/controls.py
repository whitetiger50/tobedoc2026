"""Generate the prespecified destructive controls and audit their paired length variants."""
import json
import re
from pathlib import Path
from dispatch import HERE, read, write, natural_path

def words(a):
    return sum(len(re.findall(r"[\w]+(?:['’][\w]+)*",s)) for s in a)
def build():
    audit=[]
    for n in range(1,5):
        c=f"D{n:02}"
        rows=[read(natural_path(c,"T0",j)) for j in range(1,13)]
        source=[r["raw"] for r in rows]
        if n==1:
            err=[f"Patient response recorded as follows. Subjective report: {s} End of entry." for s in source]
        elif n==2:
            err=[s if t%2 else s+" I already put the paper in that drawer. I already put the paper in that drawer." for t,s in enumerate(source,1)]
        elif n==3:
            err=source[5:]+source[:5]
        else:
            err=[s if t not in (3,6,9,12) else "As your interviewer, I'd like you to tell me a bit more about that." for t,s in enumerate(source,1)]
        write(HERE/"controls"/(c+"-Error.json"),dict(answers=err))
        path=HERE/"controls"/(c+"-Length.json")
        if not path.exists(): continue
        variant=read(path)["answers"]
        assert len(variant)==12 and all(isinstance(s,str) and s.strip() for s in variant)
        orig,edit=words(source),words(variant)
        direction=1 if n in (2,4) else -1
        change=(edit-orig)/orig*direction
        audit.append(dict(case=c,original_words=orig,variant_words=edit,signed_change=(edit-orig)/orig,
                          target_range_met=.20<=change<=.50))
    if len(audit)==4:
        write(HERE/"controls"/"length-counts.json",audit)
    return audit
if __name__=="__main__":
    print(json.dumps(build(),indent=2))
