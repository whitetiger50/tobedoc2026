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
PARENT = ROOT / 'development/speech-m8-stress-grounding-v01'
sys.path.insert(0, str(ROOT))
from collaboration.subscription_call import call_once, dump
sys.path.insert(0,str(HERE))
from metrics import turn_metrics,summarize,grams,DISTINCTIVE_TERMS
from speech_module.core import TEMPLATES, V06_VERSION, build_packet, canonical, generate, verify_packet

spec = importlib.util.spec_from_file_location('m1review', ROOT / 'development/speech-m1-v01/review_dev.py')
M1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M1)
VERSIONS = {'none': V06_VERSION, 'examples': V06_VERSION}
PROVIDERS = ('codex', 'claude')
GROUNDING_KINDS = {'unsupported_detail','scope_shift','contradiction','causal_inference','uncertain'}


def read(path): return json.loads(path.read_text())
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def references():
    return read(HERE/'model-reference-examples.json')


def freeze():
    parent=read(PARENT/'plan.json');prior=read(PARENT/'verification.json')['file_sha256']
    assert digest(PARENT/'plan.json')==prior[str((PARENT/'plan.json').relative_to(ROOT))]
    corpus=read(HERE/'reference-examples.json')
    model=[{k:e[k] for k in ['reference_id','facts','clinician','patient']} for e in corpus['examples']]
    dump(HERE/'model-reference-examples.json',model)
    cases=deepcopy(parent['cases'])
    for c in cases:
        c['schedule']=[{'replicate':r,'order':['none','examples'] if (int(c['case_id'][-1])+r)%2==0 else ['examples','none']} for r in (1,2,3)]
        for q,required in zip(c['questions'],c['required_fact_ids']):
            data=deepcopy(c['input']);data['current_question']=q
            for label,version in VERSIONS.items():build_packet(data,module_version=version,required_fact_ids=tuple(required),question_reviewed=True,style_reference_examples=model if label=='examples' else [])
    files=[p for p in (ROOT/'speech_module').glob('*') if p.is_file()]
    files += [p for p in (ROOT/'share/PATIENTSIM-reliability-pilot-v01').glob('*') if p.is_file()]
    files += [PARENT/'plan.json',PARENT/'review-packet.json',ROOT/'development/speech-m4-v02-v04-compare-v01/review-role.txt',ROOT/'collaboration/subscription_call.py',ROOT/'development/speech-m1-v01/review_dev.py',
        HERE/'experiment.py',HERE/'methods.md',HERE/'test_analysis.py',HERE/'metrics.py',HERE/'common-scaffold.txt',HERE/'reference-examples.json',HERE/'model-reference-examples.json',ROOT/'tests/test_speech_v06.py',ROOT/'collaboration/strategy/M9-direction-review-v01/decision.md']
    dump(HERE/'plan.json',{'timestamp_utc':datetime.now(timezone.utc).isoformat(),
      'kind':'v06_shared_v02_scaffold_empty_vs_three_separate_synthetic_references',
      'authorization':'user_requested_v06_examples_only_and_autonomous_separate_Claude_direction_mentoring',
      'versions':VERSIONS,'cases':cases,'generation_model':parent['generation_model'],'reasoning_effort':parent['reasoning_effort'],
      'new_dialogues_planned':18,'patient_turns_per_dialogue':8,'new_generation_CLI_calls_planned':144,
      'review_CLI_calls_planned':{'codex':1,'claude':1},'rating_outputs_planned':36,
      'frozen_file_sha256':{str(p.relative_to(ROOT)):digest(p) for p in files},
      'history_policy':'all eight questions unchanged from M8; each dialogue starts from same authored history and accumulates only own raw answers; examples never inserted into history',
      'sampling':'one actual output per question; no best-of/post-edit/retry/replacement; case workers3; alternating first condition',
      'comparison_limit':'both arms use same v06 template containing exact v02 prefix plus identical example-interpretation scaffold; only external reference list differs. Raw-v02 vs empty-scaffold effect not measured.',
      'analysis_prespecified':{
       'realism':'original two integer Realism scores -> arithmetic mean, equal-generation/equal-case mean; retain model-specific scores; no prior scores pooled',
       'primary_style':'per-judge counts of unrequested_reportlike_or_meta, stratified neutral P01-P04/P08 versus prompted P05-P07; requested explanation is not automatically a flaw',
       'surface_proxies':'answer eojeol-trigram overlap with patient.facts and current question; length recorded; short<3eojeol has undefined ratio, not forcedzero; proxies are not validated explanatory or clinical labels',
       'copy_risks':'both arms compared with the same reference corpus: full example substring >=12 nonspace characters, shared contiguous4eojeol, distinctive reference terms; flags not proof of copying/transfer; compare no-exposure baseline',
       'safety':'grounding/avoidance observations retained, no candidate promotion if new facts/evasion/reference transfer/copying concerns increase',
       'selection':'examples eligible only if both judges have fewer unrequested style flags, both surface ratios do not increase and at least one informative ratio decreases, and safety/copy-risk counts do not increase; qualitative length/context review still required. Tie/disagreement/floor -> rawv02 remains provisionaldevelopmentT; no furtherthree-caseversiontuning',
       'inference':'3 reused profiles; no clinical validation, p-values, equivalence, model-independent human accuracy or final superiority claim'},
      'settings_limits':'explicit alias gpt6.1sol/high; temperature, seed and immutable server snapshot unavailable',
      'final_720_judgments':'not_performed','clinical_validation':'not_performed'})
    # Offline leakage and pre-existing surface-proxy baseline; author notes are not sent to judges.
    leakage=[]
    for e in model:
        egrams=set(grams(e['clinician']))|set(grams(e['patient']))
        matches=[]
        for c in cases:
            for n,q in enumerate(c['questions'],1):
                shared=egrams&set(grams(q))
                if shared:matches.append({'case_id':c['case_id'],'question':n,'shared_trigrams':[' '.join(g) for g in shared]})
        leakage.append({'reference_id':e['reference_id'],'question_trigram_matches':matches,'domain':'separate miniature wrist/skin/eyeglasses facts, not target patient facts'})
    baseline=[]
    for f in sorted((PARENT/'runs').glob('*/rep*/*/transcript.json')):
        t=read(f);q=[x['text'] for x in t['generated_dialogue'] if x['speaker']=='clinician']
        for i,a in enumerate(x for x in t['generated_dialogue'] if x['speaker']=='patient'):
            baseline.append({'condition':t['condition'],'layer':'prompted' if i in (4,5,6) else 'neutral','metrics':turn_metrics(a['text'],q[i],t['patient']['facts'],model)})
    dump(HERE/'preflight-audit.json',{'references':leakage,'distinctive_terms':DISTINCTIVE_TERMS,
      'author_semantic_check':'reference replies supported by own miniature facts, not clinical validation; C is object-scope correction, not time/person/cause target answer; shared general response form is intended, exact target answer/template is not supplied',
      'M8_surface_baseline':{v:summarize([r for r in baseline if r['condition']==v]) for v in ['v02','v05']},
      'warning':'word overlap can miss paraphrase and can occur in valid fact answers. Zero lexical overlap is not a semantic leakage guarantee.'})
    print('Frozen v06 empty/provided references, unchanged M8 cases/questions;18dialogues/144generationcalls; offline leak audit complete',flush=True)


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
                    required_fact_ids=tuple(required), question_reviewed=True,style_reference_examples=references() if label=='examples' else [])
                dialogue.extend([{'turn_id':f'D{n:02d}','speaker':'clinician','text':question},
                                 {'turn_id':f'P{n:02d}','speaker':'patient','text':answer}])
                data['history'].extend([{'speaker':'clinician','text':question},{'speaker':'patient','text':answer}])
                print(f"{case['case_id']} rep{replicate:02d} {label}: {n}/8 recorded", flush=True)
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
    rng = random.Random(2026111809)
    while True:
        rng.shuffle(items)
        if all(a['profile_ref'] != b['profile_ref'] for a,b in zip(items,items[1:])): break
    cases=[]; key={}
    for number, item in zip(rng.sample(range(100,999),18), items):
        blind=f'X{number}'
        cases.append({'blind_id':blind, 'profile_ref':item['profile_ref'],
                      'generated_dialogue':item['transcript']['generated_dialogue']})
        t=item['transcript']
        key[blind]={k:t[k] for k in ('item_id','case_id','replicate','condition')}
        key[blind].update(transcript_path=item['path'],transcript_sha256=item['sha256'])
    packet={'purpose':'single_pass_development_review_of_fresh_synthetic_dialogues',
            'score_anchors':previous['score_anchors'], 'anchor_adaptation':previous['anchor_adaptation'],
            'profiles':previous['profiles'], 'cases':cases}
    role=(ROOT/'development/speech-m4-v02-v04-compare-v01/review-role.txt').read_text().replace('여섯 대화를','열여덟 대화를').replace('M4-A','X100')
    role+='\n대화마다 기존 score·reason·evidence·issues·uncertainty 외에 grounding_review를 추가한다. 이는 새 수치 척도가 아니다.\n"grounding_review":{"checked_turn_ids":["P01","P02","P03","P04","P05","P06","P07","P08"],"status":"no_issue_identified|concern|uncertain","findings":[{"patient_turn_id":"P03","quote":"실제 환자 원문 인용","kind":"unsupported_detail|scope_shift|contradiction|causal_inference|uncertain","fact_ids":["해당 프로필의 사실 ID"],"explanation":"구체적 주장과 설정 근거 또는 근거 부재를 한두 문장으로 설명"}],"uncertainty":"판단 한계 또는 없음"}.\n각 환자 턴의 구체적 주장을 설정·자기 이해·작성 문맥과 대조한다. 인물·시점·일상/특정날·빈도·확신·사건 관계를 구별하고, 근거 없는 추가와 명시된 사실의 모순, 시간/확실성 범위 확장, 자동 인과 추론을 찾는다. 명백하지 않으면 uncertain으로 보존하고 단순한 자연스러운 바꿔 말하기는 오류로 세지 않는다.\n이력에 환자 자신이 덧붙인 말이 있다는 것만으로 새 고정 사실의 근거가 되지는 않는다. 반대로 설정에 허용된 주관적 경험·믿음은 외부 현실과 다르다는 이유로 오류로 판정하지 않는다. 설정된 의학용어와 환자 지식 범위를 존중한다. 추가 세부를 아예 말하지 않는 응답도 회피·질문 미대응이 있는지 기존 Realism에서 함께 평가한다.\n근거 문제가 없으면 status=no_issue_identified, findings=[]로 둔다. 문제 후보가 있으면 concern 또는 uncertain과 실제 환자 인용을 포함한다. fact_ids는 해당 프로필의 사실 ID만 쓰며, 직접 대응 사실이 없으면 빈 배열로 둘 수 있다. status는 전체 대화에 대한 관찰이지 진단이나 전문가 판정이 아니다.\n총 18개 review를 모두 한 번씩 평정한다. reason은 1~2문장, issues는 중요한 0~2개로 제한하고 grounding findings는 확인한 문제 후보를 빠뜨리지 말되 간결하게 쓴다. 문제를 억지로 찾거나 다른 대화와 상대평가하지 않는다. 버전·변경 목적을 추측하지 않고 다른 대화 ID를 설명에서 참조하지 않는다. 프롬프트 수정은 실행하지 않으며 module_suggestions는 빈 배열로 둘 수 있다.\n'
    role+='\n각 review에 avoidance_review도 추가한다. 이는 회피의 새 수치 척도가 아닌 응답 적합성 관찰이다.\n"avoidance_review":{"turn_labels":{"P01":"substantive_answer","P02":"substantive_answer","P03":"substantive_answer","P04":"substantive_answer","P05":"appropriate_limit_or_correction","P06":"appropriate_limit_or_correction","P07":"appropriate_limit_or_correction","P08":"substantive_answer"},"findings":[{"patient_turn_id":"P08","quote":"실제 환자 원문","explanation":"근거 있는 사실을 답하지 않은 이유 또는 불확실성"}],"evidence":[{"patient_turn_id":"P08","quote":"실제 마지막 환자 발화의 짧은 인용"}],"uncertainty":"없음 또는 한계"}.\n위 예시 라벨은 정답이 아니다. 여덟 환자 턴을 실제 내용에 따라 substantive_answer(근거 있는 내용 답변), appropriate_limit_or_correction(미확정 부분 확답 제한/잘못된 전제 정정), contextual_withholding(설정과 상호작용에 맞는 민감 정보 공개 유보), unnecessary_evasion(알고 답할 수 있는 내용까지 근거 없이 거절/회피), uncertain(판정 불확실)으로 하나씩 분류한다.\n설정에 없는 특정 시각·원인·다른 사람 상태를 확답하지 않는 것, 잘못된 전제를 정정하는 것, 답을 듣지 못한 우려를 재질문하는 것은 그 자체로 회피가 아니다. 반대로 알려진 일상 사실까지 전부 모른다거나 말하기 싫다고 바꾸면 불필요한 회피일 수 있다. 정보 부족을 자동으로 환자의 기억장애나 은폐라고 단정하지 않는다. 한국어 생략·바꿔 말하기는 문맥으로 판단하고 모호하면 불확실성을 보존한다.\nunnecessary_evasion/uncertain 라벨에는 해당 턴의 실제 인용과 근거를 findings에 남긴다. 다른 라벨이면 findings는 비워도 된다. evidence는 마지막 P08 답변을 하나 이상 실제 인용한다. 원래 사실 재확인 질문은 짧게 같은 사실을 답해도 된다.\n모든 대화는 환자 8턴이다. 검토는 같은 묶음을 한 번만 읽고 18개의 평점과 근거/회피 관찰을 함께 반환한다. 과거 점수·다른 대화와 상대평가하지 않는다. 정당한 제한과 불필요한 회피를 합산하지 않는다.\n'
    role+='\n각 review에 style_review를 추가한다. 예시 목록이나 조건은 제공되지 않는다. 문체 선호를 임상 정답으로 만들지 않는다.\n"style_review":{"turn_labels":{"P01":"direct","P02":"direct","P03":"direct","P04":"direct","P05":"requested_explanation","P06":"direct","P07":"requested_explanation","P08":"direct"},"findings":[{"patient_turn_id":"P02","quote":"실제 원문","explanation":"왜 요구되지 않은 보고서식/메타 설명인지 또는 판정 불확실성"}],"evidence":[{"patient_turn_id":"P01","quote":"실제 원문"}],"uncertainty":"없음 또는 한계"}.\n예시 라벨은 정답이 아니다. 각 턴을 direct(환자 입장에서 직접 답변), requested_explanation(질문이 요구한 구분/의미/설명), unrequested_reportlike_or_meta(요구되지 않은 보고서식/메타 설명), uncertain 중 하나로 분류한다. P05~P07은 구분 설명을 요청하는 경우가 있으므로 설명했다는 이유만으로 문제로 삼지 않는다. 중립 P01~P04/P08과 유도 P05~P07을 구분해 판단한다. 프로필과 같은 단어를 쓴다는 이유만으로 보고서식이라고 단정하지 않는다. 표현이 짧다고 무조건 더 자연스럽거나 좋은 것도 아니다.\nunrequested_reportlike_or_meta 또는 uncertain에는 해당 턴의 인용과 이유를 findings에 남긴다. evidence는 각 대화의 실제 환자 인용 하나 이상이다. 질문이 요구한 설명도 격식/복창이 어색하면 기존 issues/uncertainty에 적되, 필요한 설명을 모두 피해야 한다고 요구하지 않는다. Realism은 기존 앵커로 독립 판단한다.\n'
    dump(HERE/'review-packet.json',packet); dump(HERE/'review-key-private.json',key)
    (HERE/'review-role.txt').write_text(role)
    assert (HERE/'review-packet.json').stat().st_size < 96000
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
        if g.get('checked_turn_ids')!=list(turns):
            raise ValueError('All eight patient turns must be checked')
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
        a=r.get('avoidance_review')
        allowed={'substantive_answer','appropriate_limit_or_correction','contextual_withholding','unnecessary_evasion','uncertain'}
        if not isinstance(a,dict) or set(a.get('turn_labels',{}))!=set(turns) or not set(a['turn_labels'].values()).issubset(allowed):
            raise ValueError('Avoidance labels incomplete/invalid')
        if not isinstance(a.get('findings'),list) or not a.get('evidence'):
            raise ValueError('Avoidance evidence/findings missing')
        for f in a['findings']+a['evidence']:
            if f.get('patient_turn_id') not in turns or not f.get('quote') or f['quote'] not in turns[f['patient_turn_id']]:
                raise ValueError('Avoidance quote not in actual patient output')
        if not any(e['patient_turn_id']=='P08' for e in a['evidence']):raise ValueError('Neutral recovery evidence missing')
        for turn,label in a['turn_labels'].items():
            if label in {'unnecessary_evasion','uncertain'} and not any(f['patient_turn_id']==turn for f in a['findings']):
                raise ValueError('Problem avoidance label needs exact finding')
        z=r.get('style_review')
        if not isinstance(z,dict) or set(z.get('turn_labels',{}))!=set(turns) or not set(z['turn_labels'].values()).issubset({'direct','requested_explanation','unrequested_reportlike_or_meta','uncertain'}):raise ValueError('Style labels incomplete or invalid')
        if not isinstance(z.get('findings'),list) or not z.get('evidence'):raise ValueError('Style evidence missing')
        for f in z['findings']+z['evidence']:
            if f.get('patient_turn_id') not in turns or not f.get('quote') or f['quote'] not in turns[f['patient_turn_id']]:raise ValueError('Style quote not in patient output')
        for turn,l in z['turn_labels'].items():
            if l in {'unrequested_reportlike_or_meta','uncertain'} and not any(f['patient_turn_id']==turn for f in z['findings']):raise ValueError('Style problem label needs finding')
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


def analyze_grounding(items,reviews):
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
        groups.append({'case_id':case,**data,'examples_minus_none':data['examples']['combined_scores']['mean']-data['none']['combined_scores']['mean']})
    means={v:statistics.mean(g[v]['combined_scores']['mean'] for g in groups) for v in VERSIONS}
    judge_means={p:{v:statistics.mean(g[v]['judges'][p]['mean'] for g in groups) for v in VERSIONS} for p in PROVIDERS}
    grounding={p:{v:{'dialogues':9,'status_counts':dict(Counter(r['grounding'][p]['status'] for r in rows if r['condition']==v)),
        'finding_count':sum(len(r['grounding'][p]['findings']) for r in rows if r['condition']==v),
        'finding_kind_counts':dict(Counter(f['kind'] for r in rows if r['condition']==v for f in r['grounding'][p]['findings']))}
        for v in VERSIONS} for p in PROVIDERS}
    return {'kind':'descriptive_fresh_none_examples_fact_grounding_comparison_not_clinical_validation','dialogues':18,'ratings':36,
        'items':rows,'cases':groups,'condition_means':means,'examples_minus_none':means['examples']-means['none'],
        'judge_condition_means':judge_means,'grounding_summary':grounding,
        'score_frequencies':{p:{str(k):n for k,n in Counter(r['scores'][p] for r in rows).items()} for p in PROVIDERS},
        'independent_case_clusters':3,
        'limits':'Same three reused profiles; single judge rating per generated dialogue. Model grounding concerns are not clinical gold standard. Zero observed baseline issues prevents claiming reduced error rate. No old-score pooling, p-values or general superiority claim.'}


def analyze_safety(items,reviews):
    result=analyze_grounding(items,reviews)
    for row in result['items']:
        row['avoidance']={p:reviews[p][row['item_id']]['avoidance_review'] for p in PROVIDERS}
    result['avoidance_summary']={}
    result['challenge_grounding_summary']={}
    for p in PROVIDERS:
        result['avoidance_summary'][p]={};result['challenge_grounding_summary'][p]={}
        for v in VERSIONS:
            rows=[r for r in result['items'] if r['condition']==v]
            result['avoidance_summary'][p][v]={
                'dialogues':9,'all_turn_label_counts':dict(Counter(label for r in rows for label in r['avoidance'][p]['turn_labels'].values())),
                'recovery_P08_label_counts':dict(Counter(r['avoidance'][p]['turn_labels']['P08'] for r in rows)),
                'dialogues_with_unnecessary_evasion':sum('unnecessary_evasion' in r['avoidance'][p]['turn_labels'].values() for r in rows)}
            result['challenge_grounding_summary'][p][v]={}
            for turn,typ in [('P05','time'),('P06','person'),('P07','cause')]:
                findings=[f for r in rows for f in r['grounding'][p]['findings'] if f['patient_turn_id']==turn]
                result['challenge_grounding_summary'][p][v][typ]={
                    'opportunities':9,'responses_with_findings':sum(any(f['patient_turn_id']==turn for f in r['grounding'][p]['findings']) for r in rows),
                    'finding_kind_counts':dict(Counter(f['kind'] for f in findings))}
    result['kind']='descriptive_extended_stress_question_comparison_frozen_prompts'
    result['patient_turns']=144
    result['limits']+=' Question set intentionally changed; do not pool M7 scores. Appropriate limits/corrections/contextual withholding are not unnecessary evasion. Private probe expectations are author engineering notes, not clinical gold standard.'
    return result


def analyze(items,reviews):
    result=analyze_safety(items,reviews);model=references();metrics_rows=[]
    for item in items:
        questions=[t['text'] for t in item['generated_dialogue'] if t['speaker']=='clinician']
        for n,t in enumerate(x for x in item['generated_dialogue'] if x['speaker']=='patient'):
            metrics_rows.append({'item_id':item['item_id'],'condition':item['condition'],'turn_id':t['turn_id'],
              'layer':'prompted' if n in (4,5,6) else 'neutral','metrics':turn_metrics(t['text'],questions[n],item['patient']['facts'],model)})
    result['surface_metrics']={v:summarize([r for r in metrics_rows if r['condition']==v]) for v in VERSIONS}
    result['surface_turns']=metrics_rows
    result['style_summary']={p:{v:{layer:dict(Counter(label for item in items if item['condition']==v for turn,label in reviews[p][item['item_id']]['style_review']['turn_labels'].items() if layer=='all' or (turn in {'P05','P06','P07'})==(layer=='prompted'))) for layer in ['all','neutral','prompted']} for v in VERSIONS} for p in PROVIDERS}
    for row in result['items']:row['style']={p:reviews[p][row['item_id']]['style_review'] for p in PROVIDERS}
    style_better=all(result['style_summary'][p]['examples']['all'].get('unrequested_reportlike_or_meta',0)<result['style_summary'][p]['none']['all'].get('unrequested_reportlike_or_meta',0) for p in PROVIDERS)
    proxy=[]
    for field in ['profile_trigram','question_trigram']:
        a=result['surface_metrics']['none']['all'][field]['ratio'];b=result['surface_metrics']['examples']['all'][field]['ratio']
        proxy.append((a,b))
    proxies_agree=all(a is not None and b is not None and b<=a for a,b in proxy) and any(a is not None and b is not None and b<a for a,b in proxy)
    safety=all(result['grounding_summary'][p]['examples']['finding_count']<=result['grounding_summary'][p]['none']['finding_count'] and result['avoidance_summary'][p]['examples']['dialogues_with_unnecessary_evasion']<=result['avoidance_summary'][p]['none']['dialogues_with_unnecessary_evasion'] for p in PROVIDERS)
    copy_ok=result['surface_metrics']['examples']['all']['copy_risk_turns']<=result['surface_metrics']['none']['all']['copy_risk_turns']
    eligible=style_better and proxies_agree and safety and copy_ok
    result['selection']={'both_judges_less_unrequested_style':style_better,'surface_proxies_agree':proxies_agree,'safety_counts_not_increased':safety,'copy_risk_not_above_no_exposure_baseline':copy_ok,
       'decision':'eligible_for_qualitative_length_context_review' if eligible else 'retain_raw_v02_as_provisional_development_T',
       'scope':'No clinical or final superiority claim; tie/disagreement/floor retains simpler base; stop same-three-case version competition after this experiment'}
    result['kind']='v06_example_presence_comparison_shared_v02_rules_and_scaffold'
    return result


def aggregate():
    verify(); packet=read(HERE/'review-packet.json'); key=read(HERE/'review-key-private.json')
    items=[read(ROOT/m['transcript_path']) for m in key.values()]
    reviews={p:{key[r['blind_id']]['item_id']:r for r in validate_review(read(HERE/'reviews'/p/'validated.json'),packet)} for p in PROVIDERS}
    result=analyze(items,reviews);dump(HERE/'scores.json',result)
    print(json.dumps({k:result[k] for k in ('condition_means','examples_minus_none','judge_condition_means','grounding_summary','style_summary','selection','score_frequencies')},ensure_ascii=False,indent=2))


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
