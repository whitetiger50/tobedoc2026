"""Prespecified conditional reliability summaries; pure standard library."""
from pathlib import Path
from fractions import Fraction as F
from itertools import combinations,product
from collections import Counter
from math import sqrt
import importlib.util,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('m11rel',ROOT/'analysis/development-rating-reliability-v01/reliability.py');REL=importlib.util.module_from_spec(spec);spec.loader.exec_module(REL)
FACETS=('grounding','responsiveness','continuity','naturalness');PROVIDERS=('codex','claude')
def read(p):return json.loads(p.read_text())
def clean(x):return REL.serial(x)
def average(v):return sum(map(F,v))/len(v) if v else None

def one_way(matrix):
 n=len(matrix);k=len(matrix[0]) if matrix else 0
 if n<2 or k<2:return {'ICC11':None,'ICC1k':None,'reason':'insufficient_complete_rows','n':n,'k':k}
 assert all(len(r)==k for r in matrix)
 means=[average(r) for r in matrix];grand=average([v for r in matrix for v in r])
 msb=k*sum((v-grand)**2 for v in means)/F(n-1)
 msw=sum(sum((F(v)-mu)**2 for v in r) for r,mu in zip(matrix,means))/F(n*(k-1))
 den=msb+(k-1)*msw
 return {'ICC11':(msb-msw)/den if den else None,'ICC1k':(msb-msw)/msb if msb else None,'reason':None if den else 'zero_between_and_within_variation','n':n,'k':k,'MS_between':msb,'MS_within':msw,'within_text_SD':sqrt(float(msw)),'scope':'oneway random interchangeable rereads; interval-score sensitivity; no general population CI'}

def kappa(a,b):return REL.weighted_kappa(a,b) if a else {'value':None,'reason':'no_paired_numeric_observations'}
def matrix_summary(matrix):
 pairs=[(a,b) for r in matrix for a,b in combinations(r,2) if a is not None and b is not None]
 complete=[r for r in matrix if len(r)==3 and all(v is not None for v in r)]
 exact=F(sum(a==b for a,b in pairs),len(pairs)) if pairs else None
 kappas=[]
 for a,b in combinations(range(3),2):
  paired=[(r[a],r[b]) for r in matrix if r[a] is not None and r[b] is not None]
  kappas.append({'rounds':[a+1,b+1],'paired_texts':len(paired),**kappa([v[0] for v in paired],[v[1] for v in paired])})
 return {'texts_planned':len(matrix),'numeric_ratings':sum(v is not None for r in matrix for v in r),'complete_texts_for_ICC':len(complete),'all3equal_texts':sum(len(set(r))==1 for r in complete),'exact_numeric_pair_matches':sum(a==b for a,b in pairs),'numeric_pair_count':len(pairs),'exact_numeric_pair_agreement':exact,'mean_absolute_numeric_pair_difference':average([abs(a-b) for a,b in pairs]),'ordinal_alpha':REL.ordinal_alpha(matrix),'linear_weighted_kappa_by_pair':kappas,'round_score_counts':[dict(Counter(str(r[j]) for r in matrix if r[j] is not None)) for j in range(3)],'observed_text_ranges':[max(v)-min(v) if len(v)>=2 else None for v in [[x for x in row if x is not None] for row in matrix]],'ICC_primary_exploratory_oneway':one_way(complete),'ICC_twoway_sensitivity':REL.icc(complete) if len(complete)>1 else {'A1':None,'Ak':None,'reason':'insufficient_complete_rows'},'CI':'not_reported_3profiles_fixed_development_texts; leaveoneprofileout is descriptive not confidence interval'}

def direction(a,b):
 pairs=[(x,y) for x in a for y in b if x is not None and y is not None];ds=[F(y)-F(x) for x,y in pairs]
 return {'baseline_values':a,'candidate_values':b,'reused_pair_combinations':len(ds),'candidate_lower':sum(d<0 for d in ds),'tie':sum(d==0 for d in ds),'candidate_higher':sum(d>0 for d in ds),'mean_difference':average(ds),'both_directions_observed':any(d<0 for d in ds) and any(d>0 for d in ds),'all_observed_pairs_tie':bool(ds) and all(d==0 for d in ds),'warning':'combinations reuse the same3readings; not independent trials or a prompt-level effect estimate'}

def summarize(corpus,records):
 items=corpus['items'];byid={r['item_id']:r for r in items};natural=[r for r in items if r['kind']=='natural'];controls=[r for r in items if r['kind']!='natural']
 def get(i,p,r):return records.get((i,p,r),{})
 def value(i,p,r,d='realism'):
  v=get(i,p,r)
  return v.get('realism_score') if d=='realism' else v.get('facets',{}).get(d,{}).get('rating')
 def matrix(selected,p,d='realism'):return [[value(x['item_id'],p,r,d) for r in [1,2,3]] for x in selected]
 output={'natural_texts':12,'controls':3,'profiles':3,'planned_single_dialogue_sessions':90,'recorded_responses':len(records),'within_models':{},'strata':{},'profiles_descriptive':{},'leave_one_profile_out_descriptive':{},'between_models':{},'aggregate_repeatability':{},'contrasts':[],'control_probes':[],'dimension_missingness':{}}
 for p in PROVIDERS:
  output['within_models'][p]={d:matrix_summary(matrix(natural,p,d)) for d in ['realism',*FACETS]}
  output['strata'][p]={group:matrix_summary(matrix([i for i in natural if i['stratum']==group],p)) for group in ['four_turn','eight_turn']}
  output['profiles_descriptive'][p]={case:matrix_summary(matrix([i for i in natural if i['case_id']==case],p)) for case in ['DEV-M0-01','DEV-M0-02','DEV-M0-03']}
  output['leave_one_profile_out_descriptive'][p]={case:matrix_summary(matrix([i for i in natural if i['case_id']!=case],p)) for case in ['DEV-M0-01','DEV-M0-02','DEV-M0-03']}
  output['dimension_missingness'][p]={}
  for d in FACETS:
   states=[];uncertainties=[]
   for i in natural:
    ds=[get(i['item_id'],p,r).get('facets',{}).get(d,{}) for r in [1,2,3]]
    states.append(['NA' if v.get('semantic_NA') else 'numeric' if v.get('numeric_valid') else 'technical_missing' for v in ds]);uncertainties.append([v.get('uncertain') for v in ds])
   statepairs=[(a,b) for row in states for a,b in combinations(row,2)];upairs=[(a,b) for row in uncertainties for a,b in combinations(row,2) if a is not None and b is not None]
   output['dimension_missingness'][p][d]={'state_counts':dict(Counter(x for row in states for x in row)),'NA_and_technical_state_pair_matches':sum(a==b for a,b in statepairs),'state_pairs':len(statepairs),'uncertain_true':sum(x is True for row in uncertainties for x in row),'uncertain_false':sum(x is False for row in uncertainties for x in row),'uncertainty_pair_matches':sum(a==b for a,b in upairs),'uncertainty_pairs':len(upairs)}
 # Fixed model interagreement: each nominal round and3repeat model means separately.
 for d in ['realism',*FACETS]:
  perround=[];cross=[]
  for r in [1,2,3]:
   pairs=[(value(i['item_id'],'codex',r,d),value(i['item_id'],'claude',r,d)) for i in natural];pairs=[(a,b) for a,b in pairs if a is not None and b is not None]
   perround.append({'round':r,'paired_texts':len(pairs),'exact_matches':sum(a==b for a,b in pairs),'mean_GPT_minus_Claude':average([a-b for a,b in pairs]),'linear_weighted_kappa':kappa([a for a,b in pairs],[b for a,b in pairs]),'ICC_fixed_models_twoway':REL.icc(pairs) if len(pairs)>1 else None})
  for i in natural:
   a=[value(i['item_id'],'codex',r,d) for r in [1,2,3]];b=[value(i['item_id'],'claude',r,d) for r in [1,2,3]];pairs=[(x,y) for x in a for y in b if x is not None and y is not None]
   cross.append({'item_id':i['item_id'],'available_reused_cross_pairs':len(pairs),'exact_pair_fraction':F(sum(x==y for x,y in pairs),len(pairs)) if pairs else None,'mean_GPT_minus_Claude':average([x-y for x,y in pairs])})
  meanpairs=[]
  for i in natural:
   a=[value(i['item_id'],'codex',r,d) for r in [1,2,3]];b=[value(i['item_id'],'claude',r,d) for r in [1,2,3]]
   if all(x is not None for x in a+b):meanpairs.append([average(a),average(b)])
  output['between_models'][d]={'by_nominal_round':perround,'cross_recall_combinations_per_text':cross,'equal_text_weight_cross_exact':average([r['exact_pair_fraction'] for r in cross if r['exact_pair_fraction'] is not None]),'ICC_on_each_models_3repeat_mean':REL.icc(meanpairs) if len(meanpairs)>1 else None,'complete_texts_for_model_mean_ICC':len(meanpairs),'warning':'fixed two-model comparison, not population of judges;3x3combinations are not9independent raters'}
 agg=[]
 for i in natural:
  row=[]
  for r in [1,2,3]:
   g=value(i['item_id'],'codex',r);c=value(i['item_id'],'claude',r);row.append(F(g+c,2) if g is not None and c is not None else None)
  agg.append(row)
 output['aggregate_repeatability']=matrix_summary(agg)
 #6fixed same-profile/same-stage textual contrasts, registered before first reading.
 for case in ['DEV-M0-01','DEV-M0-02','DEV-M0-03']:
  for stage,base,cand in [('M6','v02','v04'),('M9','none','examples')]:
   a=next(i for i in natural if i['case_id']==case and i['stage']==stage and i['condition']==base);b=next(i for i in natural if i['case_id']==case and i['stage']==stage and i['condition']==cand)
   out={'case_id':case,'stage':stage,'baseline_id':a['item_id'],'candidate_id':b['item_id'],'judges':{}}
   operating=[]
   for i in [a,b]:
    g=[value(i['item_id'],'codex',r) for r in [1,2,3]];c=[value(i['item_id'],'claude',r) for r in [1,2,3]];operating.append([F(x+y,2) for x in g for y in c if x is not None and y is not None])
   for p in PROVIDERS:out['judges'][p]=direction([value(a['item_id'],p,r) for r in [1,2,3]],[value(b['item_id'],p,r) for r in [1,2,3]])
   out['two_model_operating_combinations']=direction(*operating);output['contrasts'].append(out)
 for i in controls:
  row={'control_id':i['item_id'],'parent_id':i['parent_id'],'case_id':i['case_id'],'target_turn':i['perturbation']['turn_id'],'judges':{}}
  for p in PROVIDERS:
   points=[]
   for r in [1,2,3]:
    v=get(i['item_id'],p,r);d=v.get('facets',{}).get('grounding',{});ev=d.get('evidence',[]);target=any(e.get('patient_turn_id')==row['target_turn'] and e.get('valid_quote') for e in ev)
    points.append({'repetition':r,'realism_score':v.get('realism_score'),'grounding_rating':d.get('rating'),'grounding_uncertain':d.get('uncertain'),'target_turn_valid_quote':target,'living_fact_reference':'fact:living' in d.get('context_refs',[]),'clear_grounding_at_target_with_living_ref':d.get('rating')==0 and target and 'fact:living' in d.get('context_refs',[]),'reason':d.get('reason'),'evidence':ev})
   row['judges'][p]={'readings':points,'global_direction':direction([value(i['parent_id'],p,r) for r in [1,2,3]],[value(i['item_id'],p,r) for r in [1,2,3]]),'grounding_direction':direction([value(i['parent_id'],p,r,'grounding') for r in [1,2,3]],[value(i['item_id'],p,r,'grounding') for r in [1,2,3]])}
  output['control_probes'].append(row)
 output['items']=[]
 for i in items:
  row={k:i[k] for k in ['item_id','case_id','kind','stratum','stage','condition','parent_id']};row['judges']={}
  for p in PROVIDERS:row['judges'][p]={'readings':[get(i['item_id'],p,r) for r in [1,2,3]],'global_scores':[value(i['item_id'],p,r) for r in [1,2,3]],'global_mean':average([value(i['item_id'],p,r) for r in [1,2,3]]) if all(value(i['item_id'],p,r) is not None for r in [1,2,3]) else None}
  row['six_rating_mean']=average([value(i['item_id'],p,r) for p in PROVIDERS for r in [1,2,3]]) if all(value(i['item_id'],p,r) is not None for p in PROVIDERS for r in [1,2,3]) else None;output['items'].append(row)
 output['completion']={'expected_responses':90,'recorded_responses':len(records),'valid_primary_scores':sum(v.get('realism_numeric_valid',False) for v in records.values()),'fully_schema_valid_responses':sum(v.get('fully_schema_valid',False) for v in records.values()),'quote_errors':sum(len(v.get('quote_errors',[])) for v in records.values()),'schema_errors':sum(len(v.get('schema_errors',[])) for v in records.values())}
 output['scope']='New integrated single-dialogue fixed-rubric system;3fixed development profiles; no population95CI, no independent raters from repeated draws, no clinical validation, no prior-score pooling or prompt superiority claim'
 return output

def fixtures():
 REL.fixtures();m=read(ROOT/'development/speech-m5-repeatability-v01/scores.json');raw=[r['judges']['claude']['scores'] for r in m['items'] if r['kind']=='original'];a=matrix_summary(raw)
 assert a['ordinal_alpha']['value']==F(5,56) and a['ICC_twoway_sensitivity']['A1']==F(1,6)
 assert a['ICC_primary_exploratory_oneway']['ICC11']==F(1,10) and a['ICC_primary_exploratory_oneway']['ICC1k']==F(1,4)
 assert one_way([[4,4,4]]*3)['ICC11'] is None
 varied_columns=[[4,3,4]]*3
 assert one_way(varied_columns)['ICC11']==F(-1,2)
 assert REL.icc(varied_columns)['A1']==0 and REL.icc(varied_columns)['C1'] is None
 # Independent pairwise-distance ANOVA identity, without row/grand centering.
 n=len(raw);k=len(raw[0]);mu=[average(r) for r in raw]
 wb=sum((F(a)-F(b))**2 for row in raw for a,b in combinations(row,2))/F(n*k*(k-1))
 bb=k*sum((a-b)**2 for a,b in combinations(mu,2))/F(n*(n-1))
 independent=(bb-wb)/(bb+(k-1)*wb)
 assert independent==one_way(raw)['ICC11']
 assert matrix_summary([[4,None,4],[None,3,3]])['numeric_ratings']==4
 assert direction([3,4,4],[3,3,4])['both_directions_observed'] is True
 return {'M5_alpha_and_legacy_twoway_ICC_reproduced':True,'oneway_M5_known_ANOVA_reproduced':True,'constant_and_missing_handling_checked':True,'direction_tie_and_reversal_fixture_checked':True}


def main():
 import argparse
 p=argparse.ArgumentParser();p.add_argument('action',choices=['fixtures','aggregate']);a=p.parse_args()
 if a.action=='fixtures':print(json.dumps(fixtures(),ensure_ascii=False));return
 from experiment import verify
 verify();corpus=read(HERE/'corpus.json');slots=read(HERE/'schedule.json')['slots'];records={}
 for s in slots:
  d=HERE/'reviews'/s['provider']/s['opaque_id'];v=d/'validated.json'
  if v.exists():records[(s['item_id'],s['provider'],s['repetition'])]=read(v)
 result=clean(summarize(corpus,records));(HERE/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
 print(json.dumps({'completion':result['completion'],'global':{p:result['within_models'][p]['realism'] for p in PROVIDERS}},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
