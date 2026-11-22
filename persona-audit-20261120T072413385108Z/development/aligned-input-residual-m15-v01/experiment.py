"""M15 single-dialogue fresh-session ratings with unchanged M12 criterion/parser."""
from pathlib import Path
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,json,random,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT))
from collaboration.subscription_call import call_once,preflight
from generate_dialogues import verify as verify_generation
spec=importlib.util.spec_from_file_location('M12parser',ROOT/'development/rater-reliability-m12-v01/experiment.py')
M12=importlib.util.module_from_spec(spec);spec.loader.exec_module(M12)
parse=M12.parse;validate=M12.validate;PROVIDERS=('codex','claude')
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def dump(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

def prepare():
    verify_generation()
    if (HERE/'corpus.json').exists():raise FileExistsError('Preserve existing corpus')
    rows=[];sources={}
    for case in read(HERE/'cases.json')['cases']:
        for rep in [1,2,3]:
            f=HERE/'runs'/case['case_id']/f'rep{rep:02d}'/'transcript.json';t=read(f)
            payload={'patient_profile':{k:deepcopy(t['patient'][k]) for k in ['facts','self_understanding']},
                     'communication':deepcopy(t['communication']),'prior_authored_context':deepcopy(t['authored_context']),
                     'dialogue':deepcopy(t['generated_dialogue'])}
            item=t['item_id'];p=HERE/'inputs'/f'{item}.json';p.parent.mkdir(exist_ok=True);p.write_text(canonical(payload))
            sources[str(f.relative_to(ROOT))]=sha(f)
            rows.append({'item_id':item,'case_id':case['case_id'],'generation_replicate':rep,'kind':'actual_generated_aligned_v02',
                         'source_path':str(f.relative_to(ROOT)),'input_sha256':sha(p),'payload':payload})
    assert len(rows)==9
    rng=random.Random(20261119015);slots=[]
    for provider in PROVIDERS:
        last=None
        for rep in [1,2,3]:
            for _ in range(100000):
                order=rng.sample(rows,9)
                if order[0]['case_id']!=last and all(a['case_id']!=b['case_id'] for a,b in zip(order,order[1:])):break
            else:raise RuntimeError('Cannot build order')
            last=order[-1]['case_id']
            for pos,row in enumerate(order,1):
                opaque=hashlib.sha256(f'M15:{provider}:{rep}:{pos}:{row["item_id"]}'.encode()).hexdigest()[:16]
                slots.append({'provider':provider,'repetition':rep,'position':pos,'item_id':row['item_id'],
                              'slot_id':f'{provider}-r{rep:02d}-p{pos:02d}','opaque_id':opaque})
    dump(HERE/'corpus.json',{'profiles':3,'dialogues':9,'new_actual_patient_outputs':72,'items':rows,
         'source_sha256':sources,'unique_semantic_inputs':len({r['input_sha256'] for r in rows}),'final12_used':0,
         'scope':'ReusedM13developmentprofiles,new aligneddialogues;not9independentprofiles'})
    dump(HERE/'schedule.json',{'seed':20261119015,'slots':slots,'one_dialogue_per_fresh_session':True,
         'provider_workers':2,'round_barrier':True,'adjacent_profiles_distinct':True,'opaque_ids_external_only':True})
    print('Prepared9actualdialogs/54single-dialogue ratings;unique semanticinputs',len({r['input_sha256'] for r in rows}),flush=True)

def freeze():
    if (HERE/'freeze.json').exists():raise FileExistsError('Already frozen')
    verify_generation();corpus=read(HERE/'corpus.json');audit=read(HERE/'author-prejudge-audit.json')
    assert audit['reviewed_patient_turns']==72 and audit['new_judge_outputs_seen']==0
    assert audit['corpus_sha256']==sha(HERE/'corpus.json')
    assert len(read(HERE/'schedule.json')['slots'])==54
    files=[HERE/n for n in ['experiment.py','analysis_stats.py','test_protocol.py','fixture-results.json','methods.md',
         'cases.json','question-audit.json','attribution-rules.json','author-prejudge-audit.json','review-role.txt',
         'score-anchors.json','generation-freeze.json','corpus.json','schedule.json']]
    files+=list((HERE/'inputs').glob('*.json'))
    files+=[ROOT/'collaboration/subscription_call.py',ROOT/'development/rater-reliability-m12-v01/experiment.py',
            ROOT/'development/rater-reliability-m12-v01/analysis_stats.py',ROOT/'analysis/development-rating-reliability-v01/reliability.py']
    for n in ['review-role.txt','score-anchors.json']:
        assert sha(HERE/n)==sha(ROOT/'development/rater-reliability-m12-v01'/n)
    for row in corpus['items']:
        p=HERE/'inputs'/f'{row["item_id"]}.json';assert sha(p)==row['input_sha256'] and read(p)==row['payload']
    dump(HERE/'freeze.json',{'timestamp_utc':datetime.now(timezone.utc).isoformat(),'planned_numeric_calls':54,
         'requested_models':{'codex':'gpt-6.1-sol high','claude':'claude-opus-5-5 medium'},
         'file_sha256':{str(p.relative_to(ROOT)):sha(p) for p in files},'source_sha256':corpus['source_sha256'],
         'author_audit_before_first_judge':True,'criteria_and_parser_unchanged':True,'final12_used':0})
    print('Frozen54ratingplan andprejudgeauthoraudit beforefirst numericreading',flush=True)

def verify():
    verify_generation();f=read(HERE/'freeze.json')
    for section in ['file_sha256','source_sha256']:
        for p,h in f[section].items():
            if sha(ROOT/p)!=h:raise ValueError('Frozen file changed:'+p)
    return f

def run_slot(slot,version):
    verify();base=HERE/'reviews'/slot['provider']/slot['opaque_id']
    if base.exists():raise FileExistsError('Already started;never rerate')
    start=time.monotonic();body=(HERE/'inputs'/f'{slot["item_id"]}.json').read_text()
    try:
        response=call_once(slot['provider'],body,(HERE/'review-role.txt').read_text(),base)
        try:
            raw=parse(response['text']);v=validate(raw,json.loads(body));dump(base/'parsed.json',raw)
        except (ValueError,TypeError,KeyError,AssertionError) as error:
            v={'realism_score':None,'realism_numeric_valid':False,'facets':{},'schema_errors':['unparseable:'+str(error)],
               'quote_errors':[],'fully_schema_valid':False,'all_provided_quotes_exact':False}
        dump(base/'validated.json',v);dump(base/'slot.json',dict(slot,elapsed_seconds=time.monotonic()-start))
        print(slot['slot_id'],slot['item_id'],'score='+str(v['realism_score']),'schema='+str(v['fully_schema_valid']),flush=True)
        if read(base/'metadata.json')['cli_version']!=version:raise RuntimeError('CLIversionchanged;retainreceivedscore,stopprovider')
        return True
    except Exception as error:
        dump(HERE/'failures'/f'{slot["slot_id"]}.json',{'slot':slot,'exception':type(error).__name__,
             'message':str(error),'automatic_retry':False,'elapsed_seconds':time.monotonic()-start})
        print(slot['slot_id'],'technical_stop',type(error).__name__,str(error),flush=True);return False

def run(provider):
    verify();_,version,method=preflight(provider);failed=False
    dump(HERE/f'{provider}-execution-start.json',{'timestamp_utc':datetime.now(timezone.utc).isoformat(),
         'provider':provider,'cli_version':version,'auth_method':method,'planned_slots':27})
    slots=read(HERE/'schedule.json')['slots']
    for rep in [1,2,3]:
        block=iter(s for s in slots if s['provider']==provider and s['repetition']==rep)
        with ThreadPoolExecutor(max_workers=2) as pool:
            active={pool.submit(run_slot,next(block),version) for _ in range(2)}
            while active:
                done,active=wait(active,return_when=FIRST_COMPLETED)
                for f in done:
                    if not f.result():failed=True
                if not failed:
                    for _ in done:
                        s=next(block,None)
                        if s is not None:active.add(pool.submit(run_slot,s,version))
        if failed:break
    dump(HERE/f'{provider}-execution.json',{'provider':provider,'status':'technical_stop' if failed else 'all27_slots_recorded',
         'timestamp_utc':datetime.now(timezone.utc).isoformat(),'automatic_retries':0})
    if failed:raise RuntimeError('Technicalstop;preserve results,noretry')

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','freeze','verify','run']);p.add_argument('--provider',choices=PROVIDERS);a=p.parse_args()
    if a.action=='prepare':prepare()
    elif a.action=='freeze':freeze()
    elif a.action=='verify':verify();print('Frozenfilesverified')
    elif a.provider:run(a.provider)
    else:p.error('--providerrequired')
if __name__=='__main__':main()
