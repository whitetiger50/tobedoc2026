"""M12 frozen single-dialogue repeated ratings through existing subscription CLIs."""
from pathlib import Path
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,json,random,sys,threading,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT))
from collaboration.subscription_call import call_once
FACETS=('grounding','responsiveness','continuity','naturalness')
PROVIDERS=('codex','claude')
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def dump(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

def prepare():
 if (HERE/'corpus.json').exists():raise FileExistsError('Draft corpus already exists; preserve originals')
 rows=[];sources={}
 definitions=[('M6','development/speech-m6-generation-variability-v01',['v02','v04']),('M9','development/speech-m9-style-examples-v01',['none','examples'])]
 for case in ['DEV-M0-01','DEV-M0-02','DEV-M0-03']:
  for stage,base,conditions in definitions:
   for label in conditions:
    f=ROOT/base/'runs'/case/'rep03'/label/'transcript.json';t=read(f);sources[str(f.relative_to(ROOT))]=sha(f)
    item=f'{stage}-{case[-2:]}-{label}'
    patient={k:deepcopy(t['patient'][k]) for k in ['facts','self_understanding']}
    payload={'patient_profile':patient,'communication':deepcopy(t['communication']),'prior_authored_context':deepcopy(t['authored_context']),'dialogue':deepcopy(t['generated_dialogue'])}
    rows.append({'item_id':item,'case_id':case,'kind':'natural','stratum':'four_turn' if stage=='M6' else 'eight_turn','stage':stage,'condition':label,'source_path':str(f.relative_to(ROOT)),'source_item_id':t['item_id'],'payload':payload,'parent_id':None})
 for case in ['DEV-M0-01','DEV-M0-02','DEV-M0-03']:
  base=next(r for r in rows if r['case_id']==case and r['stage']=='M6' and r['condition']=='v02');x=deepcopy(base);x.update(item_id='CONTROL-'+case[-2:],kind='authored_fact_inversion',parent_id=base['item_id'],stratum='authored_control')
  turn='P02' if case.endswith('02') else 'P04'
  replacement={'DEV-M0-01':'어머니와는 함께 살지 않고 혼자 살아요.','DEV-M0-02':'누나하고 같이 살고 있어요. 혼자 사는 건 아니에요.','DEV-M0-03':'아버지와는 함께 살지 않고 혼자 살아요.'}[case]
  target=next(t for t in x['payload']['dialogue'] if t['turn_id']==turn)
  x['perturbation']={'turn_id':turn,'original':target['text'],'replacement':replacement,'reference_fact_ids':['living'],'profile_conflict':'explicit opposite of fixed cohabitation fact','author_provenance':'deterministic developer substitution; not an actual generated utterance','prior_authored_context':deepcopy(x['payload']['prior_authored_context']),'earlier_patient_turns':[t for t in x['payload']['dialogue'] if t['speaker']=='patient' and t['turn_id']<turn]}
  target['text']=replacement;rows.append(x)
 assert len(rows)==15 and len({r['item_id'] for r in rows})==15
 for r in rows:
  body=canonical(r['payload']);(HERE/'inputs').mkdir(exist_ok=True);(HERE/'inputs'/f"{r['item_id']}.json").write_text(body)
  r['input_sha256']=hashlib.sha256(body.encode()).hexdigest()
 rng=random.Random(20261119012);slots=[]
 for provider in PROVIDERS:
  last=None
  for repetition in [1,2,3]:
   for attempt in range(20000):
    order=rng.sample(rows,len(rows));positions={x['item_id']:i for i,x in enumerate(order)}
    if last and order[0]['case_id']==last:continue
    if any(a['case_id']==b['case_id'] for a,b in zip(order,order[1:])):continue
    if any(abs(positions[x['item_id']]-positions[x['parent_id']])<3 for x in order if x['parent_id']):continue
    break
   else:raise RuntimeError('Could not form bounded balanced order')
   last=order[-1]['case_id']
   for index,r in enumerate(order,1):slots.append({'provider':provider,'repetition':repetition,'position':index,'item_id':r['item_id'],'slot_id':f'{provider}-r{repetition:02d}-p{index:02d}','opaque_id':hashlib.sha256(f'{provider}:{repetition}:{index}:{r["item_id"]}:M12'.encode()).hexdigest()[:16]})
 dump(HERE/'corpus.json',{'kind':'existing_development_texts_plus_explicit_author_controls','profiles':3,'natural_texts':12,'authored_controls':3,'new_generated_patient_outputs':0,'items':rows,'source_sha256':sources})
 dump(HERE/'schedule.json',{'seed':20261119012,'slots':slots,'one_dialogue_per_fresh_session':True,'blind_ids':'external only; semantic model input is exactly identical for each text across both providers and all3repeats','within_round_parent_control_min_position_gap':3,'provider_workers':2,'round_barrier':True,'launch_order_vs_completion':'positions specify submission order; concurrent completion may differ and is logged'})
 print('Prepared12natural+3authoredcontrols;90single-dialogue slots; exact same input across repeats/providers')

def freeze():
 if (HERE/'freeze.json').exists():raise FileExistsError('Already frozen')
 corpus=read(HERE/'corpus.json');schedule=read(HERE/'schedule.json')
 assert len(schedule['slots'])==90
 files=[p for p in HERE.glob('*') if p.is_file() and p.name not in ['freeze.json']]
 files+=list((HERE/'inputs').glob('*.json'))
 files+=[ROOT/'collaboration/subscription_call.py',ROOT/'analysis/development-rating-reliability-v01/reliability.py',ROOT/'development/speech-m1-v01/sources/llm_eval_metrics_persona.json',ROOT/'speech_module/patient_v02.txt',ROOT/'speech_module/patient_v04.txt',ROOT/'speech_module/patient_v06.txt']
 review=ROOT/'collaboration/strategy/M12-reliability-protocol-v01'
 files += [review/'decision.md',review/'astra-round01.md',review/'astra-round02.md',review/'claude-round01/response.txt',review/'claude-round02/response.txt']
 for r in corpus['items']:
  p=HERE/'inputs'/f"{r['item_id']}.json";assert sha(p)==r['input_sha256'];assert read(p)==r['payload']
 for f,h in corpus['source_sha256'].items():assert sha(ROOT/f)==h
 dump(HERE/'freeze.json',{'timestamp_utc':datetime.now(timezone.utc).isoformat(),'authorized':'user requested fixedcriteria,freshsession pertext,eachGPT/Claude3times,noheldout12,newmodelsnone;protocolreviewcompleted','planned_calls':90,'planned_natural_rating_outputs':72,'planned_control_rating_outputs':18,'provider_models':{'codex':'gpt-6.1-sol high','claude':'claude-opus-5-5 medium'},'file_sha256':{str(p.relative_to(ROOT)):sha(p) for p in files},'source_sha256':corpus['source_sha256']})
 print('Frozen protocol,role,parser,statistics,inputs and90slot schedule before first rating')

def verify():
 frozen=read(HERE/'freeze.json')
 for group in ['file_sha256','source_sha256']:
  for f,h in frozen[group].items():
   if sha(ROOT/f)!=h:raise ValueError('Frozen file changed:'+f)
 return frozen

def parse(text):
 s=text.strip()
 if s.startswith('```'):
  lines=s.splitlines();assert lines[-1].strip()=='```';s='\n'.join(lines[1:-1])
 x=json.loads(s)
 if not isinstance(x,dict):raise ValueError('Expected one JSON object')
 return x

def validate(x,payload):
 turns={t['turn_id']:t['text'] for t in payload['dialogue'] if t['speaker']=='patient'};allturns={t['turn_id'] for t in payload['dialogue']};fact_ids={f['id'] for f in payload['patient_profile']['facts']}
 errors=[];quote_errors=[];dimensions={}
 def integer(v,lo,hi):return type(v) is int and lo<=v<=hi
 def evidence(values,label,required):
  if not isinstance(values,list):
   if required:errors.append(label+':missing_evidence')
   return []
  if required and not values:errors.append(label+':empty_required_evidence')
  output=[]
  for e in values:
   if not isinstance(e,dict):quote_errors.append({'dimension':label,'error':'bad_evidence_object'});continue
   tid=e.get('patient_turn_id');quote=e.get('quote');valid=tid in turns and isinstance(quote,str) and bool(quote) and quote in turns[tid]
   output.append({'patient_turn_id':tid,'quote':quote,'valid_quote':valid})
   if not valid:quote_errors.append({'dimension':label,'patient_turn_id':tid,'quote':quote,'error':'not_exact_generated_patient_quote'})
  return output
 score=x.get('realism_score');good=integer(score,1,4)
 if not good:errors.append('realism:invalid_numeric_score')
 if not isinstance(x.get('realism_reason'),str) or not x.get('realism_reason','').strip():errors.append('realism:missing_reason')
 global_evidence=evidence(x.get('realism_evidence',[]),'realism',good and score<4)
 facets=x.get('facets',{})
 if not isinstance(facets,dict):facets={};errors.append('facets:bad_object')
 for name in FACETS:
  d=facets.get(name);d=d if isinstance(d,dict) else {};raw=d.get('rating','MISSING');numeric=integer(raw,0,2);na=raw is None and 'rating'in d
  uncertain=d.get('uncertain');uvalid=type(uncertain)is bool
  if not numeric and not na:errors.append(name+':missing_or_invalid_rating')
  if not uvalid:errors.append(name+':missing_uncertainty_flag')
  reason=d.get('reason');rvalid=isinstance(reason,str) and bool(reason.strip())
  if not rvalid:errors.append(name+':missing_reason')
  ev=evidence(d.get('evidence',[]),name,numeric and (raw<2 or uncertain is True))
  refs=d.get('context_refs',[]);refsvalid=isinstance(refs,list) and all(isinstance(r,str) for r in refs)
  if refsvalid:
   for ref in refs:
    if ref=='authored_context':continue
    if ref.startswith('fact:') and ref[5:] in fact_ids:continue
    if ref.startswith('turn:') and ref[5:] in allturns:continue
    errors.append(name+':invalid_context_ref:'+ref)
  elif refs:errors.append(name+':invalid_context_refs')
  if numeric and raw<2 and (not refsvalid or not refs):errors.append(name+':missing_context_ref_for_finding')
  dimensions[name]={'rating':raw if numeric else None,'semantic_NA':na,'numeric_valid':numeric,'uncertain':uncertain if uvalid else None,'uncertainty_valid':uvalid,'reason':reason,'evidence':ev,'context_refs':refs if refsvalid else []}
 return {'realism_score':score if good else None,'realism_numeric_valid':good,'realism_reason':x.get('realism_reason'),'realism_evidence':global_evidence,'facets':dimensions,'schema_errors':errors,'quote_errors':quote_errors,'fully_schema_valid':not errors,'all_provided_quotes_exact':not quote_errors,'missingness_policy':'retain every valid numeric field; do not impute or discard a numeric score solely for another field/quotation error'}

def run_slot(slot):
 verify();base=HERE/'reviews'/slot['provider']/slot['opaque_id']
 if base.exists():raise FileExistsError('Slot already started; no automatic reattempt:'+str(base))
 body=(HERE/'inputs'/f"{slot['item_id']}.json").read_text();role=(HERE/'review-role.txt').read_text();start=time.monotonic()
 try:
  response=call_once(slot['provider'],body,role,base)
  try:
   x=parse(response['text']);v=validate(x,json.loads(body));dump(base/'parsed.json',x)
  except (ValueError,TypeError,KeyError,AssertionError) as error:
   v={'realism_score':None,'realism_numeric_valid':False,'facets':{},'schema_errors':['unparseable_response:'+str(error)],'quote_errors':[],'fully_schema_valid':False,'all_provided_quotes_exact':False}
  dump(base/'validated.json',v);dump(base/'slot.json',dict(slot,elapsed_seconds=time.monotonic()-start,response_characters=len(response['text'])))
  print(slot['slot_id'],slot['item_id'],'recorded','score='+str(v['realism_score']),'schema='+str(v['fully_schema_valid']),flush=True)
  return {'status':'recorded','slot':slot}
 except Exception as error:
  dump(HERE/'failures'/f"{slot['slot_id']}.json",{'slot':slot,'status':'technical_failure_no_retry','exception':type(error).__name__,'message':str(error),'elapsed_seconds':time.monotonic()-start})
  print(slot['slot_id'],'technical_failure_no_retry',type(error).__name__,str(error),flush=True)
  return {'status':'technical_failure','slot':slot}

def run(provider):
 verify();slots=read(HERE/'schedule.json')['slots'];failed=False
 for rep in [1,2,3]:
  block=[s for s in slots if s['provider']==provider and s['repetition']==rep];iterator=iter(block)
  with ThreadPoolExecutor(max_workers=2) as pool:
   active={pool.submit(run_slot,next(iterator)) for _ in range(2)}
   while active:
    done,active=wait(active,return_when=FIRST_COMPLETED)
    for f in done:
     result=f.result()
     if result['status']=='technical_failure':failed=True
    if not failed:
     for _ in done:
      item=next(iterator,None)
      if item is not None:active.add(pool.submit(run_slot,item))
  if failed:break
 dump(HERE/f'{provider}-execution.json',{'provider':provider,'status':'stopped_after_technical_failure' if failed else 'all45_slots_recorded','no_automatic_retries':True,'time_utc':datetime.now(timezone.utc).isoformat()})
 if failed:raise RuntimeError('Provider stopped; preserve completed/inflight responses, no extra rating')


def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','freeze','verify','run']);p.add_argument('--provider',choices=PROVIDERS);a=p.parse_args()
 if a.action=='prepare':prepare()
 elif a.action=='freeze':freeze()
 elif a.action=='verify':verify();print('Frozen files verified')
 else:
  if not a.provider:p.error('--provider required')
  run(a.provider)
if __name__=='__main__':main()
