"""Prespecified descriptive discrimination summaries. No score rewriting or model calls."""
from pathlib import Path
from fractions import Fraction as F
from collections import Counter
from itertools import product
import importlib.util, json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('m12stats',ROOT/'development/rater-reliability-m12-v01/analysis_stats.py')
M12=importlib.util.module_from_spec(spec);spec.loader.exec_module(M12)
PROVIDERS=('codex','claude');CONDITIONS=('R','I','F1','F2','N1','N2')
FACETS=('grounding','responsiveness','continuity','naturalness')
def read(p):return json.loads(p.read_text())
def avg(xs):return sum(map(F,xs))/len(xs) if xs else None
def scores_summary(values):
    good=[v for v in values if v is not None]
    return {'scores':values,'valid':len(good),'mean':avg(good) if len(good)==3 else None,
            'counts':{str(k):good.count(k) for k in [1,2,3,4]},'range':max(good)-min(good) if good else None}

def contrast(a,b):
    d=M12.direction(a,b);lo=d['candidate_lower'];hi=d['candidate_higher'];eq=d['tie']
    if any(v is None for v in a+b):label='incomplete'
    elif lo==len(a)*len(b):label='complete_separation_expected_lower'
    elif hi==len(a)*len(b):label='complete_separation_reversed_higher'
    elif eq==len(a)*len(b):label='all_tie'
    elif lo and hi:label='overlap_both_directions'
    elif lo:label='expected_lower_or_tie'
    else:label='reversed_higher_or_tie'
    return dict(d,descriptive_class=label)

def ordered_triplet(a,b,c):
    combinations=[x for x in product(a,b,c) if all(v is not None for v in x)]
    return {'reused_combinations':len(combinations),'nonincreasing':sum(x>=y>=z for x,y,z in combinations),
            'strictly_decreasing':sum(x>y>z for x,y,z in combinations),
            'all_three_tie':sum(x==y==z for x,y,z in combinations),
            'any_reversed_step':sum(x<y or y<z for x,y,z in combinations),
            'warning':'At most27combinations reuse9ratings;not27independenttrials;tiesnotfine-discriminationevidence'}

def marker_quote(record,condition,facet):
    f=record.get('facets',{}).get(facet,{});markers={'F1':['3층'],'F2':['혼자','같이 사는 사람은 없'],
          'N1':['거주 형태','공동 거주'],'N2':['환자','설정'],'I':[],'R':[]}[condition]
    ev=f.get('evidence',[])
    target=any(e.get('patient_turn_id')=='P02' and e.get('valid_quote') for e in ev)
    changed=any(e.get('patient_turn_id')=='P02' and e.get('valid_quote') and
                any(marker in (e.get('quote') or '') for marker in markers) for e in ev)
    return {'numeric_rating':f.get('rating'),'uncertain':f.get('uncertain'),
            'target_turn_exact_quote':target,'changed_marker_exact_quote':changed,
            'living_fact_reference':'fact:living' in f.get('context_refs',[]),
            'mechanical_target_finding':f.get('rating') in [0,1] and changed,
            'reason':f.get('reason'),'evidence':ev,'context_refs':f.get('context_refs',[]),
            'warning':'Mechanical marker evidence,not independent semantic/clinical adjudication. No quote can mean no reported finding,not proven nonrecognition.'}

def summarize(corpus,records):
    items=corpus['items'];by={(i['case_id'],i['condition']):i for i in items};cases=sorted({i['case_id'] for i in items})
    def record(case,cond,p,r):return records.get((by[(case,cond)]['item_id'],p,r),{})
    def vals(case,cond,p,facet='realism'):
        rs=[record(case,cond,p,r) for r in [1,2,3]]
        return [v.get('realism_score') if facet=='realism' else v.get('facets',{}).get(facet,{}).get('rating') for v in rs]
    result={'profiles':3,'texts':18,'planned_responses':108,'items':[],'contrasts':[],'ordered_families':[],
            'repeatability':{},'target_findings':[],'detection_total_cross':[],'condition_means':{},'completion':{}}
    for item in items:
        case=item['case_id'];cond=item['condition'];judges={}
        for p in PROVIDERS:
            v=vals(case,cond,p)
            judges[p]={**scores_summary(v),'facets':{f:vals(case,cond,p,f) for f in FACETS},
                       'readings':[record(case,cond,p,r) for r in [1,2,3]]}
        allvalues=[v for p in PROVIDERS for v in vals(case,cond,p)]
        result['items'].append({k:item[k] for k in ['item_id','case_id','condition','kind','family','parent_id','target_characters','target_eojeol','patient_characters']}|
            {'judges':judges,'six_score_mean':avg(allvalues) if all(v is not None for v in allvalues) else None})
    for p in PROVIDERS:
        result['condition_means'][p]={cond:avg([v for case in cases for v in vals(case,cond,p)])
            if all(v is not None for case in cases for v in vals(case,cond,p)) else None for cond in CONDITIONS}
        result['repeatability'][p]={}
        for facet in ['realism',*FACETS]:
            matrix=[vals(i['case_id'],i['condition'],p,facet) for i in items]
            result['repeatability'][p][facet]={'all_conditions':M12.matrix_summary(matrix),
                'by_condition':{cond:M12.matrix_summary([vals(case,cond,p,facet) for case in cases]) for cond in CONDITIONS},
                'interpretation':'Within-condition3texts is tiny; pooled coefficient includes intentionally broad manipulated between-text spread,not improvement overM12.'}
    result['condition_means']['two_model_mean']={cond:avg([result['condition_means'][p][cond] for p in PROVIDERS])
         if all(result['condition_means'][p][cond] is not None for p in PROVIDERS) else None for cond in CONDITIONS}
    for case in cases:
        # All reference/invariance contrasts plus the two prespecified adjacent steps.
        pairs=[('R',c) for c in CONDITIONS if c!='R']+[('I',c) for c in ['F1','F2','N1','N2']]+[('F1','F2'),('N1','N2')]
        for a,b in pairs:
            row={'case_id':case,'baseline':a,'candidate':b,'judges':{}}
            for p in PROVIDERS:
                row['judges'][p]={f:contrast(vals(case,a,p,f),vals(case,b,p,f)) for f in ['realism',*FACETS]}
            result['contrasts'].append(row)
        for family,conditions in [('fact',['R','F1','F2']),('expression',['R','N1','N2'])]:
            result['ordered_families'].append({'case_id':case,'family':family,'conditions':conditions,
                 'judges':{p:ordered_triplet(*(vals(case,c,p) for c in conditions)) for p in PROVIDERS}})
        for cond in ['F1','F2','N1','N2']:
            facet='grounding' if cond.startswith('F') else 'naturalness'
            row={'case_id':case,'condition':cond,'target_facet':facet,'judges':{}}
            for p in PROVIDERS:
                readings=[marker_quote(record(case,cond,p,r),cond,facet) for r in [1,2,3]]
                row['judges'][p]={'readings':readings,'mechanical_target_findings':sum(v['mechanical_target_finding'] for v in readings)}
                cross=Counter()
                for r,reading in enumerate(readings,1):
                    source=record(case,'R',p,r);v=record(case,cond,p,r);a=source.get('realism_score');b=v.get('realism_score')
                    lowered=b<a if a is not None and b is not None else None
                    facet_source=source.get('facets',{}).get(facet,{}).get('rating');facet_control=reading['numeric_rating']
                    moved=facet_control<facet_source if facet_control is not None and facet_source is not None else None
                    cross[f'target_marker_finding={reading["mechanical_target_finding"]};total_lower={lowered};facet_lower={moved}']+=1
                result['detection_total_cross'].append({'case_id':case,'condition':cond,'provider':p,'cells':dict(cross),
                     'pairing':'same nominal recall round fordescriptiononly;notmatchedseed orindependentclinicalcoding'})
            result['target_findings'].append(row)
    result['completion']={'expected_responses':108,'recorded_responses':len(records),
       'valid_primary_scores':sum(v.get('realism_numeric_valid',False) for v in records.values()),
       'fully_schema_valid_responses':sum(v.get('fully_schema_valid',False) for v in records.values()),
       'quote_errors':sum(len(v.get('quote_errors',[])) for v in records.values()),
       'schema_errors':sum(len(v.get('schema_errors',[])) for v in records.values())}
    result['scope']='Three new fixed synthetic development profiles,author-defined manipulations and ranks; no independent clinicalgold/populationCI/pvalue/promptimprovementclaim. Model-level disagreementnotitself failure.'
    return result

def fixtures():
    assert contrast([4,4,4],[3,3,3])['descriptive_class']=='complete_separation_expected_lower'
    assert contrast([4,4,4],[4,4,4])['descriptive_class']=='all_tie'
    assert contrast([3,4,4],[3,3,4])['descriptive_class']=='overlap_both_directions'
    assert contrast([3,None,4],[3,3,4])['descriptive_class']=='incomplete'
    o=ordered_triplet([4]*3,[4]*3,[3]*3);assert o['nonincreasing']==27 and o['strictly_decreasing']==0
    assert M12.matrix_summary([[4,4,4]]*3)['ordinal_alpha']['value'] is None
    assert not marker_quote({'facets':{'grounding':{'rating':0,'evidence':[{'patient_turn_id':'P02','quote':'남편과','valid_quote':True}]}}},'F1','grounding')['mechanical_target_finding']
    return {'ordinal_direction_ties_and_reversal':True,'missingness_preserved':True,'non_strict_vs_strict_order_distinguished':True,'constant_reliability_not_one':True,'target_quote_requires_changed_marker':True}

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('action',choices=['aggregate','fixtures']);a=p.parse_args()
    if a.action=='fixtures':print(json.dumps(fixtures()));return
    from experiment import verify
    verify();corpus=read(HERE/'corpus.json');records={}
    for s in read(HERE/'schedule.json')['slots']:
        p=HERE/'reviews'/s['provider']/s['opaque_id']/'validated.json'
        if p.exists():records[(s['item_id'],s['provider'],s['repetition'])]=read(p)
    value=M12.clean(summarize(corpus,records));(HERE/'results.json').write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'completion':value['completion'],'condition_means':value['condition_means']},ensure_ascii=False))
if __name__=='__main__':main()
