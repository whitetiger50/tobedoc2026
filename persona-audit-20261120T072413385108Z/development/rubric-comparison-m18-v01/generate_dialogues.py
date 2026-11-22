"""Fixed v0.2 generation: three newly authored M18 profiles x three starts."""
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
    cases=read(HERE/'cases.json')['cases'];assert len(cases)==3
    for c in cases:
        for q,ids in zip(c['questions'],c['required_fact_ids']):
            build_packet(dict(c['input'],current_question=q),module_version=V02_VERSION,required_fact_ids=tuple(ids),question_reviewed=True)
    strategy=ROOT/'collaboration/strategy/M18-rubric-comparison-v01'
    assert (strategy/'decision.md').exists()
    files=[HERE/n for n in ['generate_dialogues.py','cases.json','question-audit.json','perturbation-spec.json','methods.md','role-realism.txt','role-ccf.txt']]
    files += [ROOT/'collaboration/subscription_call.py',strategy/'decision.md',strategy/'astra-round01.md',strategy/'astra-round02.md',strategy/'claude-round01/response.txt',strategy/'claude-round02/response.txt']
    files += [p for p in (ROOT/'speech_module').glob('*') if p.is_file()]
    protected=read(strategy/'scope-freeze.json')['protected_final_files_sha256']
    dump(HERE/'generation-freeze.json',{'timestamp_utc':datetime.now(timezone.utc).isoformat(),'profiles':3,'generation_starts_per_profile':3,'planned_dialogues':9,'planned_patient_outputs':72,'module_version':V02_VERSION,'requested_model':'gpt-6.1-sol high','maximum_numeric_judge_calls':288,'file_sha256':{str(p.relative_to(ROOT)):sha(p) for p in files},'protected_final_files_sha256':protected,'final12_content_read':False})
    print('Frozen new3profiles x3starts:9dialogs/72patientturns; v02 unchanged',flush=True)

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
                 'question_design':'M18newprofilesandquestions;explicitlivingreconfirmation/goalreference'})
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
