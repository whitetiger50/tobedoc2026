"""M13: fixed-rubric, single-dialogue discrimination probe, existing subscriptions only."""
from pathlib import Path
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone
import argparse, hashlib, importlib.util, json, random, sys, time
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT))
from collaboration.subscription_call import call_once, preflight
from generate_reference import verify as verify_generation
spec=importlib.util.spec_from_file_location('m12parser',ROOT/'development/rater-reliability-m12-v01/experiment.py')
M12=importlib.util.module_from_spec(spec);spec.loader.exec_module(M12)
parse=M12.parse;validate=M12.validate
PROVIDERS=('codex','claude');CONDITIONS=('R','I','F1','F2','N1','N2')
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def dump(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

def prepare():
    verify_generation()
    if (HERE/'corpus.json').exists():raise FileExistsError('Preserve existing corpus')
    edits=read(HERE/'perturbation-spec.json');correction=read(HERE/'perturbation-orthography-correction.json')
    amendment=read(HERE/'stimulus-amendment-before-ratings.json')
    audit=read(HERE/'reference-audit.json');rows=[];sources={}
    for rule in edits['profiles']:
        case=rule['case_id'];f=HERE/'runs'/case/'transcript.json';t=read(f)
        a=next(v for v in audit['profiles'] if v['case_id']==case)
        assert a['eligible_for_amended_pilot'] is True and a['transcript_sha256']==sha(f)
        sources[str(f.relative_to(ROOT))]=sha(f)
        payload={'patient_profile':{k:deepcopy(t['patient'][k]) for k in ['facts','self_understanding']},
                 'communication':deepcopy(t['communication']),
                 'prior_authored_context':deepcopy(t['authored_context']),
                 'dialogue':deepcopy(t['generated_dialogue'])}
        original=next(v['text'] for v in payload['dialogue'] if v['turn_id']=='P02')
        for condition in CONDITIONS:
            body=deepcopy(payload);replacement=original
            if condition=='F1':replacement=original+' '+rule['F1_append']
            elif condition!='R':replacement=rule[condition]
            if condition in amendment['overrides'].get(case,{}):replacement=amendment['overrides'][case][condition]
            if case=='DEV-M13-03' and condition in ['N1','N2']:
                for before,after in correction['replacements'].items():replacement=replacement.replace(before,after)
            next(v for v in body['dialogue'] if v['turn_id']=='P02')['text']=replacement
            item=case+'-'+condition;kind='generated_reference' if condition=='R' else 'authored_invariance' if condition=='I' else 'authored_graded_control'
            row={'item_id':item,'case_id':case,'condition':condition,'kind':kind,'parent_id':None if condition=='R' else case+'-R',
                 'family':'reference' if condition=='R' else 'invariance' if condition=='I' else 'fact' if condition.startswith('F') else 'expression',
                 'payload':body,'source_path':str(f.relative_to(ROOT)),
                 'perturbation':None if condition=='R' else {'turn_id':'P02','original':original,'replacement':replacement,
                       'fact_ids':['living'],'changed_clause':rule['F1_append'] if condition=='F1' else replacement,
                       'author_provenance':'prewritten deterministic developer substitution, never a model-generated output'},
                 'patient_characters':sum(len(v['text']) for v in body['dialogue'] if v['speaker']=='patient'),
                 'target_characters':len(replacement),'target_eojeol':len(replacement.split())}
            text=canonical(body);p=HERE/'inputs'/f'{item}.json';p.parent.mkdir(exist_ok=True);p.write_text(text)
            row['input_sha256']=sha(p);rows.append(row)
    assert len(rows)==18 and len({r['input_sha256'] for r in rows})==18
    rng=random.Random(20261119013);slots=[]
    for provider in PROVIDERS:
        last=None
        for rep in [1,2,3]:
            for _ in range(100000):
                order=rng.sample(rows,len(rows))
                if order[0]['case_id']==last:continue
                if all(a['case_id']!=b['case_id'] for a,b in zip(order,order[1:])):break
            else:raise RuntimeError('Cannot form balanced schedule')
            last=order[-1]['case_id']
            for position,row in enumerate(order,1):
                opaque=hashlib.sha256(f'M13:{provider}:{rep}:{position}:{row["item_id"]}'.encode()).hexdigest()[:16]
                slots.append({'provider':provider,'repetition':rep,'position':position,'item_id':row['item_id'],
                              'slot_id':f'{provider}-r{rep:02d}-p{position:02d}','opaque_id':opaque})
    dump(HERE/'corpus.json',{'profiles':3,'reference_dialogues':3,'authored_variants':15,'items':rows,'source_sha256':sources,
         'new_generated_patient_outputs':24,'final12_used':0,'control_strength':'author intended, not clinician gold'})
    dump(HERE/'schedule.json',{'seed':20261119013,'slots':slots,'workers_each_provider':2,'round_barrier':True,
         'same_semantic_input_across_models_repeats':True,'adjacent_profile_distinct':True,'opaque_ids_external_only':True})
    print('Prepared18texts/108single-dialogue slots;allcontrolsfromprewrittenP02rules',flush=True)

def freeze():
    if (HERE/'freeze.json').exists():raise FileExistsError('Already frozen')
    verify_generation();corpus=read(HERE/'corpus.json');schedule=read(HERE/'schedule.json')
    assert len(schedule['slots'])==108
    files=[HERE/name for name in ['experiment.py','analysis_stats.py','test_protocol.py','fixture-results.json','methods.md',
           'references.json','review-role.txt','score-anchors.json','generation-freeze.json','perturbation-spec.json',
           'perturbation-orthography-correction.json','stimulus-amendment-before-ratings.json','reference-audit.json','corpus.json','schedule.json']]
    files += list((HERE/'inputs').glob('*.json'))
    files += [ROOT/'collaboration/subscription_call.py',ROOT/'development/rater-reliability-m12-v01/experiment.py',
              ROOT/'development/rater-reliability-m12-v01/analysis_stats.py',ROOT/'analysis/development-rating-reliability-v01/reliability.py']
    strategy=ROOT/'collaboration/strategy/M13-graded-discrimination-v01'
    files += [strategy/n for n in ['decision.md','astra-round01.md','astra-round02.md','claude-round01/response.txt','claude-round02/response.txt']]
    for r in corpus['items']:
        p=HERE/'inputs'/f'{r["item_id"]}.json';assert sha(p)==r['input_sha256'] and read(p)==r['payload']
    for n in ['review-role.txt','score-anchors.json']:
        assert sha(HERE/n)==sha(ROOT/'development/rater-reliability-m12-v01'/n)
    dump(HERE/'freeze.json',{'timestamp_utc':datetime.now(timezone.utc).isoformat(),'planned_numeric_calls':108,
         'requested_models':{'codex':'gpt-6.1-sol high','claude':'claude-opus-5-5 medium'},
         'file_sha256':{str(p.relative_to(ROOT)):sha(p) for p in files},'source_sha256':corpus['source_sha256'],
         'criteria_unchanged_from_M12':True,'final12_used':0,'new_judge_models':0})
    print('Frozen criteria/parser/corpus/schedule/analysis before first numeric rating',flush=True)

def verify():
    verify_generation();f=read(HERE/'freeze.json')
    for section in ['file_sha256','source_sha256']:
        for p,h in f[section].items():
            if sha(ROOT/p)!=h:raise ValueError('Frozen file changed:'+p)
    return f

def run_slot(slot,expected_version):
    verify();base=HERE/'reviews'/slot['provider']/slot['opaque_id']
    if base.exists():raise FileExistsError('Slot already started; no retry')
    started=time.monotonic();body=(HERE/'inputs'/f'{slot["item_id"]}.json').read_text()
    try:
        response=call_once(slot['provider'],body,(HERE/'review-role.txt').read_text(),base)
        try:
            raw=parse(response['text']);v=validate(raw,json.loads(body));dump(base/'parsed.json',raw)
        except (ValueError,TypeError,KeyError,AssertionError) as error:
            v={'realism_score':None,'realism_numeric_valid':False,'facets':{},'schema_errors':['unparseable:'+str(error)],
               'quote_errors':[],'fully_schema_valid':False,'all_provided_quotes_exact':False}
        dump(base/'validated.json',v);dump(base/'slot.json',dict(slot,elapsed_seconds=time.monotonic()-started))
        metadata=read(base/'metadata.json');version_ok=metadata['cli_version']==expected_version
        print(slot['slot_id'],slot['item_id'],'score='+str(v['realism_score']),'schema='+str(v['fully_schema_valid']),flush=True)
        if not version_ok:raise RuntimeError('CLI version changed; preserve received result, stop provider')
        return {'status':'recorded','slot':slot}
    except Exception as error:
        dump(HERE/'failures'/f'{slot["slot_id"]}.json',{'slot':slot,'exception':type(error).__name__,
             'message':str(error),'automatic_retry':False,'elapsed_seconds':time.monotonic()-started})
        print(slot['slot_id'],'technical_failure_no_retry',type(error).__name__,str(error),flush=True)
        return {'status':'technical_failure','slot':slot}

def run(provider):
    verify();_,version,method=preflight(provider);slots=read(HERE/'schedule.json')['slots'];failed=False
    dump(HERE/f'{provider}-execution-start.json',{'timestamp_utc':datetime.now(timezone.utc).isoformat(),
         'provider':provider,'cli_version':version,'auth_method':method,'planned_slots':54})
    for rep in [1,2,3]:
        block=iter(s for s in slots if s['provider']==provider and s['repetition']==rep)
        with ThreadPoolExecutor(max_workers=2) as pool:
            active={pool.submit(run_slot,next(block),version) for _ in range(2)}
            while active:
                done,active=wait(active,return_when=FIRST_COMPLETED)
                for f in done:
                    if f.result()['status']=='technical_failure':failed=True
                if not failed:
                    for _ in done:
                        s=next(block,None)
                        if s:active.add(pool.submit(run_slot,s,version))
        if failed:break
    dump(HERE/f'{provider}-execution.json',{'provider':provider,'status':'technical_stop' if failed else 'all54_slots_recorded',
         'timestamp_utc':datetime.now(timezone.utc).isoformat(),'automatic_retries':0})
    if failed:raise RuntimeError('Stopped provider; no extra rating')

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','freeze','verify','run']);p.add_argument('--provider',choices=PROVIDERS);a=p.parse_args()
    if a.action=='prepare':prepare()
    elif a.action=='freeze':freeze()
    elif a.action=='verify':verify();print('Frozen files verified')
    elif a.provider:run(a.provider)
    else:p.error('--provider required')
if __name__=='__main__':main()
