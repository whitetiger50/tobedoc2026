"""M18: same inputs, two frozen criteria, two subscription judges, three fresh reads."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from datetime import datetime,timezone
import argparse,hashlib,json,random,time
from common import HERE,ROOT,BASE,read,dump,sha,canonical,validate_safe,fallback_validation
from collaboration.subscription_call import call_once,preflight
from generate_dialogues import verify as verify_generation

def prepare():
    verify_generation()
    if (HERE/'corpus.json').exists():raise FileExistsError('Preserve existing corpus')
    spec=read(HERE/'perturbation-spec.json');rows=[];sources={}
    def add(t,condition,payload,targets,parent=None,edits=None):
        item=t['item_id'] if condition=='N' else t['case_id']+'-'+condition
        body=canonical(payload);directory=HERE/'inputs';directory.mkdir(exist_ok=True)
        path=directory/(item+'.json');path.write_text(body)
        rows.append({'item_id':item,'case_id':t['case_id'],'condition':condition,
          'kind':'natural_generated' if condition=='N' else 'authored_control',
          'generation_replicate':t.get('generation_replicate'),'parent_id':parent,
          'input_sha256':sha(path),'payload':payload,'targets':targets,'edits':edits,
          'author_hypothesis_only':condition!='N'})
    for case in read(HERE/'cases.json')['cases']:
        for rep in [1,2,3]:
            f=HERE/'runs'/case['case_id']/f'rep{rep:02d}'/'transcript.json';t=read(f)
            sources[str(f.relative_to(ROOT))]=sha(f)
            payload={'patient_profile':{k:deepcopy(t['patient'][k]) for k in ['facts','self_understanding']},
              'communication':deepcopy(t['communication']),'prior_authored_context':deepcopy(t['authored_context']),
              'dialogue':deepcopy(t['generated_dialogue'])}
            turns={x['turn_id']:x for x in payload['dialogue']}
            add(t,'N',deepcopy(payload),{'P04':[[0,len(turns['P04']['text'])]]})
            if rep!=1:continue
            for condition in ['P','G','U','F','X']:
                variant=deepcopy(payload);v={x['turn_id']:x for x in variant['dialogue']};targets={};edits=[]
                def replace(tid,text,spans):
                    old=v[tid]['text'];v[tid]['text']=text;targets[tid]=spans
                    edits.append({'turn_id':tid,'original':old,'replacement':text,'changed':old!=text})
                if condition=='P':
                    replacement=turns['P02']['text'];replace('P04',replacement,[[0,len(replacement)]])
                elif condition=='G':
                    ref=case['authored_experience_reference'];goal=case['authored_goal_sentence'].replace('싶다.','싶어요.')
                    replace('P08',ref+' '+goal,[[0,len(ref)]])
                elif condition=='U':
                    replacement=turns['P03']['text'];replace('P06',replacement,[[0,len(replacement)]])
                elif condition=='F':
                    for tid in spec['F']['turns']:
                        old=turns[tid]['text'];prefix=spec['F']['prefix'];suffix=spec['F']['suffix']
                        replace(tid,prefix+old+suffix,[[0,len(prefix)],[len(prefix)+len(old),len(prefix)+len(old)+len(suffix)]])
                else:
                    prefix=spec['X']['prefix'];replace('P06',prefix+turns['P06']['text'],[[0,len(prefix)]])
                add(t,condition,variant,targets,t['item_id'],edits)
    assert len(rows)==24
    # Same bytes are rated once per criterion/model/repetition; retain all condition aliases.
    seen={};unique=[]
    for row in sorted(rows,key=lambda x:(x['condition']!='N',x['item_id'])):
        key=row['input_sha256']
        if key not in seen:seen[key]=row['item_id'];unique.append(row)
        else:assert canonical(row['payload'])==canonical(next(x for x in unique if x['item_id']==seen[key])['payload'])
        row['semantic_id']=seen[key]
    by_id={x['item_id']:x for x in rows}
    for row in rows:
        row['semantic_id']=seen[row['input_sha256']]
        row['manipulation_realized']=row['input_sha256']!=by_id[row['parent_id']]['input_sha256'] if row['parent_id'] else None
    rng=random.Random(20261119018);slots=[]
    for provider in ['codex','claude']:
        for repetition in [1,2,3]:
            pool=[(row,criterion) for row in unique for criterion in ['realism','ccf']];rng.shuffle(pool)
            for pos,(row,criterion) in enumerate(pool,1):
                sid=f'{provider}-r{repetition:02d}-p{pos:02d}'
                opaque=hashlib.sha256(f'M18:{sid}:{criterion}:{row["item_id"]}'.encode()).hexdigest()[:18]
                slots.append({'provider':provider,'criterion':criterion,'repetition':repetition,'position':pos,
                              'item_id':row['item_id'],'slot_id':sid,'opaque_id':opaque})
    dump(HERE/'corpus.json',{'profiles':3,'natural_generations':9,'authored_variants':15,'condition_rows':24,
      'unique_inputs':len(unique),'unique_item_ids':[x['item_id'] for x in unique],
      'planned_rating_calls':len(slots),'source_sha256':sources,'items':rows,'final12_used':0})
    dump(HERE/'schedule.json',{'seed':20261119018,'slots':slots,'provider_workers':2,'round_barrier':True,
      'single_dialogue_per_fresh_context':True,'criterion_and_case_randomized_together':True})
    print('Prepared24conditionrows/',len(unique),'unique inputs/',len(slots),'planned calls',flush=True)

def freeze():
    if (HERE/'freeze.json').exists():raise FileExistsError('Already frozen')
    verify_generation();corpus=read(HERE/'corpus.json');audit=read(HERE/'author-prejudge-audit.json')
    assert audit['new_judge_outputs_seen']==0 and audit['actual_generated_turns_read']==72
    assert audit['corpus_sha256']==sha(HERE/'corpus.json')
    assert sha(HERE/'role-realism.txt')==sha(ROOT/'development/aligned-input-residual-m15-v01/review-role.txt')
    assert sha(HERE/'role-ccf.txt')==sha(ROOT/'collaboration/strategy/M17-evaluation-rubric-revision-v01/evaluator-instructions-proposal.txt')
    files=[p for p in HERE.glob('*') if p.is_file() and p.suffix in ['.py','.json','.md','.txt'] and p.name not in ['freeze.json']]
    files+=list((HERE/'inputs').glob('*.json'))
    files+=[ROOT/'collaboration/subscription_call.py',ROOT/'development/rater-reliability-m12-v01/experiment.py',
            ROOT/'analysis/development-rating-reliability-v01/reliability.py']
    dump(HERE/'freeze.json',{'timestamp_utc':datetime.now(timezone.utc).isoformat(),
      'planned_rating_calls':corpus['planned_rating_calls'],'unique_inputs':corpus['unique_inputs'],
      'file_sha256':{str(p.relative_to(ROOT)):sha(p) for p in files},'source_sha256':corpus['source_sha256'],
      'author_audit_before_first_judge':True,'both_exact_criterion_roles_unchanged':True,'final12_used':0})
    print('Frozen actual corpus, author audit, schedule and analysis before first rating',flush=True)

def verify():
    verify_generation();f=read(HERE/'freeze.json')
    for group in ['file_sha256','source_sha256']:
        for path,expected in f[group].items():
            if sha(ROOT/path)!=expected:raise ValueError('Frozen file changed: '+path)
    return f

def run_slot(slot,version):
    verify();base=HERE/'reviews'/slot['provider']/slot['opaque_id']
    if base.exists():raise FileExistsError('Already started, no rerating')
    body=(HERE/'inputs'/(slot['item_id']+'.json')).read_text();start=time.monotonic()
    try:
        response=call_once(slot['provider'],body,(HERE/f'role-{slot["criterion"]}.txt').read_text(),base)
        raw=None
        try:
            raw=BASE.parse(response['text']);dump(base/'parsed.json',raw)
            validated=validate_safe(raw,json.loads(body),slot['criterion'])
        except (ValueError,TypeError,KeyError,AssertionError) as e:
            validated=fallback_validation(raw,e)
        dump(base/'validated.json',validated);dump(base/'slot.json',dict(slot,elapsed_seconds=time.monotonic()-start))
        print(slot['slot_id'],slot['criterion'],slot['item_id'],'score='+str(validated['realism_score']),
              'schema='+str(validated['fully_schema_valid']),flush=True)
        if read(base/'metadata.json')['cli_version']!=version:raise RuntimeError('CLI version changed, received score retained')
        return True
    except Exception as e:
        dump(HERE/'failures'/(slot['slot_id']+'.json'),{'slot':slot,'exception':type(e).__name__,'message':str(e),'automatic_retry':False})
        print(slot['slot_id'],'technical_stop',type(e).__name__,str(e),flush=True);return False

def run(provider):
    verify();_,version,method=preflight(provider);slots=read(HERE/'schedule.json')['slots'];failed=False
    dump(HERE/f'{provider}-execution-start.json',{'timestamp_utc':datetime.now(timezone.utc).isoformat(),
      'provider':provider,'cli_version':version,'auth_method':method,'planned_slots':sum(s['provider']==provider for s in slots)})
    for rep in [1,2,3]:
        block=iter(s for s in slots if s['provider']==provider and s['repetition']==rep)
        with ThreadPoolExecutor(max_workers=2) as pool:
            active=set()
            for _ in range(2):
                s=next(block,None)
                if s:active.add(pool.submit(run_slot,s,version))
            while active:
                done,active=wait(active,return_when=FIRST_COMPLETED)
                for f in done:
                    if not f.result():failed=True
                if not failed:
                    for _ in done:
                        s=next(block,None)
                        if s:active.add(pool.submit(run_slot,s,version))
        if failed:break
    dump(HERE/f'{provider}-execution.json',{'provider':provider,'status':'technical_stop' if failed else 'all_planned_recorded',
      'timestamp_utc':datetime.now(timezone.utc).isoformat(),'automatic_retries':0})
    if failed:raise RuntimeError('Provider technical stop; no retry')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','freeze','verify','run']);p.add_argument('--provider',choices=['codex','claude']);a=p.parse_args()
    if a.action=='prepare':prepare()
    elif a.action=='freeze':freeze()
    elif a.action=='verify':verify();print('Frozenfiles verified')
    elif a.provider:run(a.provider)
    else:p.error('--provider required')
