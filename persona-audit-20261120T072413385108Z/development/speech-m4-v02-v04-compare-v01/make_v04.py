"""Make a narrow v03->v04 prompt change; preserve prior prompts and evidence."""
from copy import deepcopy
import difflib
import hashlib
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
R4="""[R4 정보 공개와 상호작용]
현재 질문이 요구하는 내용, 환자가 이미 말한 내용, 면담자가 그 걱정에 실제로 답한 내용을 구별한다. 민감한 경험은 disclosure, 설정된 경계심, 질문의 구체성, 앞선 상호작용을 함께 고려해 공개 범위를 정한다. 일상적인 정보는 경계심이 있다는 이유만으로 숨기지 않는다. 짧은 답변·적은 자발성·말하기 꺼림을 같은 현상으로 취급하지 않는다.
이미 공개한 민감 경험을 다시 물을 때에는 공개 전 상태로 돌아가지 않는다. 그렇다고 이전에 일부를 말했다는 이유로 나머지를 모두 공개할 필요도 없다. 더 말해 달라는 요청은 질문과 관련되고 아직 말하지 않은 설정 내용이 있을 때 그 범위에서 이어 답할 수 있다. 추가로 말할 설정 내용이 없으면 이미 말한 경험을 짧게 확인하거나 현재 질문에 필요한 부분만 다시 말할 수 있다. 새 감정·사건·원인을 만들어 답을 늘리지 않는다.
공개를 주저하는 설정이고 전달 범위 등에 대한 우려가 아직 해소되지 않았다면 확인을 먼저 하거나, 일부 경험을 말하면서 우려를 남기거나, 공개를 제한할 수 있다. 이 중 어느 한 순서도 모든 환자나 모든 턴에 강제하지 않는다. 우려에 대한 답을 이미 들었는지도 확인해, 해소되지 않은 질문의 반복과 이전 답변 전체의 재생을 구분한다. 설명이 있었다는 사실만으로 우려가 해소됐다고 가정하지 않는다.
설정된 자신의 관심사를 표현할 수 있지만 매 턴 증상이나 걱정을 끼워 넣지 않는다. 공감이나 비밀보장 설명 한 번, 턴의 경과만으로 신뢰·병식·증상이 자동으로 바뀌지 않는다. 반응의 변화는 사례의 허용 범위와 실제 상호작용에 따른다. 공개를 반드시 지연하거나 반드시 확대하는 일정은 두지 않는다.

"""
R7="""[R7 대화의 연속성]
history 전체가 앞선 면담이고 current_question이 다음 질문이다. 고정 사실과 이력이 충돌하거나 질문에 틀린 전제가 있으면 환자가 알고 이해하는 범위에서만 필요한 내용을 정정한다. 환자가 모르는 임상 기록을 낭독하거나 주관적 믿음을 면담자의 관점으로 교정하지 않는다. 이력의 미확인 내용을 자동으로 새 고정 사실로 삼지 않는다.
질문이 이미 말한 사실의 재확인인지, 같은 경험의 추가 설명을 원하는지, 새 내용을 묻는지에 맞춰 답한다. 재확인에는 같은 짧은 사실 답을 그대로 해도 된다. 추가 설명에서는 이력과 이어지는 관련 부분을 답하며, 같은 배경 설명 전체를 처음부터 다시 꺼내는 것을 기본으로 삼지 않는다. 이미 말한 점을 드러낼 필요가 있으면 자연스럽게 연결하되, 앞 발화를 언급하는 특정 문구를 매번 넣지는 않는다.
면담자가 같은 질문을 반복하면 사실을 유지하는 반복 답변도 가능하다. 아직 답을 듣지 못한 걱정은 다시 물을 수 있다. 반복 자체를 일괄 금지하거나, 단지 다르게 보이기 위해 말투를 바꾸거나, 반복을 피하려고 새 사건·감정을 덧붙이지 않는다. 추가 공개가 없다는 것을 자동으로 회피나 기억 문제로 설명하지 않는다.

"""


def main():
    parent=ROOT/'speech_module/patient_v03.txt'
    before=parent.read_text()
    after=re.sub(r'\[R4 .*?(?=\[R5 )',lambda _:R4,before,flags=re.S)
    after=re.sub(r'\[R7 .*?(?=\[R8 )',lambda _:R7,after,flags=re.S)
    assert before!=after
    out=ROOT/'speech_module/patient_v04.txt'
    with out.open('x') as f:f.write(after)
    mapping=deepcopy(json.loads((ROOT/'speech_module/patient_v03.sources.json').read_text()))
    mapping['module_version']='schizophrenia-speech-m4-v0.4'
    mapping['status']='targeted_development_hypothesis_not_clinical_validation'
    mapping['parent_prompt_sha256']=hashlib.sha256(parent.read_bytes()).hexdigest()
    mapping['change_scope']=['R4','R7']
    mapping['local_evidence']={}
    for provider in ['codex','claude']:
        p=ROOT/'development/speech-m3-v02-v03-compare-v01/reviews'/provider/'validated.json'
        mapping['local_evidence'][provider]={'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    mapping['user_constraints']=['no_mandatory_phrase','no_uniform_disclosure_delay','same_M3_case_settings_questions_model_for_v02_comparison']
    mapping['interpretation']='R4/R7 respond to model critiques and explicit user constraints. M3 reviewers disagreed on disclosure pace; no fixed pace is treated as clinically correct.'
    for r in mapping['rules']:
        if r['rule_id'] in ['R4','R7']:
            r['type']='M3_development_feedback_and_user_constrained_design_hypothesis'
            r['change_from_v03']='Distinguish prior disclosure, new related information, unanswered worries, factual reconfirmation, and elaboration; retain natural repetition without fixed phrases or fixed delay.'
    mapping.pop('post_review_revision',None)
    with out.with_suffix('.sources.json').open('x') as f:json.dump(mapping,f,ensure_ascii=False,indent=2);f.write('\n')
    (HERE/'diff-v03-v04.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='speech_module/patient_v03.txt',tofile='speech_module/patient_v04.txt')))
    print('v0.4 created; only R4/R7 prompt sections changed; no patient facts added.')


if __name__=='__main__':main()
