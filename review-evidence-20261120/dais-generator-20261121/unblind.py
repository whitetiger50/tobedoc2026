"""Join the locked reader scores to the source key only after both readers finish."""
from collections import Counter
import json
import os
from pathlib import Path
from statistics import median

import experiment as exp


def main():
    os.umask(0o077)
    private=exp.PRIVATE
    key=json.loads((private/"key.json").read_text())
    blind=json.loads((private/"blind.json").read_text())
    scores=json.loads((private/"blind-ratings.json").read_text())
    audit=json.loads((exp.HERE/"blind-verification.json").read_text())
    assert audit["input_sha256"]==exp.digest(private/"blind.json")
    assert audit["ratings_sha256"]==exp.digest(private/"blind-ratings.json")
    assert not audit["submitted_source_metadata_fields"] and not audit["detected_tool_calls"]
    inputs={v["uid"]:v for v in blind}
    assert len(inputs)==len(key)==140 and set(inputs)==set(scores)=={v["uid"] for v in key}
    groups,original=exp.data_cases()
    schedule=json.loads((private/"schedule.json").read_text())
    source_slots={(v["person"],v["arm"],v["rep"]):v for v in schedule}
    assert len(source_slots)==126
    joined=[]
    for v in key:
        uid,person,arm,rep=(v[k] for k in ("uid","person","arm","rep"))
        assert groups[person]==v["question"] and inputs[uid]["question"]==original[person]["question"]
        if arm=="patient":
            assert rep==0
            answer=original[person]["answer"]
        else:
            j=source_slots[(person,arm,rep)]
            answer=json.loads((private/"generated"/(j["job"]+".json")).read_text())["raw"]
        assert inputs[uid]["answer"]==exp.presentation(answer)
        joined.append({**v,"readers":scores[uid]})
    exp.dump(private/"ratings.json",joined)
    length={}
    for arm in ("patient",*exp.ARMS):
        length[arm]={}
        for q in ("Q2","Q3","all"):
            rows=[r for r in joined if r["arm"]==arm and (q=="all" or r["question"]==q)]
            counts=[r["words"] for r in rows]
            answers=Counter(inputs[r["uid"]]["answer"] for r in rows)
            length[arm][q]={"n":len(counts),"min":min(counts),"median":median(counts),"max":max(counts),
                            "distinct_reply_texts":len(answers),"maximum_identical_reply_count":max(answers.values())}
    exp.dump(exp.HERE/"integrity.json",{"generated":126,"real":14,"matched_source_slots":len(joined),
             "generation_transport_failures":len(list((private/"failures").glob("*.json"))),
             "masked_sha256":audit["input_sha256"],"word_counts":length})
    print("Verified and joined all 140 source slots")


if __name__=="__main__":
    main()
