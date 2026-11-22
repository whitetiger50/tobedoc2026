"""Matched v02/v03 development comparison using official subscription CLIs only."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT))
from collaboration.subscription_call import call_once, dump
from speech_module.core import TEMPLATES, V02_VERSION, VERSION, build_packet, canonical, generate, verify_packet

SPEC=importlib.util.spec_from_file_location('m1review',ROOT/'development/speech-m1-v01/review_dev.py')
M1=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M1)
VERSIONS={'v02':V02_VERSION,'v03':VERSION}


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze():
    original=json.loads((ROOT/'development/speech-m1-v01/generation-plan.json').read_text())
    prior=json.loads((ROOT/'development/speech-m1-v01/followup-plan-v02.json').read_text())
    additions={t['case_id']:t['new_author_defined_synthetic_facts'] for t in prior['targets']}
    requirements={
        'DEV-M0-01':[['breakfast'],['voice'],['medication_knowledge'],['living']],
        'DEV-M0-02':[['sleep','sleep_voice_relation'],['living'],['voice','belief'],['visit']],
        'DEV-M0-03':[['belief','experience'],['routine'],['today_activity'],['living']]}
    cases=[]
    for index,c in enumerate(original['cases']):
        data=deepcopy(c['input']);extra=deepcopy(additions[c['case_id']])
        if c['case_id']=='DEV-M0-01':
            extra.append({'id':'medication_knowledge','kind':'treatment','patient_knows':True,'disclosure':'on_topic',
                          'content':'현재 복용하는 약의 이름과 용량을 본인은 정확히 알지 못한다. 특정 약 이름이나 용량은 정하지 않았다.'})
        data['patient']['facts'].extend(extra)
        assert 'speech_examples' not in data
        for q,required in zip(c['questions'],requirements[c['case_id']]):
            check=deepcopy(data);check['current_question']=q
            for version in VERSIONS.values():
                build_packet(check,module_version=version,required_fact_ids=tuple(required),question_reviewed=True)
        cases.append({'case_id':c['case_id'],'input':data,'questions':c['questions'],
            'required_fact_ids':requirements[c['case_id']],'shared_synthetic_additions':extra,
            'generation_order':['v02','v03'] if index%2==0 else ['v03','v02']})
    files={str(p.relative_to(ROOT)):digest(p) for p in [TEMPLATES[V02_VERSION],TEMPLATES[VERSION],
           ROOT/'speech_module/patient_v03.sources.json',ROOT/'speech_module/core.py',ROOT/'collaboration/subscription_call.py']}
    plan={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'kind':'matched_development_not_final_confirmation',
       'versions':VERSIONS,'cases':cases,'frozen_file_sha256':files,'generation_model':'gpt-6.1-sol','reasoning_effort':'high',
       'examples':False,'sampling':'one_output_per_question_per_version_no_retries_or_best_of',
       'history_policy':'identical_authored_start_then_each_condition_own_actual_generated_history',
       'calls_planned':24,'review_calls_planned':{'codex':1,'claude':1},'ratings_planned':12,
       'aggregation':'two original integer Realism scores -> arithmetic mean per conversation; v03-minus-v02 within each case; equal-case mean per version; reviewer-specific deltas also retained',
       'interpretation':'descriptive paired development signal only; no inferential test or final superiority claim; qualitative new failures assessed alongside score direction',
       'input_completion_note':'same three case identities and original questions; two previously authored followup additions reused; one new explicit medication-knowledge fact shared by both conditions before any outputs; not compared with historical M1 scores',
       'generation_judge_dependence':'GPT judge uses same model as generator; masked source is not independent clinical validation',
       'no_new_training_or_paid_API':True}
    dump(HERE/'plan.json',plan)
    for label,version in VERSIONS.items():(HERE/f'prompt-{label}.txt').write_bytes(TEMPLATES[version].read_bytes())
    print('Frozen 3 matched cases, 12 questions per version, no examples; no inference yet',flush=True)


def read_plan():
    plan=json.loads((HERE/'plan.json').read_text())
    for p,h in plan['frozen_file_sha256'].items():
        if digest(ROOT/p)!=h:raise ValueError('Frozen implementation changed: '+p)
    return plan


def run_pair(case):
    ident=case['case_id']
    for label in case['generation_order']:
        transcript_path=HERE/'runs'/ident/label/'transcript.json'
        if transcript_path.exists():raise FileExistsError('Completed pair must not be regenerated')
        data=deepcopy(case['input']);dialogue=[]
        for turn,(question,required) in enumerate(zip(case['questions'],case['required_fact_ids']),1):
            read_plan()
            data['current_question']=question
            directory=HERE/'runs'/ident/label/f'turn{turn:02d}'
            def backend(messages):
                return call_once('codex',messages[1]['content'],messages[0]['content'],directory/'transport')
            answer=generate(data,backend,directory,module_version=VERSIONS[label],required_fact_ids=tuple(required),question_reviewed=True)
            dialogue.extend([{'turn_id':f'D{turn:02d}','speaker':'clinician','text':question},
                             {'turn_id':f'P{turn:02d}','speaker':'patient','text':answer}])
            data['history'].extend([{'speaker':'clinician','text':question},{'speaker':'patient','text':answer}])
            print(f'{ident} {label}: {turn}/4 recorded',flush=True)
        dump(transcript_path,{'case_id':ident,'condition':label,'module_version':VERSIONS[label],
            'patient':case['input']['patient'],'communication':case['input']['communication'],
            'authored_context':case['input']['history'],'generated_dialogue':dialogue,'partition':'development'})
    return ident


def make_review():
    plan=read_plan()
    rubric_path=ROOT/'development/speech-m1-v01/sources/llm_eval_metrics_persona.json'
    assert digest(rubric_path)=='ef29b12666d8241b6559db144e8004b91dab21d1ede6d5c306e27a7a5086e995'
    rubric=json.loads(rubric_path.read_text())['Realism_w_Profile']
    anchors={k:v.replace('an ED patient','a psychiatric patient').replace('ED patient','psychiatric patient') for k,v in rubric.items()}
    profiles={};items=[]
    for index,c in enumerate(plan['cases'],1):
        profile_id=f'PROFILE-{index}'
        p=c['input']['patient']
        profiles[profile_id]={'patient_setting':{'facts':p['facts'],'self_understanding':p['self_understanding']},
                             'communication':c['input']['communication'],'authored_context':c['input']['history']}
        for label in ['v02','v03']:
            path=HERE/'runs'/c['case_id']/label/'transcript.json'
            t=json.loads(path.read_text())
            items.append((profile_id,c['case_id'],label,t['generated_dialogue'],digest(path)))
    random.Random(20261118).shuffle(items)
    cases=[];key={}
    for letter,item in zip('ABCDEF',items):
        profile,ident,label,dialogue,h=item;blind='M3-'+letter
        cases.append({'blind_id':blind,'profile_ref':profile,'generated_dialogue':dialogue})
        key[blind]={'case_id':ident,'condition':label,'transcript_sha256':h}
    packet={'purpose':'single_pass_development_realism_review','score_anchors':anchors,
       'anchor_adaptation':'ED patient -> psychiatric patient only; not schizophrenia-validated',
       'profiles':profiles,'cases':cases}
    role=M1.ROLE.replace('세 대화를','여섯 대화를').replace('M1-A','M3-A')
    role+='\n각 대화의 profile_ref로 profiles의 환자 설정·의사소통·작성 문맥을 참조한다. 여섯 대화를 모두 각각 한 번 평정한다. 조건·출처를 추측하거나 우열을 정하려 하지 말고, 같은 앵커로 대화마다 독립 평정한다.\n'
    dump(HERE/'review-packet.json',packet);dump(HERE/'review-key-private.json',key)
    (HERE/'review-role.txt').write_text(role)
    dump(HERE/'review-freeze.json',{'timestamp_utc':datetime.now(timezone.utc).isoformat(),
         'packet_sha256':digest(HERE/'review-packet.json'),'role_sha256':digest(HERE/'review-role.txt'),
         'blind_key_sha256':digest(HERE/'review-key-private.json'),'calls_each':1,
         'masking_limit':'version/generator hidden; shared profiles and textual clues may reveal paired identities; not guaranteed perfect blinding'})
    print('Frozen six source-masked conversations, packet bytes:',(HERE/'review-packet.json').stat().st_size)


def review(provider):
    frozen=json.loads((HERE/'review-freeze.json').read_text())
    for name,key in [('review-packet.json','packet_sha256'),('review-role.txt','role_sha256')]:
        assert digest(HERE/name)==frozen[key]
    packet=json.loads((HERE/'review-packet.json').read_text())
    body=(HERE/'review-packet.json').read_text();role=(HERE/'review-role.txt').read_text()
    if len(body.encode())>32000:raise ValueError('Review packet too large')
    output=call_once(provider,body,role,HERE/'reviews'/provider)
    value=M1.parse_review(output['text']);M1.validate_review(value,packet)
    dump(HERE/'reviews'/provider/'validated.json',value)
    print(provider+': one review received; 6 scores and exact quotations validated')


def aggregate(reviews,packet,key):
    if set(reviews)!={'codex','claude'}:raise ValueError('Both single reviews required')
    indexed={p:{r['blind_id']:r for r in M1.validate_review(v,packet)} for p,v in reviews.items()}
    if set(key)!={c['blind_id'] for c in packet['cases']}:raise ValueError('Blind mapping incomplete')
    paired={}
    for blind,meta in key.items():
        case=paired.setdefault(meta['case_id'],{})
        if meta['condition'] not in {'v02','v03'} or meta['condition'] in case:raise ValueError('Duplicate/invalid condition')
        original={p:indexed[p][blind]['score'] for p in indexed}
        case[meta['condition']]={'blind_id':blind,'original_scores':original,'mean':sum(original.values())/2}
    rows=[]
    for ident,values in sorted(paired.items()):
        if set(values)!={'v02','v03'}:raise ValueError('Each case needs both versions')
        rows.append({'case_id':ident,**values,'delta_v03_minus_v02':values['v03']['mean']-values['v02']['mean']})
    means={v:sum(r[v]['mean'] for r in rows)/len(rows) for v in ['v02','v03']}
    judges={p:{v:sum(r[v]['original_scores'][p] for r in rows)/len(rows) for v in ['v02','v03']} for p in indexed}
    for p in judges:judges[p]['delta_v03_minus_v02']=judges[p]['v03']-judges[p]['v02']
    return {'kind':'paired_descriptive_development_comparison','scale':'adapted_PATIENTSIM_Realism_1_to_4',
            'cases':rows,'condition_means':means,'delta_v03_minus_v02':means['v03']-means['v02'],
            'judge_specific_means':judges,'case_delta_counts':{'positive':sum(r['delta_v03_minus_v02']>0 for r in rows),
            'zero':sum(r['delta_v03_minus_v02']==0 for r in rows),'negative':sum(r['delta_v03_minus_v02']<0 for r in rows)},
            'clinical_validation':'not_performed','inference':'3 reused development cases, one conversation per condition, one rating per model; not final performance or causal certainty'}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['freeze','generate','review-packet','review','aggregate']);ap.add_argument('--reviewer',choices=['codex','claude']);a=ap.parse_args()
    if a.action=='freeze':freeze()
    elif a.action=='generate':
        plan=read_plan()
        with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(run_pair,plan['cases']))
        print('Completed 6 dialogues / 24 patient turns:',results)
    elif a.action=='review-packet':make_review()
    elif a.action=='review':
        if not a.reviewer:ap.error('--reviewer required')
        review(a.reviewer)
    else:
        packet=json.loads((HERE/'review-packet.json').read_text());key=json.loads((HERE/'review-key-private.json').read_text())
        result=aggregate({p:json.loads((HERE/'reviews'/p/'validated.json').read_text()) for p in ['codex','claude']},packet,key)
        dump(HERE/'scores.json',result);print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
