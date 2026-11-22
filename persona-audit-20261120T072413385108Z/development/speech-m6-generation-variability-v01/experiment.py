"""18 fresh dialogues: three development cases x two frozen prompts x three starts."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import statistics
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PARENT = ROOT / 'development/speech-m4-v02-v04-compare-v01'
sys.path.insert(0, str(ROOT))
from collaboration.subscription_call import call_once, dump
from speech_module.core import TEMPLATES, V02_VERSION, VERSION, build_packet, canonical, generate, verify_packet

spec = importlib.util.spec_from_file_location('m1review', ROOT / 'development/speech-m1-v01/review_dev.py')
M1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M1)
VERSIONS = {'v02': V02_VERSION, 'v04': VERSION}
PROVIDERS = ('codex', 'claude')
DISCLOSURE = {'limited', 'partial_then_elaborated', 'early_broad', 'other', 'not_applicable', 'uncertain'}
REPETITION = {'brief_reconfirmation', 'useful_elaboration', 'mechanical_replay', 'mixed', 'no_repeated_topic', 'uncertain'}


def read(path): return json.loads(path.read_text())
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze():
    parent = read(PARENT / 'plan.json')
    old = read(PARENT / 'verification.json')['file_sha256']
    assert digest(PARENT / 'plan.json') == old[str((PARENT / 'plan.json').relative_to(ROOT))]
    cases = []
    for index, original in enumerate(parent['cases']):
        case = {k: deepcopy(original[k]) for k in ('case_id', 'input', 'questions', 'required_fact_ids')}
        assert 'speech_examples' not in case['input']
        for q, required in zip(case['questions'], case['required_fact_ids']):
            data = deepcopy(case['input']); data['current_question'] = q
            for version in VERSIONS.values():
                build_packet(data, module_version=version, required_fact_ids=tuple(required), question_reviewed=True)
        case['schedule'] = [{'replicate': r, 'order': ['v02', 'v04'] if (index+r)%2 else ['v04', 'v02']} for r in (1,2,3)]
        cases.append(case)
    protected = [p for p in (ROOT / 'speech_module').glob('*') if p.is_file()]
    protected += [p for p in (ROOT / 'share/PATIENTSIM-reliability-pilot-v01').glob('*') if p.is_file()]
    files = protected + [PARENT/'plan.json', PARENT/'review-packet.json', PARENT/'review-role.txt',
        ROOT/'collaboration/subscription_call.py', ROOT/'development/speech-m1-v01/review_dev.py',
        HERE/'experiment.py', HERE/'methods.md', HERE/'test_analysis.py']
    dump(HERE/'plan.json', {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'kind': 'fresh_generation_variability_development_experiment_not_final_confirmation',
        'authorization': 'explicit_user_request_three_new_dialogues_each_version_each_case_two_judges_once_prompts_unchanged',
        'versions': VERSIONS, 'cases': cases,
        'generation_model': parent['generation_model'], 'reasoning_effort': parent['reasoning_effort'],
        'new_dialogues_planned': 18, 'patient_turns_per_dialogue': 4, 'new_generation_CLI_calls_planned': 72,
        'review_CLI_calls_planned': {'codex': 1, 'claude': 1}, 'rating_outputs_planned': 36,
        'frozen_file_sha256': {str(p.relative_to(ROOT)): digest(p) for p in files},
        'history_policy': 'reset to identical authored history for every new dialogue; accumulate only that dialogue actual generated turns; no history summaries/truncation',
        'generation_order': 'three case workers; within case alternate first version by replicate, all outputs retained; replicate number is an administrative block, not shared sampling seed',
        'examples': False, 'sampling': 'one actual output per question; no best-of, regeneration, wrapper retries or exclusion based on score',
        'analysis_prespecified': {
            'primary': 'two integer Realism scores -> arithmetic mean per dialogue; three generated dialogues -> mean, sample SD, min/max per case/version; equal-case mean per version and case-specific v04-minus-v02',
            'reviewer_specific': 'retain both scores and condition means; each reviewer one fresh 18-dialogue packet, not three repeated ratings of fixed text',
            'text_variation': 'number of unique exact four-answer sequences among three starts and patient character-count range; descriptive only, not semantic quality or clinical diversity metrics',
            'flow': 'same-round categorical disclosure and repetition observations per judge with exact quotes; counts within case/version retain uncertain/mixed labels and disagreement; no new numeric clinical scale',
            'focus': 'case2 first sensitive-content turn, early disclosure versus partial elaboration and unresolved concern recurrence; case3 repeated routine/today question versus mechanical replay and unsupported specifics; case1 reconfirmation consistency',
            'limits': 'three reused synthetic profiles remain three clusters; single rating per generated dialogue confounds judge variation with score variation; no p-values, CI, optimization/equivalence or clinical superiority claims; do not pool M4/M5 scores',
        },
        'final_720_judgments': 'not_performed_plan_unchanged', 'clinical_validation': 'not_performed',
        'settings_limits': 'same explicit official CLI alias/effort; immutable server snapshot, temperature and generation seed not exposed',
    })
    print('Frozen same M4 inputs/prompts/model: 18 dialogues, 72 generation calls, 2 judge calls / 36 ratings', flush=True)


def verify():
    plan = read(HERE/'plan.json')
    for name, h in plan['frozen_file_sha256'].items():
        if digest(ROOT/name) != h: raise ValueError('Frozen file changed: '+name)
    return plan


def run_case(case):
    for block in case['schedule']:
        replicate = block['replicate']
        for label in block['order']:
            base = HERE/'runs'/case['case_id']/f'rep{replicate:02d}'/label
            if base.exists(): raise FileExistsError('Never regenerate a started dialogue: '+str(base))
            data = deepcopy(case['input']); dialogue = []
            for n, (question, required) in enumerate(zip(case['questions'],case['required_fact_ids']), 1):
                verify()
                data['current_question'] = question
                directory = base/f'turn{n:02d}'
                def backend(messages):
                    return call_once('codex', messages[1]['content'], messages[0]['content'], directory/'transport')
                answer = generate(data, backend, directory, module_version=VERSIONS[label],
                    required_fact_ids=tuple(required), question_reviewed=True)
                dialogue.extend([{'turn_id':f'D{n:02d}','speaker':'clinician','text':question},
                                 {'turn_id':f'P{n:02d}','speaker':'patient','text':answer}])
                data['history'].extend([{'speaker':'clinician','text':question},{'speaker':'patient','text':answer}])
                print(f"{case['case_id']} rep{replicate:02d} {label}: {n}/4 recorded", flush=True)
            dump(base/'transcript.json', {'item_id':f"{case['case_id']}-rep{replicate:02d}-{label}",
                'case_id':case['case_id'],'replicate':replicate,'condition':label,'module_version':VERSIONS[label],
                'patient':case['input']['patient'],'communication':case['input']['communication'],
                'authored_context':case['input']['history'],'generated_dialogue':dialogue,'partition':'development'})
    return case['case_id']


def make_review():
    plan = verify()
    previous = read(PARENT/'review-packet.json')
    items = []
    for index,c in enumerate(plan['cases'],1):
        for replicate in (1,2,3):
            for label in VERSIONS:
                path = HERE/'runs'/c['case_id']/f'rep{replicate:02d}'/label/'transcript.json'
                t = read(path)
                items.append({'profile_ref':f'PROFILE-{index}', 'transcript':t,
                              'path':str(path.relative_to(ROOT)), 'sha256':digest(path)})
    rng = random.Random(2026111806)
    while True:
        rng.shuffle(items)
        if all(a['profile_ref'] != b['profile_ref'] for a,b in zip(items,items[1:])): break
    cases=[]; key={}
    for number, item in zip(rng.sample(range(100,999),18), items):
        blind=f'G{number}'
        cases.append({'blind_id':blind, 'profile_ref':item['profile_ref'],
                      'generated_dialogue':item['transcript']['generated_dialogue']})
        t=item['transcript']
        key[blind]={k:t[k] for k in ('item_id','case_id','replicate','condition')}
        key[blind].update(transcript_path=item['path'],transcript_sha256=item['sha256'])
    packet={'purpose':'single_pass_development_review_of_fresh_synthetic_dialogues',
            'score_anchors':previous['score_anchors'], 'anchor_adaptation':previous['anchor_adaptation'],
            'profiles':previous['profiles'], 'cases':cases}
    role=(PARENT/'review-role.txt').read_text().replace('여섯 대화를','열여덟 대화를').replace('M4-A','G100')
    role+='''
이번 묶음은 대화별 score·reason·evidence·issues·uncertainty 외에 아래 두 관찰을 각 review 객체 안에 추가한다. 새 수치 척도가 아니며 score 앵커는 위와 같다.
"disclosure_flow":{"first_sensitive_turn":"P01|P02|P03|P04|none|uncertain","pattern":"limited|partial_then_elaborated|early_broad|other|not_applicable|uncertain","explanation":"한 문장의 관찰","evidence":[{"patient_turn_id":"P01","quote":"실제 환자 원문 인용"}]},
"repetition_flow":{"pattern":"brief_reconfirmation|useful_elaboration|mechanical_replay|mixed|no_repeated_topic|uncertain","explanation":"한 문장의 관찰","evidence":[{"patient_turn_id":"P03","quote":"실제 환자 원문 인용"}]}.
first_sensitive_turn은 생성된 환자 턴에서 설정된 민감 경험/믿음이 처음 언급된 턴이다. 작성 문맥은 이 턴 번호에 포함하지 않는다. 민감 정보가 없거나 판단하기 어렵다면 none/uncertain으로 둔다.
disclosure pattern은 제한적 공개(limited), 일부 공개 뒤 관련 후속 질문에서 새 설정 정보를 덧붙임(partial_then_elaborated), 초반에 여러 민감 내용을 한꺼번에 제시(early_broad), 기타/비해당/불확실을 구분한다. early_broad나 빠른 공개 자체가 자동 오류는 아니다. 설정·실제 질문·우려에 대한 답변 여부를 함께 고려한다.
repetition pattern은 사실 재확인에 대한 짧은 재답변, 관련 추가 설명, 질문과 무관한 기계적 재생, 혼합, 반복 주제 없음, 불확실을 구분한다. 질문이 비슷해서 답이 같은 경우나 답받지 못한 우려의 재질문을 자동 감점하지 않는다. 이전과 연결하는 특정 표현이나 공개 지연을 정답으로 요구하지 않는다.
두 관찰은 각각 실제 환자 인용을 최소 하나 포함한다. 최초 민감 턴이 P01~P04이면 해당 턴의 근거도 disclosure evidence에 포함한다. 설명은 각각 한 문장으로 짧게 쓴다. 사실 보존/미설정 구체화 우려는 기존 issues나 uncertainty에 실제 인용과 함께 남긴다.
대화별 독립적으로 평정하며 다른 대화 ID를 이유에 참조하거나 순위를 매기지 않는다. 같은 프로필의 대화가 있다는 이유로 차이를 만들지 않는다. reason은 1~2문장, issues는 가장 중요한 0~2개로 제한한다. 프롬프트 수정 제안은 실행하지 않으며 module_suggestions는 빈 배열로 둘 수 있다. 총 18개 review를 빠짐없이 포함한다.
'''
    dump(HERE/'review-packet.json',packet); dump(HERE/'review-key-private.json',key)
    (HERE/'review-role.txt').write_text(role)
    assert (HERE/'review-packet.json').stat().st_size < 64000
    dump(HERE/'review-freeze.json', {'timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'packet_sha256':digest(HERE/'review-packet.json'), 'role_sha256':digest(HERE/'review-role.txt'),
        'key_sha256':digest(HERE/'review-key-private.json'), 'review_calls_each':1, 'ratings_each':18,
        'masking_limit':'source/version/replicate/generator hidden; similar texts in one packet may reveal related items; full independent presentation not guaranteed'})
    print('Frozen 18-dialogue review packet, bytes:',(HERE/'review-packet.json').stat().st_size,flush=True)


def validate_review(value,packet):
    rows=M1.validate_review(value,packet)
    cases={c['blind_id']:c for c in packet['cases']}
    for r in rows:
        turns={t['turn_id']:t['text'] for t in cases[r['blind_id']]['generated_dialogue'] if t['speaker']=='patient'}
        for field,allowed in [('disclosure_flow',DISCLOSURE),('repetition_flow',REPETITION)]:
            obs=r.get(field)
            if not isinstance(obs,dict) or obs.get('pattern') not in allowed or not obs.get('explanation'):
                raise ValueError('Missing/invalid qualitative flow observation')
            evidence=obs.get('evidence')
            if not isinstance(evidence,list) or not evidence: raise ValueError('Flow observation needs exact quote')
            for e in evidence:
                if e.get('patient_turn_id') not in turns or not e.get('quote') or e['quote'] not in turns[e['patient_turn_id']]:
                    raise ValueError('Flow quote not in actual patient turn')
        first=r['disclosure_flow'].get('first_sensitive_turn')
        if first not in {'P01','P02','P03','P04','none','uncertain'}: raise ValueError('Invalid first sensitive turn')
        if first in turns and not any(e['patient_turn_id']==first for e in r['disclosure_flow']['evidence']):
            raise ValueError('First sensitive turn needs direct evidence')
    return rows


def review(provider):
    verify(); frozen=read(HERE/'review-freeze.json')
    assert digest(HERE/'review-packet.json')==frozen['packet_sha256']
    assert digest(HERE/'review-role.txt')==frozen['role_sha256']
    out=call_once(provider,(HERE/'review-packet.json').read_text(),(HERE/'review-role.txt').read_text(),HERE/'reviews'/provider)
    parsed=M1.parse_review(out['text']); validate_review(parsed,read(HERE/'review-packet.json'))
    dump(HERE/'reviews'/provider/'validated.json',parsed)
    print(provider+': 18 scores and categorical flow quotes validated; one review call',flush=True)


def description(values):
    if len(values)!=3: raise ValueError('Exactly three generated dialogues required')
    return {'values':values,'mean':statistics.mean(values),'min':min(values),'max':max(values),
            'range':max(values)-min(values),'sample_sd':statistics.stdev(values)}


def analyze(items,reviews):
    if set(reviews)!=set(PROVIDERS): raise ValueError('Both reviewers required')
    item_rows=[]
    for item in sorted(items,key=lambda t:t['item_id']):
        ident=item['item_id']; scores={p:reviews[p][ident]['score'] for p in PROVIDERS}
        answers=[t['text'] for t in item['generated_dialogue'] if t['speaker']=='patient']
        item_rows.append({k:item[k] for k in ('item_id','case_id','condition','replicate')} | {
            'scores':scores,'mean':statistics.mean(scores.values()),
            'patient_characters':sum(map(len,answers)), 'exact_patient_sequence_sha256':hashlib.sha256(canonical(answers)).hexdigest(),
            'flow':{p:{field:reviews[p][ident][field] for field in ('disclosure_flow','repetition_flow')} for p in PROVIDERS}})
    groups=[]
    for case in sorted({r['case_id'] for r in item_rows}):
        values={}
        for version in VERSIONS:
            rows=[r for r in item_rows if r['case_id']==case and r['condition']==version]
            if len(rows)!=3 or {r['replicate'] for r in rows}!={1,2,3}: raise ValueError('Incomplete generation group')
            values[version]={'combined_scores':description([r['mean'] for r in rows]),
                'judges':{p:description([r['scores'][p] for r in rows]) for p in PROVIDERS},
                'unique_exact_patient_sequences':len({r['exact_patient_sequence_sha256'] for r in rows}),
                'patient_characters':description([r['patient_characters'] for r in rows]),
                'flow_counts':{p:{field:dict(Counter(r['flow'][p][field]['pattern'] for r in rows)) for field in ('disclosure_flow','repetition_flow')} | {
                    'first_sensitive_turn':dict(Counter(r['flow'][p]['disclosure_flow']['first_sensitive_turn'] for r in rows))} for p in PROVIDERS}}
        groups.append({'case_id':case,**values,'v04_minus_v02':values['v04']['combined_scores']['mean']-values['v02']['combined_scores']['mean']})
    means={v:statistics.mean(g[v]['combined_scores']['mean'] for g in groups) for v in VERSIONS}
    judge_means={p:{v:statistics.mean(g[v]['judges'][p]['mean'] for g in groups) for v in VERSIONS} for p in PROVIDERS}
    return {'kind':'descriptive_fresh_generation_comparison_not_clinical_validation', 'dialogues':18,'ratings':36,
        'items':item_rows,'cases':groups,'condition_means':means,'v04_minus_v02':means['v04']-means['v02'],
        'judge_condition_means':judge_means,'score_frequencies':{p:dict(Counter(r['scores'][p] for r in item_rows)) for p in PROVIDERS},
        'independent_case_clusters':3,
        'limits':'Three generated dialogues per group, single rating per judge per dialogue; score variation includes generation and judge variability. No pooling prior runs or inferential/clinical claim. Flow labels are unvalidated descriptive judgments, not clinical scale.'}


def aggregate():
    verify(); packet=read(HERE/'review-packet.json'); key=read(HERE/'review-key-private.json')
    items=[read(ROOT/m['transcript_path']) for m in key.values()]
    reviews={p:{key[r['blind_id']]['item_id']:r for r in validate_review(read(HERE/'reviews'/p/'validated.json'),packet)} for p in PROVIDERS}
    result=analyze(items,reviews);dump(HERE/'scores.json',result)
    print(json.dumps({k:result[k] for k in ('condition_means','v04_minus_v02','judge_condition_means','score_frequencies')},ensure_ascii=False,indent=2))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['freeze','verify','generate','review-packet','review','aggregate']);ap.add_argument('--provider',choices=PROVIDERS);a=ap.parse_args()
    if a.action=='freeze':freeze()
    elif a.action=='verify':verify();print('Frozen files verified')
    elif a.action=='generate':
        plan=verify()
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures=[pool.submit(run_case,c) for c in plan['cases']]
            for future in as_completed(futures): print('Completed all six dialogues for',future.result(),flush=True)
    elif a.action=='review-packet':make_review()
    elif a.action=='review':
        if not a.provider:ap.error('--provider required')
        review(a.provider)
    else:aggregate()


if __name__=='__main__':main()
