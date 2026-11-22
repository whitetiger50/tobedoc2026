"""One prespecified v0.2 dialogue per new development profile; no retries/selection."""
from pathlib import Path
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import argparse, hashlib, json, sys
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from collaboration.subscription_call import call_once
from speech_module.core import V02_VERSION, build_packet, generate

def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2, allow_nan=False)+'\n')

def freeze():
    target=HERE/'generation-freeze.json'
    if target.exists(): raise FileExistsError('Already frozen')
    cases=read(HERE/'cases.json')['cases']
    for case in cases:
        for q, req in zip(case['questions'], case['required_fact_ids']):
            build_packet(dict(case['input'], current_question=q), module_version=V02_VERSION,
                         required_fact_ids=tuple(req), question_reviewed=True)
    files=[HERE/'cases.json', HERE/'perturbation-spec.json', HERE/'generate_reference.py', HERE/'generation-methods.md',
           ROOT/'collaboration/subscription_call.py', ROOT/'collaboration/strategy_call.py',
           ROOT/'collaboration/strategy/M13-graded-discrimination-v01/generation-decision.md']
    files += [p for p in (ROOT/'speech_module').glob('*') if p.is_file()]
    # Protect the final-pilot directory by hashing bytes only; never parse profiles.
    protected=[p for p in (ROOT/'share/PATIENTSIM-reliability-pilot-v01').rglob('*') if p.is_file()]
    dump(target, {'timestamp_utc':datetime.now(timezone.utc).isoformat(), 'module_version':V02_VERSION,
                 'planned_dialogues':3, 'planned_patient_outputs':24, 'model':'gpt-6.1-sol high',
                 'new_development_profiles':3, 'final12_content_read':False,
                 'file_sha256':{str(p.relative_to(ROOT)):sha(p) for p in files},
                 'protected_final_files_sha256':{str(p.relative_to(ROOT)):sha(p) for p in protected}})
    print('Frozen3newprofiles/8questions/v02:24single-turncalls;final12bytesprotected', flush=True)

def verify():
    f=read(HERE/'generation-freeze.json')
    for section in ['file_sha256','protected_final_files_sha256']:
        for p,h in f[section].items():
            if sha(ROOT/p)!=h: raise ValueError('Frozen input changed:'+p)
    return f

def run_case(case):
    base=HERE/'runs'/case['case_id']
    if base.exists(): raise FileExistsError('Never regenerate a started reference')
    data=deepcopy(case['input']); dialogue=[]
    try:
        for n,(q,req) in enumerate(zip(case['questions'],case['required_fact_ids']),1):
            verify(); data['current_question']=q; directory=base/f'turn{n:02d}'
            def backend(messages):
                return call_once('codex',messages[1]['content'],messages[0]['content'],directory/'transport')
            answer=generate(data,backend,directory,module_version=V02_VERSION,
                            required_fact_ids=tuple(req),question_reviewed=True)
            dialogue.extend([{'turn_id':f'D{n:02d}','speaker':'clinician','text':q},
                             {'turn_id':f'P{n:02d}','speaker':'patient','text':answer}])
            data['history'].extend([{'speaker':'clinician','text':q},{'speaker':'patient','text':answer}])
            print(case['case_id'],f'{n}/8actualpatientturns recorded',flush=True)
        dump(base/'transcript.json',{'case_id':case['case_id'],'partition':'development',
             'module_version':V02_VERSION,'patient':case['input']['patient'],
             'communication':case['input']['communication'],'authored_context':case['input']['history'],
             'generated_dialogue':dialogue,'selection':'first and only output per turn, no post-edit'})
    except Exception as e:
        dump(base/'failure.json',{'exception':type(e).__name__,'message':str(e),'retry':False})
        raise

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','verify','run']);a=p.parse_args()
    if a.action=='freeze': freeze()
    elif a.action=='verify': verify();print('Generation files verified')
    else:
        verify()
        with ThreadPoolExecutor(max_workers=3) as pool:
            list(pool.map(run_case,read(HERE/'cases.json')['cases']))
        print('All3reference dialogues/24patientturns recorded',flush=True)
if __name__=='__main__':main()
