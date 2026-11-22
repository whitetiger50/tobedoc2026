"""Fixed v0.2 generation: 3 existing development profiles x 3 independent starts."""
from pathlib import Path
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import argparse, hashlib, json, sys, threading
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT))
from collaboration.subscription_call import call_once
from speech_module.core import V02_VERSION,build_packet,generate
STOP=threading.Event()
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

def freeze():
    if (HERE/'generation-freeze.json').exists():raise FileExistsError('Already frozen')
    cases=read(HERE/'cases.json')['cases'];audit=read(HERE/'question-audit.json')
    assert len(cases)==3 and len(audit['rows'])==24 and audit['changed_questions']==4
    source=read(ROOT/'development/graded-discrimination-m13-v01/cases.json')
    for c in cases:
        old=next(x for x in source['cases'] if x['case_id']==c['case_id'])
        for key in ['patient','communication','history']:assert c['input'][key]==old['input'][key]
        for q,ids in zip(c['questions'],c['required_fact_ids']):
            build_packet(dict(c['input'],current_question=q),module_version=V02_VERSION,
                         required_fact_ids=tuple(ids),question_reviewed=True)
    files=[HERE/n for n in ['generate_dialogues.py','cases.json','question-audit.json','attribution-rules.json',
                            'methods.md','review-role.txt','score-anchors.json']]
    files += [ROOT/'collaboration/subscription_call.py',ROOT/'development/graded-discrimination-m13-v01/cases.json',
              ROOT/'collaboration/strategy/M14-v02-resumption-plan-v01/next-development-plan.md',
              ROOT/'collaboration/strategy/M14-v02-resumption-plan-v01/question-readiness-plan.md']
    files += [p for p in (ROOT/'speech_module').glob('*') if p.is_file()]
    protected=[p for p in (ROOT/'share/PATIENTSIM-reliability-pilot-v01').rglob('*') if p.is_file()]
    dump(HERE/'generation-freeze.json',{'timestamp_utc':datetime.now(timezone.utc).isoformat(),
         'authorization':'Userexplicitlyrequestedaligneddevelopmentgenerationwithv02andGPT6.1SolHigh;GPT/Claude3freshsingle-dialoguereadings;final12excluded',
         'profiles':3,'generation_starts_per_profile':3,'planned_dialogues':9,'planned_patient_outputs':72,
         'module_version':V02_VERSION,'requested_model':'gpt-6.1-sol high','planned_numeric_judge_calls':54,
         'file_sha256':{str(p.relative_to(ROOT)):sha(p) for p in files},
         'protected_final_files_sha256':{str(p.relative_to(ROOT)):sha(p) for p in protected},
         'M14_direction_review_reused_no_new_mentor_call':True,'final12_content_read':False})
    print('Frozen aligned3profiles x3starts:9dialogs/72patientturns;unchangedv02/criteria',flush=True)

def verify():
    f=read(HERE/'generation-freeze.json')
    for section in ['file_sha256','protected_final_files_sha256']:
        for p,h in f[section].items():
            if sha(ROOT/p)!=h:raise ValueError('Frozen file changed:'+p)
    return f

def run_case(case):
    for rep in [1,2,3]:
        if STOP.is_set():return
        base=HERE/'runs'/case['case_id']/f'rep{rep:02d}'
        if base.exists():raise FileExistsError('Do not regenerate started dialogue')
        data=deepcopy(case['input']);dialogue=[]
        try:
            for n,(q,ids) in enumerate(zip(case['questions'],case['required_fact_ids']),1):
                if STOP.is_set():return
                verify();data['current_question']=q;directory=base/f'turn{n:02d}'
                def backend(messages):
                    return call_once('codex',messages[1]['content'],messages[0]['content'],directory/'transport')
                answer=generate(data,backend,directory,module_version=V02_VERSION,
                                required_fact_ids=tuple(ids),question_reviewed=True)
                dialogue.extend([{'turn_id':f'D{n:02d}','speaker':'clinician','text':q},
                                 {'turn_id':f'P{n:02d}','speaker':'patient','text':answer}])
                data['history'].extend([{'speaker':'clinician','text':q},{'speaker':'patient','text':answer}])
                print(case['case_id'],f'rep{rep:02d}',f'{n}/8 recorded',flush=True)
            dump(base/'transcript.json',{'item_id':f'{case["case_id"]}-rep{rep:02d}-v02',
                 'case_id':case['case_id'],'generation_replicate':rep,'partition':'development',
                 'module_version':V02_VERSION,'patient':case['input']['patient'],
                 'communication':case['input']['communication'],'authored_context':case['input']['history'],
                 'generated_dialogue':dialogue,'selection':'Firstandonlyactualanswerperturn;notpost-edited',
                 'question_design':'M15aligned;notpriorM13regenerationwithidenticalquestions'})
        except Exception as error:
            STOP.set();dump(base/'failure.json',{'exception':type(error).__name__,'message':str(error),
                 'automatic_retry':False,'completed_patient_turns':sum(x['speaker']=='patient' for x in dialogue)})
            raise

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','verify','run']);a=p.parse_args()
    if a.action=='freeze':freeze()
    elif a.action=='verify':verify();print('Generation files verified')
    else:
        verify()
        with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(run_case,read(HERE/'cases.json')['cases']))
        if STOP.is_set():raise RuntimeError('Generationtechnicalstop;preservepartialoutputs,noretry')
        print('All9dialogues/72patientturns recorded',flush=True)
if __name__=='__main__':main()
