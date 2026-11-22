"""Existing fixed-text rating statistics, pure stdlib; no new model calls."""
from collections import Counter
from fractions import Fraction as F
from itertools import combinations
from math import sqrt
from pathlib import Path
import json,hashlib
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]

def serial(x):
 if isinstance(x,F):return float(x)
 if isinstance(x,dict):return {str(k):serial(v) for k,v in x.items()}
 if isinstance(x,(list,tuple)):return [serial(v) for v in x]
 return x

def ordinal_alpha(units):
 units=[[v for v in row if v is not None] for row in units];units=[row for row in units if len(row)>1]
 counts=Counter(v for row in units for v in row);n=sum(counts.values());cats=sorted(counts)
 def d(a,b):
  if a==b:return F(0)
  lo,hi=sorted([a,b]);return (sum(F(counts[c]) for c in cats if lo<=c<=hi)-F(counts[lo]+counts[hi],2))**2
 if n<2:return {'value':None,'reason':'fewer_than_two_pairable_ratings'}
 do=sum((sum(d(a,b) for i,a in enumerate(row) for j,b in enumerate(row) if i!=j)/F(len(row)-1)) for row in units)/n
 de=sum(F(counts[a]*counts[b])*d(a,b) for a in cats for b in cats)/F(n*(n-1))
 return {'value':1-do/de if de else None,'reason':None if de else 'expected_disagreement_zero_constant_scores','observed_disagreement':do,'expected_disagreement':de,'pairable_ratings':n,'category_counts':dict(counts)}

def weighted_kappa(a,b,power=1):
 assert len(a)==len(b)>0;n=len(a);ca=Counter(a);cb=Counter(b)
 do=sum(F(abs(x-y)**power) for x,y in zip(a,b))/n
 de=sum(F(nx*ny*abs(x-y)**power) for x,nx in ca.items() for y,ny in cb.items())/F(n*n)
 return {'value':1-do/de if de else None,'reason':None if de else 'expected_disagreement_zero_constant_scores','weight':'linear' if power==1 else 'quadratic','observed_disagreement':do,'expected_disagreement':de}

def icc(matrix):
 n=len(matrix);k=len(matrix[0]);assert n>1 and k>1 and all(len(row)==k for row in matrix)
 x=[[F(v) for v in row] for row in matrix];grand=sum(sum(row) for row in x)/F(n*k)
 rows=[sum(row)/k for row in x];cols=[sum(x[i][j] for i in range(n))/n for j in range(k)]
 ssr=k*sum((v-grand)**2 for v in rows);ssc=n*sum((v-grand)**2 for v in cols)
 sse=sum((x[i][j]-rows[i]-cols[j]+grand)**2 for i in range(n) for j in range(k))
 msr=ssr/F(n-1);msc=ssc/F(k-1);mse=sse/F((n-1)*(k-1));num=msr-mse
 den={'A1':msr+(k-1)*mse+F(k,n)*(msc-mse),'Ak':msr+(msc-mse)/n,'C1':msr+(k-1)*mse,'Ck':msr}
 return {'A1':num/den['A1'] if den['A1'] else None,'Ak':num/den['Ak'] if den['Ak'] else None,'C1':num/den['C1'] if den['C1'] else None,'Ck':num/den['Ck'] if den['Ck'] else None,'k':k,'n':n,'MS_rows':msr,'MS_columns':msc,'MS_residual':mse,'undefined_forms':[v for v,d in den.items() if not d],'interpretation':'ANOVA two-way mixed fixed-column, absolute agreement(A)/consistency(C), single(1)/average(k); exploratory equal-interval score assumption; columns are observed repeat rounds or fixed panel models, not random clinical raters'}

def within(matrix):
 pairs=[(a,b) for row in matrix for a,b in combinations(row,2)];n=len(matrix);k=len(matrix[0])
 pooled_variance=sum(sum((F(v)-sum(map(F,row))/k)**2 for v in row) for row in matrix)/F(n*(k-1))
 return {'dialogues':n,'repeats':k,'underlying_profiles':3,'pooled_within_text_variance':pooled_variance,'pooled_within_text_SD':sqrt(float(pooled_variance)),'exact_pair_agreement':F(sum(a==b for a,b in pairs),len(pairs)),'exact_pair_matches':sum(a==b for a,b in pairs),'pair_count':len(pairs),'all_repeats_equal_dialogues':sum(len(set(row))==1 for row in matrix),'mean_absolute_within_text_pair_difference':sum(F(abs(a-b)) for a,b in pairs)/len(pairs),'ordinal_alpha':ordinal_alpha(matrix),'weighted_kappa_by_round_pair':[{'rounds':[i+1,j+1],**weighted_kappa([r[i] for r in matrix],[r[j] for r in matrix])} for i,j in combinations(range(k),2)],'ICC_exploratory':icc(matrix),'raw_matrix':matrix}

def fixtures():
 # Original author's binary worked example, Krippendorff2011/2013, pp2-3.
 a=[0,1,0,0,0,0,0,0,1,0];b=[1,1,0,0,0,1,0,0,0,1]
 assert ordinal_alpha(list(map(list,zip(a,b))))['value']==F(2,21)
 # Varying identical ratings and zero-variation degeneracy.
 assert ordinal_alpha([[1,1,1],[2,2,2],[4,4,4]])['value']==1
 assert ordinal_alpha([[4,4,4]]*3)['value'] is None
 assert weighted_kappa([1,2,4],[1,2,4])['value']==1
 assert weighted_kappa([4,4,4],[4,4,4])['value'] is None
 assert weighted_kappa([4,4,4],[3,4,4])['value']==0
 # Analytically known fixed+1 column shift: consistency1, absolute agreement2/3.
 v=icc([[1,2],[2,3],[3,4]]);assert v['C1']==1 and v['A1']==F(2,3) and v['Ak']==F(4,5)
 assert all(icc([[4,4]]*3)[f] is None for f in ['A1','Ak','C1','Ck'])
 return {'public_author_binary_example_passed':True,'perfect_varying_and_constant_degeneracy_passed':True,'known_additive_bias_ICC_fixture_passed':True,'weighted_kappa_constant_margin_fixtures_passed':True}

def main():
 tests=fixtures();source=ROOT/'development/speech-m5-repeatability-v01/scores.json';old=json.loads(source.read_text());items=[r for r in old['items'] if r['kind']=='original']
 by={p:within([r['judges'][p]['scores'] for r in items]) for p in ['codex','claude']}
 assert by['claude']['ordinal_alpha']['value']==F(5,56)
 assert by['claude']['ICC_exploratory']['A1']==F(1,6)
 aggregate_matrix=[[F(row['judges']['codex']['scores'][r]+row['judges']['claude']['scores'][r],2) for r in range(3)] for row in items]
 aggregate=within(aggregate_matrix)
 assert aggregate['ICC_exploratory']['A1']==by['claude']['ICC_exploratory']['A1']
 rounds=[]
 for r in range(3):
  matrix=[[row['judges'][p]['scores'][r] for p in ['codex','claude']] for row in items]
  a=[v[0] for v in matrix];b=[v[1] for v in matrix]
  rounds.append({'round':r+1,'exact_agreement':F(sum(x==y for x,y in matrix),len(matrix)),'mean_GPT_minus_Claude':sum(F(x-y) for x,y in matrix)/len(matrix),'linear_weighted_kappa':weighted_kappa(a,b),'ordinal_alpha':ordinal_alpha(matrix),'ICC_exploratory':icc(matrix)})
 m8=ROOT/'development/speech-m8-stress-grounding-v01/scores.json';s8=json.loads(m8.read_text());x=[[r['scores'][p] for p in ['codex','claude']] for r in s8['items']]
 out={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'kind':'existing_fixed_text_reliability_point_estimates_not_validation','source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,m8]},'formula_sources':{'ordinal_alpha':'https://www.asc.upenn.edu/sites/default/files/2021-03/Computing%20Krippendorff%27s%20Alpha-Reliability.pdf','ICC':'https://pmc.ncbi.nlm.nih.gov/articles/PMC4913118/','ICC_erratum':'https://pmc.ncbi.nlm.nih.gov/articles/PMC5731844/','weighted_kappa_reference':'https://www.statsmodels.org/stable/generated/statsmodels.stats.inter_rater.cohens_kappa.html'},'M5_originals_only':{'item_ids':[r['item_id'] for r in items],'within_model':by,'two_model_arithmetic_mean_repeatability':aggregate,'between_models_by_round':rounds},'M8_fixed_panel_only':{'dialogues':len(x),'profiles':3,'exact_agreement':F(sum(a==b for a,b in x),len(x)),'linear_weighted_kappa':weighted_kappa([a for a,b in x],[b for a,b in x]),'ordinal_alpha':ordinal_alpha(x),'ICC_exploratory':icc(x)},'checks':tests,'confidence_intervals':'not_reported:6reusedtexts from3profiles and constant margins; a point estimate can be computed but stable generalizable precision is not established. No naive independent18pair CI. Future analysis must handle profile clustering and item/rater/repeat structure.','limits':['Posthoc estimates on M5 original6texts,3profiles,ratings concentrated3/4; no population pass/fail claim.','Same9item packet included obvious family substitutions; no isolated-presentation generalization.','Kappa/alpha chance models differ; not interchangeable, constant or narrow-range margins strongly affect values.','ICC treats integer1-4scores as equally spaced; secondary sensitivity analysis rather than sole primary ordinal reliability metric.','Natural and manipulated controls must not be pooled to inflate between-item variation and reliability.','Repeated-rating reliability does not establish clinical validity or sensitivity to subtle changes.','No new utterances, model calls, ratings, external APIs, packages or final720 execution.']}
 (HERE/'results.json').write_text(json.dumps(serial(out),ensure_ascii=False,indent=2)+'\n')
 print('M5 within-model exploratory points')
 for p,r in by.items():print(p,'exact',float(r['exact_pair_agreement']),'ordinalAlpha',serial(r['ordinal_alpha']['value']),'ICC(A,1)',serial(r['ICC_exploratory']['A1']),'ICC(A,3)',serial(r['ICC_exploratory']['Ak']))
 print('Two-model mean ICC(A,1)',serial(aggregate['ICC_exploratory']['A1']),'within-text SD',aggregate['pooled_within_text_SD'])
 print('M8 between models:',serial(out['M8_fixed_panel_only']));print('Fixtures passed',tests)
if __name__=='__main__':main()
