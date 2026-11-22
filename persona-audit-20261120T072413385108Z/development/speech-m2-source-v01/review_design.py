"""One small source/design review per authorized subscription model; no patient grading."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT))
from collaboration.subscription_call import call_once, dump

ROLE="""당신은 가상 환자 발화 프롬프트의 근거와 설계를 비평하는 검토자다. 제공한 작은 묶음만 읽고 도구·웹·파일 탐색은 하지 않는다.
각 근거의 범위, 출처 유형, 미확보 자료, 원저와 새 설계의 차이를 엄격히 구분한다. 새로운 문헌이나 임상 검증 결과를 만들지 않는다.
조현병에 직접 적용할 수 없는 양극성장애·CBT·우울증·음성 모사의 지시를 무리하게 전이했는지 확인한다.
실제 환자 데이터나 전문의 검토가 없다. v0.3으로 생성한 발화도 아직 없다. 현실성 점수나 PATIENTSIM 평점을 매기지 않는다.
문맥 조건부 생성, 예시의 사실 오염, 모순되는 제약, 조현병 고정관념을 확인한다. source excerpts는 일부이며 완전한 원저 검증을 수행했다고 주장하지 않는다.
JSON 하나만 출력한다. 중대한 문제 최대 5개. {"issues":[{"id":"I1","severity":"high|medium|low","rule_ids":["R1"],"evidence_ids":["E1"],"problem":"구체적 문제와 근거 또는 불확실성","recommendation":"최소 수정"}],"retain":["유지할 장점 최대 2개"],"unverified":["아직 확인하지 못한 점"],"next_checks":["다음 확인 과제 최대 3개"]}
문제가 없으면 issues를 빈 배열로 둔다. 문헌이 방법을 사용했다는 사실을 그 방법의 조현병 타당성으로 바꾸지 않는다."""


def prepare():
    evidence=json.loads((HERE/'evidence-ledger.json').read_text())['evidence']
    excerpts=[]
    for e in evidence:
        if e['id']=='E8': continue
        text=re.sub(r'\s+',' ',(HERE/e['file']).resolve().read_text())
        i=text.index(e['anchor'])
        excerpts.append({'evidence_id':e['id'],'locator':e['locator'],'excerpt':text[max(0,i-90):i+390]})
    template=(ROOT/'speech_module/patient_v03.txt').read_text()
    packet={'kind':'M2_source_alignment_design_review_no_observed_patient_outputs',
      'source_evidence':evidence,'selected_primary_excerpts':excerpts,'proposed_prompt':template,
      'source_map':json.loads((ROOT/'speech_module/patient_v03.sources.json').read_text()),
      'implementation_summary':'v03 is default; v01/v02 remain selectable and verifiable. Optional speech_examples: 1..3 context/utterance/fact_ids/provenance entries. Provenance must be synthetic_author_example_not_patient_data; IDs must belong to known facts in same case. IDs do not semantically validate utterances. Earlier schemas reject the extra information. Legacy unknown-fact preflight remains author-annotated. No extra self-refinement calls.',
      'structural_tests':'24 offline tests passed, not clinical validation',
      'review_policy':'same packet once for GPT-6.1 Sol High and Claude Opus 5.5; qualitative design feedback only'}
    dump(HERE/'review-packet.json',packet)
    (HERE/'review-role.txt').write_text(ROLE)
    dump(HERE/'review-freeze.json',{'timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'packet_sha256':hashlib.sha256((HERE/'review-packet.json').read_bytes()).hexdigest(),
        'role_sha256':hashlib.sha256((HERE/'review-role.txt').read_bytes()).hexdigest(),
        'draft_prompt_sha256':hashlib.sha256(template.encode()).hexdigest(),
        'each_model_calls':1,'numeric_score':'not_applicable_no_generated_outputs'})
    print('Prepared source/design packet, bytes:',(HERE/'review-packet.json').stat().st_size)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','run']);parser.add_argument('--reviewer',choices=['codex','claude'])
    args=parser.parse_args()
    if args.action=='prepare': prepare();return
    if not args.reviewer: parser.error('--reviewer required')
    freeze=json.loads((HERE/'review-freeze.json').read_text())
    body=(HERE/'review-packet.json').read_text();role=(HERE/'review-role.txt').read_text()
    assert hashlib.sha256(body.encode()).hexdigest()==freeze['packet_sha256']
    assert hashlib.sha256(role.encode()).hexdigest()==freeze['role_sha256']
    if len(body.encode())>32000: raise ValueError('Packet too large; narrow it before a call')
    output=call_once(args.reviewer,body,role,HERE/'reviews'/args.reviewer)
    text=output['text'].strip()
    if text.startswith('```json\n') and text.endswith('```'):text=text[8:-3].strip()
    value=json.loads(text)
    assert isinstance(value['issues'],list) and len(value['issues'])<=5
    dump(HERE/'reviews'/args.reviewer/'parsed.json',value)
    print(args.reviewer+': design review received, no patient score')


if __name__=='__main__':main()
