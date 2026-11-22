"""Create an allowlisted ZIP of the synthetic study; run its analysis again offline before writing."""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

import run

HERE=Path(__file__).resolve().parent
README="""# 영어 모의 면담의 선택적 되묻기 연구 재현 자료

압축을 전용 빈 폴더에 푼 뒤 그 폴더에서 `python3 -I -B verify.py`를 실행한다. 인터넷 연결이나 모델 계정 없이 Python 3.9 이상에서 고정된 관측 결과를 재계산할 수 있다. 주 분석 단위는 독립적으로 작성한 새 가상 사례 8개다.

- `cases.json`은 8개 가상 사례 카드, 각 12개의 영어 질문, 비교 전에 구분한 네 질문 유형과 후속 질문을 담는다. `opportunities.json`에는 질문의 의도, 가능한 해석과 분류 근거가 있다. `DESIGN.ko.md`는 결과 확인 전 설계 원문이다.
- `prompts/`에는 원형 B, B에 한 문장을 보탠 후보 BC, 비교 조건 T2의 실제 지시문 및 B의 MIT 라이선스가 있다. BC의 추가 문장은 RULE.txt로도 제공한다. B·BC는 원래의 역할별 대화 이력을 같은 세션에서 이어받고 T2는 매 턴 같은 사례와 해당 면담 이력을 JSON으로 읽었다.
- `interviews.json`은 사례 → 조건 → 생성 반복 → 12턴 순서다. 각 턴의 고정 질문과 합성 환자 첫 답을 보존했다. 표시된 생성 반복은 같은 질문으로 독립 생성한 면담이며 반복 간에 난수 시드는 맞추지 않았다.
- `first_scores.json`은 판독자 → 사례 → 조건 → 생성 반복 → 두 번의 현실성 평정 순서다. 점수, 원래 근거와 합성 환자 발화 인용을 포함한다. 각 판독 세션에서 한 면담만 보았다. `assessment/realism.json`은 실제 영어 점수 앵커와 판독 지시다. `aggregate/defect_controls.json`에는 별도의 가상 오류 대조 4쌍의 두 회차 점수와 통과 여부가 있다.
- `behavior/{gpt,opus}-turns.json`은 판독자당 576개 행이다. 한 행에 해당 턴의 설계 분류, 별도 질문 의미 판독(대상인 192턴만), 환자 응답 행동, 인용과 이유를 함께 읽을 수 있다. 질문 의미 판독에는 현재 답과 뒤 문답이 제공되지 않았다. 응답 판독은 별도 세션에서 이루어졌다. 본문에는 질문만으로 충분히 확인할 수 있었던지를 뜻하는 need와, 실제로 되묻고 기다렸는지를 뜻하는 action이 구분되어 있다. 판정에 쓸 수 없는 형식이나 인용은 결측으로 보존한다. 행동 판독자가 받은 정의는 `assessment/behavior.json`에 있다.
- `aggregate/primary.json`에는 새 면담 전체의 192개 평점 집계, `aggregate/decision.json`에는 사례·반복별 점수 대비, 질문별 행동 분모, 실제 맥락에서 공통으로 필요했던 질문의 결과 및 채택 문턱이 담겨 있다. `analysis/decision.py`는 원 분석 함수다. 검산기는 원점수·인용·문항 유형을 확인하고 주요 사례 수와 되묻기 빈도를 독립 계산한 후 모든 판정 항목을 재계산한다.
- 별도 보조 판독인 `coverage/`에는 서로 다른 답이 가능한 사전 지정 96개 턴에서, 되묻지 않고도 두 의미에 모두 정확하게 답했는지 살핀 규칙·판독자별 근거와 집계가 있다. A와 B는 원래 문항의 두 해석을 나타내며 `opportunities.json`의 순서를 따른다. 독립 검산에는 각 해석에 대한 응답 인용과 두 판독자의 범주 교차표가 포함된다. 이 탐색 결과로 주 연구의 합격 기준을 변경하지 않았다.
- 자료의 출처와 허용 조건은 `sources.json`, 무결성 목록은 `SHA256.json`에 있다. 모든 면담은 가상 연구 자료이며 결과는 임상적 평가를 대신하지 않는다.
"""

def encode(v):
    return (json.dumps(v,ensure_ascii=False,indent=2,sort_keys=True,allow_nan=False)+"\n").encode()

def clean_behavior(row):
    keys=("case","arm","rep","turn","planned","followup","need","action","responsiveness","harm",
          "prefix_citation_match","event_citation_match")
    out={k:row[k] for k in keys}
    for key,fields in (("prefix_evidence",("need","question_quote","reason","alternatives")),
                       ("event_evidence",("action","responsiveness","harm","quote","reason"))):
        evidence=row.get(key)
        if evidence is not None:
            run.check(isinstance(evidence,dict),"Unexpected behavior evidence syntax")
            evidence={k:evidence[k] for k in fields if k in evidence}
            if isinstance(evidence.get("alternatives"),list):
                evidence["alternatives"]=[{k:a[k] for k in ("meaning","answer") if k in a} if isinstance(a,dict) else {} for a in evidence["alternatives"]]
        out[key]=evidence
    return out

def clean_coverage(row):
    keys=("case","arm","rep","turn","category","quote_match","states","branch_quote_match")
    out={k:row[k] for k in keys}
    evidence=row.get("evidence")
    if isinstance(evidence,dict):
        clean={k:evidence[k] for k in ("quote","reason") if k in evidence}
        for branch in ("A","B"):
            v=evidence.get(branch)
            if isinstance(v,dict):
                clean[branch]={k:v[k] for k in ("state","quote") if k in v}
        evidence=clean
    out["evidence"]=evidence
    return out

def payload():
    run.verify_design();run.check_blind()
    files={}
    def addfile(name,p):
        files[name]=p.read_bytes()
    for name in ("B.txt","BC.txt","T2.txt","RULE.txt","LICENSE-PatientHub.txt"):
        addfile("prompts/"+name,HERE/name)
    for name in ("cases.json","opportunities.json","DESIGN.ko.md","verify.py"):
        addfile(name,HERE/name)
    addfile("analysis/decision.py",HERE/"decision.py")
    for name,src in (("primary","primary-results.json"),("decision","decision.json"),("defect_controls","challenge/results.json")):
        files["aggregate/"+name+".json"]=encode(run.read(HERE/src))
    files["assessment/behavior.json"]=encode(run.read(HERE/"behavior/rules.json"))
    cases=run.inputs();docs={c:{a:{} for a in run.ARMS} for c in cases}
    ratings={j:{c:{a:{} for a in run.ARMS} for c in cases} for j in ("gpt","opus")}
    for x in run.key():
        cid,arm,rep=x["case"],x["arm"],str(x["rep"])
        sample=run.read(HERE/"blind"/(x["id"]+".json"))
        run.check(sample["profile"]==cases[cid]["profile"],"Masked vs authored profile differs")
        docs[cid][arm][rep]=sample["dialogue"]
        for j in ratings:
            pair=[]
            for n in (1,2):
                v=run.assess.load_rating(j,n,x["id"])
                run.check(v["status"]!="missing","Unsubmitted primary rating")
                out={k:v[k] for k in ("round","status","score","reason","rationale") if k in v}
                if "evidence" in v:out["evidence"]=[{"turn":e["turn"],"quote":e["quote"]} for e in v["evidence"]]
                pair.append(out)
            ratings[j][cid][arm][rep]=pair
    files["interviews.json"]=encode(docs);files["first_scores.json"]=encode(ratings)
    for j in ratings:
        rows=run.read(HERE/"behavior"/(j+"-turns.json"))
        files["behavior/"+j+"-turns.json"]=encode([clean_behavior(x) for x in rows])
        coverage=run.read(HERE/"coverage"/(j+"-turns.json"))
        files["coverage/"+j+"-turns.json"]=encode([clean_coverage(x) for x in coverage])
    for name in ("rules.json","results.json"):
        files["coverage/"+name]=encode(run.read(HERE/"coverage"/name))
    packet=run.assess.packet(sample)
    files["assessment/realism.json"]=encode({"system":run.assess.SYSTEM,**{k:packet[k] for k in ("task","scale","output")}})
    files["sources.json"]=encode({
      "study":"2026-11-21 English B clarification study; 8 fictional outpatient cases, 576 simulated first replies",
      "generator":{"model":run.gen.MODEL,"effort":"medium","B_BC":"native role history","T2":"frozen JSON adapter"},
      "readers":{"gpt":run.assess.MODELS["gpt"],"opus":run.assess.MODELS["opus"]},
      "B":{"project":"PatientHub","commit":"54d5c8761a9055a1e86d153715607ef9fa26358a",
           "template":"https://github.com/Sahandfer/PatientHub/blob/54d5c8761a9055a1e86d153715607ef9fa26358a/patienthub/data/prompts/client/psyche.yaml",
           "license":"See prompts/LICENSE-PatientHub.txt; BC appends a team-authored conditional clarification instruction."},
      "score":{"project":"PATIENTSIM","commit":"9c262e692bd94305d922654d05bd1741c4d97433",
               "rubric":"https://github.com/dek924/PatientSim/blob/9c262e692bd94305d922654d05bd1741c4d97433/src/prompts/eval/llm_eval_metrics_persona.json",
               "adaptation":"Realism_w_Profile; original emergency-department wording adapted to psychiatric outpatient."},
      "participant_material":"All study and archived control dialogues are fictional. No real patient text shared."})
    files["README.ko.md"]=README.encode()
    for name,raw in files.items():
        if name.endswith(".json"):
            run.check(not re.search(r'"(?:session|session_id|provider|request_id|api_key|token|auth|account|account_id|workdir|cwd)"\s*:|(?:/Users/|/private/var/|/home/)[^\s"]+|\b[IEP][0-9a-f]{24}\b',raw.decode()),
                      "Nonpublic metadata in "+name)
    files["SHA256.json"]=encode({k:hashlib.sha256(v).hexdigest() for k,v in files.items()})
    return files

def pack(files):
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in sorted(files):
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.create_system=3
            info.external_attr=0o100644<<16
            z.writestr(info,files[name],compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    return out.getvalue()

def main():
    files=payload();raw=pack(files)
    run.check(pack(files)==raw,"ZIP bytes unstable")
    with tempfile.TemporaryDirectory() as temp:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            run.check(z.testzip() is None and set(z.namelist())==set(files),"ZIP integrity failure")
            z.extractall(temp)
        guard="""import runpy,sys
def offline(e,a):
    if e.startswith(('socket.','subprocess.')) or e in ('os.system','os.posix_spawn'):
        raise PermissionError('Offline-only validation')
sys.addaudithook(offline)
runpy.run_path(sys.argv[1],run_name='__main__')
"""
        subprocess.run([sys.executable,"-I","-B","-c",guard,str(Path(temp)/"verify.py")],cwd=temp,
                       stdin=subprocess.DEVNULL,check=True)
    output=HERE/"release";output.mkdir(exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output,delete=False) as f:
        f.write(raw);temporary=Path(f.name)
    dest=output/"clarification-research.zip"
    os.replace(temporary,dest)
    print(dest.name,len(files),"files",len(raw),"bytes SHA256",hashlib.sha256(raw).hexdigest())

if __name__=="__main__":
    main()
