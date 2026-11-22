"""Create a v02-derived candidate; preserve all original text except one added fact block."""
import difflib
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ADDITION='''- 사실을 말할 때에는 그 내용뿐 아니라 누구의 일인지, 언제의 일인지, 일상적 경향인지 특정한 날의 사건인지, 빈도와 확실성이 어느 정도인지까지 주어진 범위를 유지한다. 평소의 경향을 이번 일의 확정된 경과로 바꾸거나 가능성을 사실로, 때때로 있는 일을 주된 양상으로 강화하지 않는다. 표현을 자연스럽게 바꾸는 것은 가능하지만 새 시간·빈도·인물·원인·확신을 덧붙이지 않는다.
- 서로 다른 사실에 공통된 행동이나 주제가 있더라도 그 사실들의 시간 범위와 관계를 자동으로 합치지 않는다. 평소의 행동 순서와 특정한 날의 일부 행동이 각각 주어졌다는 이유만으로 그 순서의 다른 행동도 그날 있었다고 확정하지 않는다. 이력 속에서 스스로 덧붙였던 세부 역시 반복되었다는 이유만으로 고정 사실의 근거가 되지 않는다.
- 답변에 담기로 한 내용의 구체적 주장과 수식이 설정의 내용·시간 범위·명시된 관계로 뒷받침되는지 확인한다. 근거 없는 부분만 빼고 나머지 설정 사실과 자연스러운 말투는 유지한다. 생략한 세부를 새 거절·기억 문제·무지·추가 걱정으로 대체하지 않는다. 이 확인은 아래 정보 공개·반복 규칙을 바꾸는 근거가 아니며, 확인 과정이나 사실 출처를 환자 발화에 해설하지 않는다.
'''


def main():
    source=ROOT/'speech_module/patient_v02.txt'
    old=source.read_text(); marker='\n의사소통과 질문 대응:\n'
    assert old.count(marker)==1
    new=old.replace(marker,ADDITION+marker)
    assert new.replace(ADDITION,'',1)==old
    assert old[old.index(marker):]==new[new.index(marker):]
    target=ROOT/'speech_module/patient_v05.txt'
    with target.open('x') as f:f.write(new)
    evidence={}
    for name in ['development/speech-m6-generation-variability-v01/author-flow-observations.json',
                 'development/speech-m6-generation-variability-v01/reviews/codex/validated.json',
                 'development/speech-m6-generation-variability-v01/reviews/claude/validated.json']:
        evidence[name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    metadata={'module_version':'schizophrenia-speech-m7-v0.5',
        'status':'v02_derived_fact_scope_engineering_hypothesis_not_clinical_validation',
        'parent_prompt':'speech_module/patient_v02.txt','parent_prompt_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'change_scope':'three added fact-boundary bullets only; all original v02 text preserved; disclosure and repetition rules byte-identical',
        'new_rules':['retain temporal/frequency/certainty/person scope','do not merge separate facts into unsupported event sequences','remove unsupported qualifiers without inventing refusal or withholding supported content'],
        'local_evidence_sha256':evidence,
        'source_attribution':'Own engineering design responding to M6 synthetic examples and explicit user request; no direct clinical or schizophrenia-specific validation claimed.',
        'no_changes':['case input schema','case facts','questions','patient knowledge','disclosure policy','repetition policy','generation model','post-generation editing'],
        'candidate_selection':'Explicit V05_VERSION registration; existing default VERSION remains v04 to preserve historical calls until a separate promotion decision.'}
    with target.with_suffix('.sources.json').open('x') as f:json.dump(metadata,f,ensure_ascii=False,indent=2);f.write('\n')
    (HERE/'diff-v02-v05.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='patient_v02.txt',tofile='patient_v05.txt')))
    print('Created v0.5: only three added fact-boundary bullets; original disclosure/repetition text unchanged')


if __name__=='__main__':main()
