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
PARENT = ROOT / 'development/speech-m6-generation-variability-v01'
sys.path.insert(0, str(ROOT))
from collaboration.subscription_call import call_once, dump
from speech_module.core import TEMPLATES, V02_VERSION, V05_VERSION, build_packet, canonical, generate, verify_packet

spec = importlib.util.spec_from_file_location('m1review', ROOT / 'development/speech-m1-v01/review_dev.py')
M1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M1)
VERSIONS = {'v02': V02_VERSION, 'v05': V05_VERSION}
PROVIDERS = ('codex', 'claude')
GROUNDING_KINDS = {'unsupported_detail','scope_shift','contradiction','causal_inference','uncertain'}


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
        case['schedule'] = [{'replicate': r, 'order': ['v02', 'v05'] if (index+r)%2 else ['v05', 'v02']} for r in (1,2,3)]
        cases.append(case)
    protected = [p for p in (ROOT / 'speech_module').glob('*') if p.is_file()]
    protected += [p for p in (ROOT / 'share/PATIENTSIM-reliability-pilot-v01').glob('*') if p.is_file()]
    files = protected + [PARENT/'plan.json', PARENT/'review-packet.json', PARENT/'review-role.txt',
        ROOT/'collaboration/subscription_call.py', ROOT/'development/speech-m1-v01/review_dev.py',
        HERE/'experiment.py', HERE/'methods.md', HERE/'test_analysis.py', HERE/'make_v05.py', ROOT/'tests/test_speech_v05.py', ROOT/'development/speech-m4-v02-v04-compare-v01/review-role.txt']
    dump(HERE/'plan.json', {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'kind': 'fresh_generation_variability_development_experiment_not_final_confirmation',
        'authorization': 'explicit_user_request_v02_derived_v05_fact_boundary_only_same_three_cases_three_generations_two_judges_once',
        'versions': VERSIONS, 'cases': cases,
        'generation_model': parent['generation_model'], 'reasoning_effort': parent['reasoning_effort'],
        'new_dialogues_planned': 18, 'patient_turns_per_dialogue': 4, 'new_generation_CLI_calls_planned': 72,
        'review_CLI_calls_planned': {'codex': 1, 'claude': 1}, 'rating_outputs_planned': 36,
        'frozen_file_sha256': {str(p.relative_to(ROOT)): digest(p) for p in files},
        'history_policy': 'reset to identical authored history for every new dialogue; accumulate only that dialogue actual generated turns; no history summaries/truncation',
        'generation_order': 'three case workers; within case alternate first version by replicate, all outputs retained; replicate number is an administrative block, not shared sampling seed',
        'examples': False, 'sampling': 'one actual output per question; no best-of, regeneration, wrapper retries or exclusion based on score',
        'analysis_prespecified': {
            'primary': 'two integer Realism scores -> arithmetic mean per dialogue; three generated dialogues -> mean, sample SD, min/max per case/version; equal-case mean per version and case-specific v05-minus-v02',
            'reviewer_specific': 'retain both scores and condition means; each reviewer one fresh 18-dialogue packet, not three repeated ratings of fixed text',
            'text_variation': 'number of unique exact four-answer sequences among three starts and patient character-count range; descriptive only, not semantic quality or clinical diversity metrics',
            'grounding': 'per-judge per-version counts of no_issue_identified/concern/uncertain over nine dialogues; retain finding kind, exact quote and referenced fact IDs; no clinical truth score; absence of baseline issues prevents claiming reduction',
            'focus': 'unsupported temporal/frequency/certainty/person/causal elaboration; examine all generated patient turns against profile; retain supported content and realism rather than avoiding all detail',
            'limits': 'three reused synthetic profiles remain three clusters; single rating per generated dialogue confounds judge variation with score variation; no p-values, CI, optimization/equivalence or clinical superiority claims; do not pool M6/M5 scores',
        },
        'final_720_judgments': 'not_performed_plan_unchanged', 'clinical_validation': 'not_performed',
        'settings_limits': 'same explicit official CLI alias/effort; immutable server snapshot, temperature and generation seed not exposed',
    })
    print('Frozen same M6 inputs/prompts/model: 18 dialogues, 72 generation calls, 2 judge calls / 36 ratings', flush=True)


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
        blind=f'H{number}'
        cases.append({'blind_id':blind, 'profile_ref':item['profile_ref'],
                      'generated_dialogue':item['transcript']['generated_dialogue']})
        t=item['transcript']
        key[blind]={k:t[k] for k in ('item_id','case_id','replicate','condition')}
        key[blind].update(transcript_path=item['path'],transcript_sha256=item['sha256'])
    packet={'purpose':'single_pass_development_review_of_fresh_synthetic_dialogues',
            'score_anchors':previous['score_anchors'], 'anchor_adaptation':previous['anchor_adaptation'],
            'profiles':previous['profiles'], 'cases':cases}
    role=(ROOT/'development/speech-m4-v02-v04-compare-v01/review-role.txt').read_text().replace('여섯 대화를','열여덟 대화를').replace('M4-A','H100')
    role+='\n대화마다 기존 score·reason·evidence·issues·uncertainty 외에 grounding_review를 추가한다. 이는 새 수치 척도가 아니다.\n"grounding_review":{"checked_turn_ids":["P01","P02","P03","P04"],"status":"no_issue_identified|concern|uncertain","findings":[{"patient_turn_id":"P03","quote":"실제 환자 원문 인용","kind":"unsupported_detail|scope_shift|contradiction|causal_inference|uncertain","fact_ids":["해당 프로필의 사실 ID"],"explanation":"구체적 주장과 설정 근거 또는 근거 부재를 한두 문장으로 설명"}],"uncertainty":"판단 한계 또는 없음"}.\n각 환자 턴의 구체적 주장을 설정·자기 이해·작성 문맥과 대조한다. 인물·시점·일상/특정날·빈도·확신·사건 관계를 구별하고, 근거 없는 추가와 명시된 사실의 모순, 시간/확실성 범위 확장, 자동 인과 추론을 찾는다. 명백하지 않으면 uncertain으로 보존하고 단순한 자연스러운 바꿔 말하기는 오류로 세지 않는다.\n이력에 환자 자신이 덧붙인 말이 있다는 것만으로 새 고정 사실의 근거가 되지는 않는다. 반대로 설정에 허용된 주관적 경험·믿음은 외부 현실과 다르다는 이유로 오류로 판정하지 않는다. 설정된 의학용어와 환자 지식 범위를 존중한다. 추가 세부를 아예 말하지 않는 응답도 회피·질문 미대응이 있는지 기존 Realism에서 함께 평가한다.\n근거 문제가 없으면 status=no_issue_identified, findings=[]로 둔다. 문제 후보가 있으면 concern 또는 uncertain과 실제 환자 인용을 포함한다. fact_ids는 해당 프로필의 사실 ID만 쓰며, 직접 대응 사실이 없으면 빈 배열로 둘 수 있다. status는 전체 대화에 대한 관찰이지 진단이나 전문가 판정이 아니다.\n총 18개 review를 모두 한 번씩 평정한다. reason은 1~2문장, issues는 중요한 0~2개로 제한하고 grounding findings는 확인한 문제 후보를 빠뜨리지 말되 간결하게 쓴다. 문제를 억지로 찾거나 다른 대화와 상대평가하지 않는다. 버전·변경 목적을 추측하지 않고 다른 대화 ID를 설명에서 참조하지 않는다. 프롬프트 수정은 실행하지 않으며 module_suggestions는 빈 배열로 둘 수 있다.\n'
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
        case=cases[r['blind_id']]
        turns={t['turn_id']:t['text'] for t in case['generated_dialogue'] if t['speaker']=='patient'}
        ids={f['id'] for f in packet['profiles'][case['profile_ref']]['patient_setting']['facts']}
        g=r.get('grounding_review')
        if not isinstance(g,dict) or g.get('status') not in {'no_issue_identified','concern','uncertain'}:
            raise ValueError('Grounding status missing or invalid')
        if g.get('checked_turn_ids')!=['P01','P02','P03','P04']:
            raise ValueError('All four patient turns must be checked')
        findings=g.get('findings')
        if not isinstance(findings,list): raise ValueError('Grounding findings must be a list')
        if (g['status']=='no_issue_identified') != (len(findings)==0):
            raise ValueError('Grounding status and findings inconsistent')
        for f in findings:
            if f.get('patient_turn_id') not in turns or not f.get('quote') or f['quote'] not in turns[f['patient_turn_id']]:
                raise ValueError('Grounding evidence not in actual patient turn')
            if f.get('kind') not in GROUNDING_KINDS or not f.get('explanation'):
                raise ValueError('Grounding finding kind/explanation invalid')
            if not isinstance(f.get('fact_ids'),list) or not set(f['fact_ids']).issubset(ids):
                raise ValueError('Grounding fact references invalid')
    return rows


def review(provider):
    verify(); frozen=read(HERE/'review-freeze.json')
    assert digest(HERE/'review-packet.json')==frozen['packet_sha256']
    assert digest(HERE/'review-role.txt')==frozen['role_sha256']
    out=call_once(provider,(HERE/'review-packet.json').read_text(),(HERE/'review-role.txt').read_text(),HERE/'reviews'/provider)
    parsed=M1.parse_review(out['text']); validate_review(parsed,read(HERE/'review-packet.json'))
    dump(HERE/'reviews'/provider/'validated.json',parsed)
    print(provider+': 18 scores and grounding audit quotes validated; one review call',flush=True)


def description(values):
    if len(values)!=3: raise ValueError('Exactly three generated dialogues required')
    return {'values':values,'mean':statistics.mean(values),'min':min(values),'max':max(values),
            'range':max(values)-min(values),'sample_sd':statistics.stdev(values)}


def analyze(items,reviews):
    if set(reviews)!=set(PROVIDERS): raise ValueError('Both reviewers required')
    rows=[]
    for item in sorted(items,key=lambda t:t['item_id']):
        ident=item['item_id'];scores={p:reviews[p][ident]['score'] for p in PROVIDERS}
        answers=[t['text'] for t in item['generated_dialogue'] if t['speaker']=='patient']
        rows.append({k:item[k] for k in ('item_id','case_id','condition','replicate')} | {
            'scores':scores,'mean':statistics.mean(scores.values()),'patient_characters':sum(map(len,answers)),
            'exact_patient_sequence_sha256':hashlib.sha256(canonical(answers)).hexdigest(),
            'grounding':{p:reviews[p][ident]['grounding_review'] for p in PROVIDERS}})
    groups=[]
    for case in sorted({r['case_id'] for r in rows}):
        data={}
        for version in VERSIONS:
            selected=[r for r in rows if r['case_id']==case and r['condition']==version]
            if len(selected)!=3 or {r['replicate'] for r in selected}!={1,2,3}: raise ValueError('Incomplete generation group')
            data[version]={'combined_scores':description([r['mean'] for r in selected]),
                'judges':{p:description([r['scores'][p] for r in selected]) for p in PROVIDERS},
                'unique_exact_patient_sequences':len({r['exact_patient_sequence_sha256'] for r in selected}),
                'patient_characters':description([r['patient_characters'] for r in selected]),
                'grounding_status_counts':{p:dict(Counter(r['grounding'][p]['status'] for r in selected)) for p in PROVIDERS}}
        groups.append({'case_id':case,**data,'v05_minus_v02':data['v05']['combined_scores']['mean']-data['v02']['combined_scores']['mean']})
    means={v:statistics.mean(g[v]['combined_scores']['mean'] for g in groups) for v in VERSIONS}
    judge_means={p:{v:statistics.mean(g[v]['judges'][p]['mean'] for g in groups) for v in VERSIONS} for p in PROVIDERS}
    grounding={p:{v:{'dialogues':9,'status_counts':dict(Counter(r['grounding'][p]['status'] for r in rows if r['condition']==v)),
        'finding_count':sum(len(r['grounding'][p]['findings']) for r in rows if r['condition']==v),
        'finding_kind_counts':dict(Counter(f['kind'] for r in rows if r['condition']==v for f in r['grounding'][p]['findings']))}
        for v in VERSIONS} for p in PROVIDERS}
    return {'kind':'descriptive_fresh_v02_v05_fact_grounding_comparison_not_clinical_validation','dialogues':18,'ratings':36,
        'items':rows,'cases':groups,'condition_means':means,'v05_minus_v02':means['v05']-means['v02'],
        'judge_condition_means':judge_means,'grounding_summary':grounding,
        'score_frequencies':{p:{str(k):n for k,n in Counter(r['scores'][p] for r in rows).items()} for p in PROVIDERS},
        'independent_case_clusters':3,
        'limits':'Same three reused profiles; single judge rating per generated dialogue. Model grounding concerns are not clinical gold standard. Zero observed baseline issues prevents claiming reduced error rate. No old-score pooling, p-values or general superiority claim.'}


def aggregate():
    verify(); packet=read(HERE/'review-packet.json'); key=read(HERE/'review-key-private.json')
    items=[read(ROOT/m['transcript_path']) for m in key.values()]
    reviews={p:{key[r['blind_id']]['item_id']:r for r in validate_review(read(HERE/'reviews'/p/'validated.json'),packet)} for p in PROVIDERS}
    result=analyze(items,reviews);dump(HERE/'scores.json',result)
    print(json.dumps({k:result[k] for k in ('condition_means','v05_minus_v02','judge_condition_means','grounding_summary','score_frequencies')},ensure_ascii=False,indent=2))


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
