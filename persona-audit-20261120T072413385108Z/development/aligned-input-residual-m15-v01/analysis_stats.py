"""M15 deterministic score/issue aggregation. Source texts and attribution stay separate."""
from pathlib import Path
from fractions import Fraction as F
from collections import Counter,defaultdict
from itertools import combinations
from math import sqrt
import importlib.util,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('m12stat',ROOT/'development/rater-reliability-m12-v01/analysis_stats.py')
M12=importlib.util.module_from_spec(spec);spec.loader.exec_module(M12)
PROVIDERS=('codex','claude');FACETS=('grounding','responsiveness','continuity','naturalness')
def read(p):return json.loads(p.read_text())
def avg(v):return sum(map(F,v))/len(v) if v else None
def complete_mean(v):return avg(v) if v and all(x is not None for x in v) else None
def distribution(v):return dict(Counter(str(x) for x in v if x is not None))
def generation_summary(v):
    good=[x for x in v if x is not None];mu=complete_mean(v)
    return {'generation_means':v,'complete_generations':len(good),'mean':mu,'sample_SD_of_generation_means':sqrt(float(sum((F(x)-avg(good))**2 for x in good)/F(len(good)-1))) if len(good)>1 else None,
            'min':min(good) if good else None,'max':max(good) if good else None,'warning':'3generationmeanstechnicaldescription;containsresidualjudgevariation;notpuregenerationvarianceorindependentprofiles'}

def summarize(corpus,records):
    items=corpus['items'];cases=sorted({i['case_id'] for i in items})
    def reading(i,p,r):return records.get((i['item_id'],p,r),{})
    def values(i,p,f='realism'):
        rs=[reading(i,p,r) for r in [1,2,3]]
        return [x.get('realism_score') if f=='realism' else x.get('facets',{}).get(f,{}).get('rating') for x in rs]
    out={'profiles':3,'planned_dialogues':9,'planned_judge_responses':54,'items':[],'model_means':{},
         'per_profile':{},'repeatability':{},'facet_distributions':{},'reported_locations':[],
         'operational_mean_repeatability':None,'completion':{}}
    for i in items:
        row={k:i[k] for k in ['item_id','case_id','generation_replicate','source_path']};row['judges']={}
        for p in PROVIDERS:
            vs=values(i,p)
            row['judges'][p]={'scores':vs,'mean':complete_mean(vs),'score_distribution':distribution(vs),
                 'facets':{f:values(i,p,f) for f in FACETS},'readings':[reading(i,p,r) for r in [1,2,3]]}
        row['six_rating_mean']=complete_mean([v for p in PROVIDERS for v in values(i,p)])
        out['items'].append(row)
    byid={i['item_id']:i for i in out['items']}
    for p in PROVIDERS:
        out['model_means'][p]=complete_mean([byid[i['item_id']]['judges'][p]['mean'] for i in items])
        out['repeatability'][p]={f:M12.matrix_summary([values(i,p,f) for i in items]) for f in ['realism',*FACETS]}
        out['facet_distributions'][p]={}
        for f in FACETS:
            ds=[reading(i,p,r).get('facets',{}).get(f,{}) for i in items for r in [1,2,3]]
            out['facet_distributions'][p][f]={'numeric_counts':distribution([d.get('rating') for d in ds]),
                 'uncertain_true':sum(d.get('uncertain') is True for d in ds),'semantic_NA':sum(d.get('semantic_NA',False) for d in ds),
                 'technical_missing':sum(not d.get('numeric_valid',False) and not d.get('semantic_NA',False) for d in ds)}
    out['model_means']['two_model_mean']=complete_mean([i['six_rating_mean'] for i in out['items']])
    for case in cases:
        selected=sorted([i for i in items if i['case_id']==case],key=lambda x:x['generation_replicate'])
        out['per_profile'][case]={p:generation_summary([byid[i['item_id']]['judges'][p]['mean'] for i in selected]) for p in PROVIDERS}
        out['per_profile'][case]['two_model_mean']=generation_summary([byid[i['item_id']]['six_rating_mean'] for i in selected])
        out['per_profile'][case]['unique_exact_patient_answer_sequences']=len({tuple(t['text'] for t in i['payload']['dialogue'] if t['speaker']=='patient') for i in selected})
    matrix=[]
    for i in items:
        row=[]
        for r in [1,2,3]:
            a=reading(i,'codex',r).get('realism_score');b=reading(i,'claude',r).get('realism_score')
            row.append(F(a+b,2) if a is not None and b is not None else None)
        matrix.append(row)
    out['operational_mean_repeatability']=M12.matrix_summary(matrix)
    locations=defaultdict(list)
    for i in items:
        for p in PROVIDERS:
            for r in [1,2,3]:
                for f,d in reading(i,p,r).get('facets',{}).items():
                    if d.get('rating') not in [0,1] and d.get('uncertain') is not True:continue
                    byturn=defaultdict(list)
                    for ev in d.get('evidence',[]):
                        if ev.get('valid_quote'):byturn[ev['patient_turn_id']].append(ev['quote'])
                    for turn,quotes in byturn.items():
                        locations[(i['item_id'],i['case_id'],p,f,turn)].append({'repetition':r,'rating':d.get('rating'),
                             'uncertain':d.get('uncertain'),'reason':d.get('reason'),'quotes':quotes,'context_refs':d.get('context_refs',[])})
    for (item,case,p,f,turn),rs in sorted(locations.items()):
        out['reported_locations'].append({'item_id':item,'case_id':case,'provider':p,'facet':f,'patient_turn_id':turn,
             'readings_with_location':len(rs),'confirmed_problem_readings':sum(x['rating'] in [0,1] for x in rs),
             'uncertain_readings':sum(x['uncertain'] is True for x in rs),'readings':rs,
             'warning':'Sameeventcanappearinmultiplefacets/models;notindependenterrorcountorclinicaladjudication'})
    out['completion']={'expected_responses':54,'recorded_responses':len(records),
         'valid_primary_scores':sum(v.get('realism_numeric_valid',False) for v in records.values()),
         'fully_schema_valid_responses':sum(v.get('fully_schema_valid',False) for v in records.values()),
         'quote_errors':sum(len(v.get('quote_errors',[])) for v in records.values()),
         'schema_errors':sum(len(v.get('schema_errors',[])) for v in records.values())}
    out['scope']='Alignedsinglearmgeneration;M13developmentprofilesreused;no causalinputalignment/promptimprovementeffect,no clinicalgold,populationCI,posthocscoreexclusionornewscale.'
    return out

def fixtures():
    assert complete_mean([4,None,4]) is None
    assert complete_mean([4,3,4])==F(11,3)
    assert generation_summary([F(7,2),F(7,2),F(7,2)])['sample_SD_of_generation_means']==0
    m=M12.matrix_summary([[4,4,4]]*3);assert m['ordinal_alpha']['value'] is None
    m=M12.matrix_summary([[4,3,4],[3,3,3],[4,4,4]]);assert m['exact_numeric_pair_matches']==7 and m['numeric_pair_count']==9
    return {'missing_means_not_imputed':True,'generation_and_rater_variation_separate':True,'constant_alpha_not_one':True,'dependent_repeat_pairs_fixture':True}

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('action',choices=['aggregate','fixtures']);a=p.parse_args()
    if a.action=='fixtures':print(json.dumps(fixtures()));return
    from experiment import verify
    verify();corpus=read(HERE/'corpus.json');records={}
    for s in read(HERE/'schedule.json')['slots']:
        f=HERE/'reviews'/s['provider']/s['opaque_id']/'validated.json'
        if f.exists():records[(s['item_id'],s['provider'],s['repetition'])]=read(f)
    value=M12.clean(summarize(corpus,records));(HERE/'results.json').write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'completion':value['completion'],'model_means':value['model_means']},ensure_ascii=False))
if __name__=='__main__':main()
