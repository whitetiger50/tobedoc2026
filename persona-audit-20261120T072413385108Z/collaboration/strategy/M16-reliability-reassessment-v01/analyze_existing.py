"""Post-hoc diagnostic reanalysis of existing ratings only; never calls a model."""
from pathlib import Path
from itertools import combinations
from datetime import datetime,timezone
import importlib.util,json,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('m12stats',ROOT/'development/rater-reliability-m12-v01/analysis_stats.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

def main():
    # HERE=ROOT/collaboration/strategy/M16, hence parents[2] is project root.
    sources={k:ROOT/f'development/{v}/results.json' for k,v in {
         'M12':'rater-reliability-m12-v01','M13':'graded-discrimination-m13-v01','M15':'aligned-input-residual-m15-v01'}.items()}
    data={k:read(p) for k,p in sources.items()};rows=[]
    def summary(label,matrix,scope):
        s=M.clean(M.matrix_summary(matrix));rows.append({'group':label,'scope':scope,'matrix':matrix,'statistics':s})
    m12=data['M12']
    for label,key in [('M12_natural_all',None),('M12_natural_4turn','four_turn'),('M12_natural_8turn','eight_turn')]:
        items=[i for i in m12['items'] if i['kind']=='natural' and (key is None or i['stratum']==key)]
        summary(label,[i['judges']['claude']['global_scores'] for i in items],'M12prespecifiednaturalstratum;3reusedoldprofiles')
    m13=data['M13']
    for label,conds in [('M13_all',['R','I','F1','F2','N1','N2']),('M13_generated_R_only',['R']),
                         ('M13_R_plus_authored_meaning_preserving_I',['R','I']),('M13_authored_graded_controls_only',['F1','F2','N1','N2'])]:
        items=[i for i in m13['items'] if i['condition'] in conds]
        summary(label,[i['judges']['claude']['scores'] for i in items],'M16post-hocdiagnosticstratum;Iis authored,notnaturalmodeloutput;notnewpreregisteredendpoint')
    m15=data['M15'];summary('M15_natural_all',[i['judges']['claude']['scores'] for i in m15['items']],'M15all9generatedtextsfrom3profiles;3independentgenerationstarts/profile')
    variable=[i for i in m15['items'] if len(set(i['judges']['claude']['scores']))>1]
    assert len(variable)==3
    comparisons=[]
    for a,b in combinations(variable,2):
        x=a['judges']['claude']['scores'];y=b['judges']['claude']['scores'];d=[j-i for i,j in zip(x,y)]
        comparisons.append({'baseline':a['item_id'],'candidate':b['item_id'],'candidate_minus_baseline_by_nominal_round':d,
             'both_strict_directions_observed':any(v<0 for v in d) and any(v>0 for v in d),
             'warning':'Post-hocselectedvariabletexts;nominalroundnotsharedseed;reuses9existingreadings,notindependentreversaltrials'})
    assert all(r['both_strict_directions_observed'] for r in comparisons)
    roundmeans=[]
    for r in range(3):
        values=[i['judges']['claude']['scores'][r] for i in m15['items']]
        roundmeans.append({'nominal_round':r+1,'sum':sum(values),'n':len(values),'mean':sum(values)/len(values),
             'score3':values.count(3),'score4':values.count(4)})
    assert all(v['sum']==30 and v['score4']==3 for v in roundmeans)
    rawrole=ROOT/'development/aligned-input-residual-m15-v01/review-role.txt';schedule=read(ROOT/'development/aligned-input-residual-m15-v01/schedule.json')['slots']
    technical=[];itemhashes={};versions=set();efforts=set();models=set()
    for s in schedule:
        if s['provider']!='claude':continue
        p=ROOT/'development/aligned-input-residual-m15-v01/reviews/claude'/s['opaque_id'];meta=read(p/'metadata.json')
        assert meta['status']=='response_received' and meta['automatic_retries']==0
        assert sha(p/'input.txt')==meta['input_sha256']
        assert sha(p/'instructions.txt')==meta['instructions_sha256']==sha(rawrole)
        itemhashes.setdefault(s['item_id'],[]).append(meta['input_sha256']);versions.add(meta['cli_version']);efforts.add(meta['settings']['reasoning_effort']);models.add(meta['requested_model'])
        cmd=read(p/'command.json')['argv'];assert '--safe-mode' in cmd and '--no-session-persistence' in cmd and cmd[cmd.index('--tools')+1]==''
        assert set(meta['reported_model_usage'])=={'claude-opus-5-5'}
        technical.append({'slot_id':s['slot_id'],'item_id':s['item_id'],'round':s['repetition'],'timestamp_utc':meta['timestamp_utc'],
             'input_sha256':meta['input_sha256'],'role_sha256':meta['instructions_sha256'],'response_sha256':meta['response_sha256']})
    assert len(technical)==27 and all(len(v)==3 and len(set(v))==1 for v in itemhashes.values())
    # Algebraic decomposition, not a causal experiment on the source mixture.
    group={r['group']:r['statistics'] for r in rows};all13=group['M13_all'];r13=group['M13_generated_R_only'];i13=group['M13_R_plus_authored_meaning_preserving_I'];ctrl=group['M13_authored_graded_controls_only'];all15=group['M15_natural_all']
    assert (all13['exact_numeric_pair_matches'],all13['numeric_pair_count'])==(50,54)
    assert (r13['exact_numeric_pair_matches'],r13['numeric_pair_count'])==(7,9)
    assert (i13['exact_numeric_pair_matches'],i13['numeric_pair_count'])==(14,18)
    assert (ctrl['exact_numeric_pair_matches'],ctrl['numeric_pair_count'])==(36,36)
    assert (all15['exact_numeric_pair_matches'],all15['numeric_pair_count'])==(21,27)
    assert all13['exact_numeric_pair_matches']==i13['exact_numeric_pair_matches']+ctrl['exact_numeric_pair_matches']
    corpus=read(ROOT/'development/aligned-input-residual-m15-v01/corpus.json');payload={i['item_id']:i['payload'] for i in corpus['items']}
    excerpts=[]
    for i in variable:
        excerpts.append({'item_id':i['item_id'],'case_id':i['case_id'],'payload':payload[i['item_id']],
             'three_actual_Claude_readings':i['judges']['claude']['readings'],'three_GPT_scores':i['judges']['codex']['scores']})
    stablecase=[i for i in m15['items'] if i['case_id']=='DEV-M13-02']
    stable=[]
    for i in stablecase:
        stable.append({'item_id':i['item_id'],'scores':i['judges']['claude']['scores'],
             'P01':next(t['text'] for t in payload[i['item_id']]['dialogue'] if t['turn_id']=='P01'),
             'D08':next(t['text'] for t in payload[i['item_id']]['dialogue'] if t['turn_id']=='D08'),
             'P08':next(t['text'] for t in payload[i['item_id']]['dialogue'] if t['turn_id']=='P08'),
             'existing_naturalness':[r['facets']['naturalness'] for r in i['judges']['claude']['readings']]})
    dump(HERE/'rationale-excerpts.json',{'variable_items':excerpts,'stable_case02_wording_criticism':stable,
         'new_numeric_judgments':0,'scope':'Actualpreviousrecords;notrescoreornewgroundtruth'})
    result={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'groups':rows,'M13_exact_agreement_decomposition':{
         'all':'50/54 = (14R+I matches +36gradedmatches)/(18R+I pairs+36gradedpairs)',
         'generated_R':'7/9=77.7778%','authored_I_alone':'7/9=77.7778%',
         'M15_natural':'21/27=77.7778%','interpretation':'Samepointpercentagenotproofpopulationreliabilityequal.R_only3texts,M15ninefreshdifferenttexts;sourcecompositionnotcausallyisolated.'},
         'M15_variable_texts':[{'item_id':i['item_id'],'scores':i['judges']['claude']['scores'],'mean':i['judges']['claude']['mean']} for i in variable],
         'M15_nominal_round_means':roundmeans,'M15_variable_pairs':comparisons,
         'visible_technical_conditions':{'same_input_within_text_across3reads':True,'same_role_all27reads':True,
             'CLI_versions':sorted(versions),'requested_models':sorted(models),'efforts':sorted(efforts),
             'fresh_context_flags_verified':True,'schema_errors':m15['completion']['schema_errors'],'quote_errors':m15['completion']['quote_errors'],
             'immutable_server_snapshot_or_temperature_available':False,'no_evidence_establishing_model_drift_or_internal_cause':True},
         'technical_records':technical,'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sources.values()},
         'limits':'Post-hocdiagnosis,3profiles/batch,reuseddependentpairs,no95%CI,pvalue,universalpasscutoff,causalreasonattributionornewrating.'}
    dump(HERE/'analysis.json',result)
    print('ReproducedM13all50/54 vsR7/9 vsgraded36/36;M15natural21/27;3variabletexts;allroundmeans30/9;same27Claudeinput/role/settings')
if __name__=='__main__':main()
