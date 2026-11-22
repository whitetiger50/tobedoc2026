"""Descriptive reanalysis only: no model calls, no inferred reliability threshold."""
from pathlib import Path
from collections import Counter
import json,statistics,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def read(p):return json.loads(p.read_text())
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
rows=[];sources={}
for stage in [3,4,6,7,8,9]:
 p=next((ROOT/'development').glob(f'speech-m{stage}-*/scores.json'));s=read(p);sources[str(p.relative_to(ROOT))]=sha(p)
 if stage in [3,4]:
  items=[{'item_id':c['case_id']+'-'+v,'condition':v,'scores':r['original_scores']} for c in s['cases'] for v,r in c.items() if v.startswith('v0')]
 else:items=s['items']
 by={}
 for cond in sorted({r['condition'] for r in items}):
  selected=[r for r in items if r['condition']==cond];n=len(selected)
  by[cond]={'dialogues':n,'score_counts':{j:dict(Counter(str(r['scores'][j]) for r in selected)) for j in ['codex','claude']},'GPT_minus_Claude_values':[r['scores']['codex']-r['scores']['claude'] for r in selected],'exact_between_judge_agreement':sum(r['scores']['codex']==r['scores']['claude'] for r in selected),'one_integer_rating_point_effect_on_condition_mean':1/(2*n)}
 rows.append({'stage':stage,'conditions':by})
m5=read(ROOT/'development/speech-m5-repeatability-v01/scores.json');sources['development/speech-m5-repeatability-v01/scores.json']=sha(ROOT/'development/speech-m5-repeatability-v01/scores.json')
originals=[r for r in m5['items'] if r['kind']=='original'];repeat={}
for judge in ['codex','claude']:
 values=[r['judges'][judge]['scores'] for r in originals]
 pairs=[abs(v[a]-v[b]) for v in values for a,b in [(0,1),(0,2),(1,2)]]
 repeat[judge]={'original_dialogues':6,'underlying_profiles':3,'ratings':18,'all_three_equal_dialogues':sum(len(set(v))==1 for v in values),'equal_pairs':sum(x==0 for x in pairs),'all_pairs':18,'mean_absolute_within_text_pair_difference':statistics.mean(pairs),'max_within_text_pair_difference':max(pairs),'scores':values,'warning':'18pairs are dependent comparisons within6texts/3profiles, not18independent samples; not a calibrated uncertainty interval'}
contrasts=[]
for n in range(3):
 means={v:statistics.mean(r['judges'][j]['scores'][n] for r in originals if r['condition']==v for j in ['codex','claude']) for v in ['v02','v04']}
 contrasts.append({'round':n+1,'means':means,'v04_minus_v02':means['v04']-means['v02']})
out={'kind':'existing_evidence_descriptive_measurement_audit_no_new_ratings','within_judge_fixed_text_M5':repeat,'same_fixed_text_M5_round_contrasts':contrasts,'between_judge_distribution_and_arithmetic_leverage_by_stage':rows,'warning':'Different stages use different generated texts and sometimes questions/reviewtasks/batches. Do not treat stage mean differences as repeated ratings of identical texts. Arithmetic leverage is not measurement error, detection threshold or clinical significance. Stable top scores can coexist with weak discrimination. No pvalues/CI/ICC/kappa calculated on these tiny/degenerate samples.','source_sha256':sources}
dump(HERE/'measurement-audit.json',out)
print('Recomputed M5 original pair agreement: GPT',repeat['codex']['equal_pairs'],'/18; Claude',repeat['claude']['equal_pairs'],'/18')
print('Fixed-text contrasts',[r['v04_minus_v02'] for r in contrasts]);print('No new patient outputs or numeric ratings')
