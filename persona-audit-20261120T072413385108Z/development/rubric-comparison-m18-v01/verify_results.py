"""Post-run reconciliation, without changing frozen analysis or invoking models."""
from collections import Counter
from copy import deepcopy
from datetime import datetime,timezone
from itertools import combinations
from common import HERE,ROOT,BASE,read,dump,sha,canonical,validate_safe,target_flags
from experiment import verify
from analyze import summary

def main():
    freeze=verify();corpus=read(HERE/'corpus.json');results=read(HERE/'results.json')
    strategy=ROOT/'collaboration/strategy/M18-rubric-comparison-v01';scope=read(strategy/'scope-freeze.json')
    for group in ['file_sha256','protected_final_files_sha256']:
        for name,expected in scope[group].items():assert sha(ROOT/name)==expected,name
    for stage in ['aligned-input-residual-m15-v01']:
        prior=read(ROOT/'development'/stage/'verification.json')
        for name,expected in prior['file_sha256'].items():assert sha(ROOT/name)==expected,name
    generation=[]
    cases=read(HERE/'cases.json')['cases']
    for case in cases:
        for rep in [1,2,3]:
            directory=HERE/'runs'/case['case_id']/f'rep{rep:02d}';t=read(directory/'transcript.json')
            history=deepcopy(case['input']['history']);patient=[x for x in t['generated_dialogue'] if x['speaker']=='patient']
            assert len(patient)==8
            for n,turn in enumerate(patient,1):
                d=directory/f'turn{n:02d}'/'transport';m=read(d/'metadata.json');packet=read(d.parent/'packet.json')
                assert m['status']=='response_received' and m['requested_model']=='gpt-6.1-sol' and m['automatic_retries']==0
                assert m['settings']['reasoning_effort']=='high'
                assert packet['template_sha256']==sha(ROOT/'speech_module/patient_v02.txt')
                assert packet['input']['history']==history and packet['input']['current_question']==case['questions'][n-1]
                assert (d/'response.txt').read_text()==(d.parent/'patient.txt').read_text()==turn['text']
                assert packet['messages'][0]['content']==(d/'instructions.txt').read_text()
                assert packet['messages'][1]['content']==(d/'input.txt').read_text()
                for f,k in [('response.txt','response_sha256'),('input.txt','input_sha256'),('instructions.txt','instructions_sha256')]:assert sha(d/f)==m[k]
                history.extend([{'speaker':'clinician','text':case['questions'][n-1]},{'speaker':'patient','text':turn['text']}])
                generation.append({'case_id':case['case_id'],'rep':rep,'turn':n,'response_sha256':m['response_sha256']})
    by={r['item_id']:r for r in corpus['items']}
    assert len(by)==24 and len(corpus['unique_item_ids'])==21
    for row in corpus['items']:
        path=HERE/'inputs'/(row['item_id']+'.json');assert sha(path)==row['input_sha256'] and read(path)==row['payload']
        assert set(row['payload'])=={'patient_profile','communication','prior_authored_context','dialogue'}
        assert set(row['payload']['patient_profile'])=={'facts','self_understanding'}
        alias=by[row['semantic_id']];assert (HERE/'inputs'/(alias['item_id']+'.json')).read_bytes()==path.read_bytes()
        if row['condition']=='N':
            t=read(HERE/'runs'/row['case_id']/f'rep{row["generation_replicate"]:02d}'/'transcript.json')
            assert row['payload']['dialogue']==t['generated_dialogue']
        else:
            parent=deepcopy(by[row['parent_id']]['payload'])
            for edit in row['edits']:
                turn=next(x for x in parent['dialogue'] if x['turn_id']==edit['turn_id'])
                assert turn['text']==edit['original'];turn['text']=edit['replacement']
            assert parent==row['payload']
    schedule=read(HERE/'schedule.json')['slots'];assert len(schedule)==252
    assert len({(s['item_id'],s['criterion'],s['provider'],s['repetition']) for s in schedule})==252
    records={};contexts=[];claude_sessions=[];counts=Counter();hashes={}
    audit=read(HERE/'author-prejudge-audit.json');audit_time=datetime.fromisoformat(audit['timestamp_utc'])
    assert audit['new_judge_outputs_seen']==0 and audit['actual_generated_turns_read']==72
    for slot in schedule:
        d=HERE/'reviews'/slot['provider']/slot['opaque_id']
        if not (d/'validated.json').exists():continue
        m=read(d/'metadata.json');v=read(d/'validated.json')
        assert m['status']=='response_received' and m['returncode']==0 and m['automatic_retries']==0
        assert datetime.fromisoformat(m['timestamp_utc'])>audit_time
        assert m['requested_model']==('gpt-6.1-sol' if slot['provider']=='codex' else 'claude-opus-5-5')
        assert m['settings']['reasoning_effort']==('high' if slot['provider']=='codex' else 'medium')
        for f,k in [('response.txt','response_sha256'),('input.txt','input_sha256'),('instructions.txt','instructions_sha256')]:assert sha(d/f)==m[k]
        assert (d/'input.txt').read_bytes()==(HERE/'inputs'/(slot['item_id']+'.json')).read_bytes()
        assert sha(d/'instructions.txt')==sha(HERE/f'role-{slot["criterion"]}.txt')
        raw=BASE.parse((d/'response.txt').read_text()) if (d/'parsed.json').exists() else None
        if raw is not None:assert raw==read(d/'parsed.json') and validate_safe(raw,by[slot['item_id']]['payload'],slot['criterion'])==v
        argv=read(d/'command.json')['argv'];assert '--resume' not in argv and '--continue' not in argv
        if slot['provider']=='codex':
            assert '--ephemeral' in argv and '--ignore-user-config' in argv and '--no-daemon' in argv
            contexts.append(argv[argv.index('--cd')+1])
        else:
            assert '--safe-mode' in argv and '--no-session-persistence' in argv and argv[argv.index('--tools')+1]==''
            assert set(m['reported_model_usage'])=={'claude-opus-5-5'}
            rawtransport=read(d/'stdout.raw')
            if rawtransport.get('session_id'):claude_sessions.append(rawtransport['session_id'])
        records[slot['item_id'],slot['criterion'],slot['provider'],slot['repetition']]=v
        counts[slot['criterion']+':'+slot['provider']]+=1;hashes.setdefault(slot['item_id'],[]).append(m['input_sha256'])
    assert len(set(contexts))==len(contexts) and len(set(claude_sessions))==len(claude_sessions)
    assert all(len(set(v))==1 for v in hashes.values())
    terms=read(HERE/'perturbation-spec.json')['repeat_terms'];result_by={i['item_id']:i for i in results['items']}
    for item in results['items']:
        row=by[item['item_id']]
        for criterion in ['realism','ccf']:
            for provider in ['codex','claude']:
                expected=[records.get((row['semantic_id'],criterion,provider,r),{}).get('realism_score') for r in [1,2,3]]
                assert expected==item['cells'][criterion][provider]['scores']
                for rec in item['cells'][criterion][provider]['readings']:
                    if rec is None:continue
                    v=records[row['semantic_id'],criterion,provider,rec['repetition']]
                    assert v==rec['validated']
                    assert target_flags(v,row['payload'],row['targets'],terms)==rec['target_flags']
    for group in results['groups']:
        matrix=[result_by[i]['cells'][group['criterion']][group['provider']]['scores'] for i in group['item_ids']]
        assert summary(matrix)==group['statistics']
        pairs=[a==b for row in matrix for a,b in combinations([x for x in row if x is not None],2)]
        assert sum(pairs)==group['statistics']['exact_numeric_pair_matches'] and len(pairs)==group['statistics']['numeric_pair_count']
    assert len(generation)==72 and results['completion']['recorded']==len(records)
    metadata=dict(timestamp_utc=datetime.now(timezone.utc).isoformat(),actual_patient_calls=72,actual_new_dialogues=9,
      condition_rows=24,unique_inputs=21,planned_numeric_calls=252,actual_numeric_responses=len(records),
      all_planned_received=len(records)==252,counts_by_criterion_provider=dict(counts),
      active_patient_module_and_both_criteria_unchanged=True,
      same_input_all12_unique_text_readings=all(len(v)==12 for v in hashes.values()) if len(records)==252 else None,
      fresh_GPT_temporary_contexts=len(contexts),distinct_Claude_reported_sessions=len(claude_sessions),
      raw_responses_numeric_fields_quotes_targets_and_group_statistics_reconciled=True,
      pair_counts_independently_counted=True,prejudge_audit_before_all_calls=True,
      final12_content_read_or_used=False,final12_byte_hashes_unchanged=True,final720_executed=False,
      paid_API_calls=0,new_models_downloaded=0,new_packages_installed=0,clinical_validation=False,
      generation_records=generation)
    files=[f for f in HERE.rglob('*') if f.is_file() and f.name!='verification.json' and '__pycache__' not in f.parts and f.suffix!='.log']
    metadata['file_sha256']={str(f.relative_to(ROOT)):sha(f) for f in files}
    dump(HERE/'verification.json',metadata)
    print('Verified actual72patientturns and',len(records),'/252judge responses; protected sources, prompts and final files unchanged; no scores printed')

if __name__=='__main__':main()
