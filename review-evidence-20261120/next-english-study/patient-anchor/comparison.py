"""Post-primary local comparison using the frozen DAIS-C lexical recurrence rule."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from statistics import median
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import anchor
from anchor import Block, Speech, QUESTIONS, HERE, BASE, document_text


def metadata(root):
    ns={"n":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with ZipFile(root/"Metadata"/"Metadata.xlsx") as z:
        strings=["".join(y.text or "" for y in x.findall(".//n:t",ns))
                 for x in ET.fromstring(z.read("xl/sharedStrings.xml"))]
        rows=ET.fromstring(z.read("xl/worksheets/sheet1.xml")).findall(".//n:row",ns)
    records={}
    for sheet_row in rows:
        row={}
        for cell in sheet_row.findall("n:c",ns):
            v=cell.find("n:v",ns)
            if v is not None:
                row[re.sub("[0-9]+","",cell.get("r"))]=strings[int(v.text)] if cell.get("t")=="s" else v.text
        if re.fullmatch(r"<[0-9A-Za-z]{6}>",row.get("A","")):
            key=row["A"][1:-1].upper()
            assert key not in records
            records[key]={k:row[k] for k in ("B","AC","AD")}
    return records


def anchored(path):
    # Identical full-tag block extraction to anchor.parse(), with an explicit general opening rule.
    text=document_text(path)
    patient=path.stem[:-5].lower()
    role_open=re.compile(r"<\s*("+re.escape(patient)+r"|int|doc|fam)\s*>",re.I)
    openings=list(role_open.finditer(text))
    blocks=[]
    for i,match in enumerate(openings):
        role=match.group(1).lower()
        seg=text[match.end():openings[i+1].start() if i+1<len(openings) else None]
        ends=list(re.finditer(r"</\s*"+re.escape(role)+r"\s*>",seg,re.I))
        if len(ends)!=1:
            blocks.append(Block(role,Speech((),False),False));continue
        value=anchor.speech(seg[:ends[0].start()])
        clean=value.clean and (i==len(openings)-1 or not seg[ends[0].end():].strip())
        blocks.append(Block(role,value,clean))
    selection=None
    for i,b in enumerate(blocks[:10]):
        if b.role!="int":
            continue
        group=next((q for q,phrase in QUESTIONS.items() if phrase in " ".join(b.value.tokens)),None)
        if group:
            if i+1<len(blocks) and blocks[i+1].role==patient:
                selection=(i,group)
            break
    if selection is None:
        idx=next((i for i in range(len(blocks)-1) if blocks[i].role=="int" and
                  blocks[i+1].role==patient and blocks[i].clean and blocks[i+1].clean),None)
        if idx is None:
            return None
        selection=idx,"other"
    i,group=selection
    seq=blocks[i:]
    return group,seq,[j for j,b in enumerate(seq) if b.role==patient]


def window(people,last):
    values=anchor.stats(people,5,maximum=last,prompt_filter=True)
    rates=[]
    for p in people:
        counts=anchor.inspect(p,5,last,True)[1]
        if counts["opportunities"]:
            rates.append(counts["recurring_turns"]/counts["opportunities"])
    values["person_recurrence_fraction_median_range_eligible"]=[median(rates),min(rates),max(rates)] if rates else None
    values["participants_without_observable_window"]=len(people)-len(rates)
    values["participants_eligible_without_recurrence"]=len(rates)-values["people_with_recurrence"]
    return values


def summarize(people, missing=0):
    out={"participants":len(people)+missing,"anchored_interviews":len(people),"missing_opening":missing}
    for name,end in (("turns_5_12",12),("from_5_to_end",None)):
        w=window(people,end)
        w["anchored_without_observable_window"]=w["participants_without_observable_window"]
        w["participants_without_observable_window"]+=missing
        out[name]=w
    return out


def run():
    root,=BASE.parent.glob("DAIS_C*/DAIS-C-Annotated - Upload")
    meta=metadata(root)
    allgroups={}
    inventory={}
    raw_counts={}
    tags={}
    for group,acode,label in (("clinical","DAI-C-CL","A (clinical)"),("comparison","DAI-C-CO","C (comparison)")):
        folder=root/acode
        files=sorted(p for p in (folder/"Interactional/Full tagged pass").glob("*-FULL.*") if p.suffix.lower() in (".docx",".rtf") and not p.name.startswith("~$"))
        records=[r for r in meta.values() if r["B"]==label]
        ids={p.stem[:-5].upper() for p in files}
        assert len(ids)==len(files)
        assert all(meta[key]["B"]==label and meta[key]["AC"]=="yes" for key in ids)
        people=[]
        missing_turns=Counter()
        for p in files:
            person=anchored(p)
            if person is not None:
                people.append(person)
                continue
            turns=re.findall(r"<INT\s*>(.*?)</INT\s*>",document_text(p),re.I|re.S)
            for t in turns:
                missing_turns["interviewer_blocks"]+=1
                words=re.findall(r"[a-z]+",re.sub(r"<[^>]+>"," ",t),re.I)
                if not words and re.search(r"<mis\b",t,re.I):
                    missing_turns["missing_markers_no_spoken_word"]+=1
        inventory[group]={"metadata_rows":len(records),"archival_yes":sum(r["AC"]=="yes" for r in records),
                          "archival_no":sum(r["AC"]=="no" for r in records),"local_full_documents":len(files),
                          "matched_records_all_archival_yes":len(ids),"no_usable_start":len(files)-len(people),
                          "interviewer_blocks_in_unanchored_documents":dict(missing_turns),
                          "metadata_openings_in_full_documents":dict(Counter(meta[k]["AD"] for k in ids)),
                          "speaker_only_tagged_documents":len(list((folder/"Interactional/Full tagged pass/Speaker_only_for_analysis").glob("*.txt"))),
                          "timestamped_documents":sum(p.suffix in (".rtf",".docx") for p in (folder/"Timestamped").glob("*"))}
        allgroups[group]={"all":summarize(people,missing=len(files)-len(people))}
        for name in ("Q1","Q2","Q3","other"):
            subset=[p for p in people if p[0]==name]
            if subset:
                allgroups[group][name]=summarize(subset)
        tags[group]=set(p[0] for p in people)
        if group=="clinical":
            subset=[p for p in people if p[0] in ("Q2","Q3")]
            raw_counts[group]=summarize(subset)
            prior=json.loads((HERE/"aggregate.json").read_text())
            for earlier,new in ((prior["primary"],raw_counts[group]["turns_5_12"]),
                                (prior["sensitivities"]["all_turns_after_four"],raw_counts[group]["from_5_to_end"])):
                assert all(new[k]==v for k,v in earlier.items()),"Inherited clinical window fails replication"
    by_opening=sorted((tags["clinical"]&tags["comparison"])&{"Q1","Q2","Q3"})
    return {"source_anchor_code_sha256":hashlib.sha256((HERE/"anchor.py").read_bytes()).hexdigest(),
            "addendum_design_sha256":hashlib.sha256((HERE/"COMPARISON-DESIGN.ko.md").read_bytes()).hexdigest(),
            "comparison_code_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "inventory":inventory,"matched_opening_families":by_opening,"groups":allgroups,
            "previous_clinical_Q2_Q3":raw_counts["clinical"]}

if __name__=="__main__":
    d=run()
    (HERE/"comparison-aggregate.json").write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
    for g,data in d["groups"].items():
        print(g,d["inventory"][g])
        for typ,r in data.items():
            print(typ,r["participants"],[(s["target_turns"],s["eligible_turns"],s["repeat_turns"],s["eligible_people"],
                                        s["people_with_recurrence"]) for s in (r["turns_5_12"],r["from_5_to_end"])])
