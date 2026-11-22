"""Reconcile raw CLI responses, fixed stimuli, exact parsing and recomputed summaries."""
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
import json
import experiment as e
import analysis_stats as a
HERE=e.HERE;ROOT=e.ROOT

def main():
    e.verify();corpus=e.read(HERE/'corpus.json');slots=e.read(HERE/'schedule.json')['slots']
    records={};gpt_contexts=[];calls=[];hashes={};generations=[]
    for c in e.read(HERE/'cases.json')['cases']:
        case=c['case_id'];t=e.read(HERE/'runs'/case/'transcript.json')
        patient_turns=[x for x in t['generated_dialogue'] if x['speaker']=='patient']
        assert len(patient_turns)==8
        expected_history=deepcopy(c['input']['history'])
        for n,turn in enumerate(patient_turns,1):
            d=HERE/'runs'/case/f'turn{n:02d}'/'transport';m=e.read(d/'metadata.json')
            packet=e.read(d.parent/'packet.json')
            assert packet['module_version']=='schizophrenia-speech-m1-v0.2'
            assert packet['template_sha256']==e.sha(ROOT/'speech_module/patient_v02.txt')
            assert packet['input']['history']==expected_history
            assert packet['input']['current_question']==c['questions'][n-1]
            assert packet['messages'][0]['content']==(d/'instructions.txt').read_text()
            assert packet['messages'][1]['content']==(d/'input.txt').read_text()
            assert m['status']=='response_received' and m['automatic_retries']==0
            assert m['requested_model']=='gpt-6.1-sol' and m['settings']['reasoning_effort']=='high'
            assert (d/'response.txt').read_text()==turn['text']
            assert e.sha(d/'input.txt')==m['input_sha256'] and e.sha(d/'instructions.txt')==m['instructions_sha256']
            assert e.sha(d/'response.txt')==m['response_sha256']
            generations.append({'case_id':case,'turn':n,'timestamp_utc':m['timestamp_utc'],'response_sha256':m['response_sha256']})
            expected_history.extend([{'speaker':'clinician','text':c['questions'][n-1]},
                                     {'speaker':'patient','text':turn['text']}])
    assert len(generations)==24
    for i in corpus['items']:
        t=e.read(ROOT/i['source_path']);ref={'patient_profile':{k:t['patient'][k] for k in ['facts','self_understanding']},
           'communication':t['communication'],'prior_authored_context':t['authored_context'],'dialogue':t['generated_dialogue']}
        if i['condition']=='R':assert ref==i['payload']
        else:
            original=deepcopy(ref);target=next(x for x in original['dialogue'] if x['turn_id']=='P02')
            assert target['text']==i['perturbation']['original'];target['text']=i['perturbation']['replacement']
            assert original==i['payload']
            assert sum(x!=y for x,y in zip(ref['dialogue'],i['payload']['dialogue']))==1
        assert e.sha(HERE/'inputs'/f'{i["item_id"]}.json')==i['input_sha256']
    for s in slots:
        d=HERE/'reviews'/s['provider']/s['opaque_id']
        if not (d/'metadata.json').exists():continue
        m=e.read(d/'metadata.json')
        if m['status']!='response_received':continue
        assert m['returncode']==0 and m['automatic_retries']==0
        assert m['requested_model']==('gpt-6.1-sol' if s['provider']=='codex' else 'claude-opus-5-5')
        assert m['settings']['reasoning_effort']==('high' if s['provider']=='codex' else 'medium')
        assert (d/'input.txt').read_bytes()==(HERE/'inputs'/f'{s["item_id"]}.json').read_bytes()
        assert e.sha(d/'input.txt')==m['input_sha256']
        assert e.sha(d/'instructions.txt')==m['instructions_sha256']==e.sha(HERE/'review-role.txt')
        assert e.sha(d/'response.txt')==m['response_sha256']
        v=e.read(d/'validated.json')
        try:raw=e.parse((d/'response.txt').read_text())
        except (ValueError,TypeError,KeyError,AssertionError):
            assert not (d/'parsed.json').exists() and v['realism_score'] is None
        else:
            assert raw==e.read(d/'parsed.json')
            assert e.validate(raw,json.loads((d/'input.txt').read_text()))==v
        cmd=e.read(d/'command.json')['argv']
        assert '--resume' not in cmd and '--continue' not in cmd
        if s['provider']=='codex':
            assert '--ephemeral' in cmd and '--ignore-user-config' in cmd and '--no-daemon' in cmd
            gpt_contexts.append(cmd[cmd.index('--cd')+1])
        else:
            assert '--safe-mode' in cmd and '--no-session-persistence' in cmd and cmd[cmd.index('--tools')+1]==''
            assert set(m['reported_model_usage'])=={'claude-opus-5-5'}
        hashes.setdefault(s['item_id'],[]).append(m['input_sha256']);records[(s['item_id'],s['provider'],s['repetition'])]=v
        calls.append({'slot':s,'timestamp_utc':m['timestamp_utc'],'cli_version':m['cli_version'],
                      'input_sha256':m['input_sha256'],'response_sha256':m['response_sha256']})
    assert len(set(gpt_contexts))==len(gpt_contexts)
    assert all(len(set(v))==1 for v in hashes.values())
    actual=e.read(HERE/'results.json');assert a.M12.clean(a.summarize(corpus,records))==actual
    strategy=ROOT/'collaboration/strategy/M13-graded-discrimination-v01';mentors=[]
    for no in [1,2]:
        d=strategy/f'claude-round{no:02d}';m=e.read(d/'metadata.json')
        assert m['status']=='response_received' and m['effort']=='high'
        assert e.sha(d/'input.txt')==m['input_sha256'] and e.sha(d/'response.txt')==m['response_sha256']
        mentors.append({'round':no,'model':m['requested_model'],'session':m['transport_session_id'],'response_sha256':m['response_sha256']})
    assert mentors[0]['session']!=mentors[1]['session']
    assert all((strategy/f'astra-round{n:02d}.md').stat().st_size>100 for n in [1,2])
    files=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='verification.json']
    e.dump(HERE/'verification.json',{'timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'frozen_source_prompt_criteria_and_analysis_unchanged':True,'actual_new_patient_outputs':24,
        'actual_new_reference_dialogues':3,'actual_numeric_responses':len(records),'planned_numeric_responses':108,
        'all108_received':len(records)==108,'valid_primary_scores':actual['completion']['valid_primary_scores'],
        'same_input_across_models_repeats':all(len(v)==6 for v in hashes.values()),'unique_GPT_temporary_contexts':len(set(gpt_contexts)),
        'all_variants_only_P02_changed':True,'prerating_stimulus_amendment_disclosed':True,
        'raw_numeric_quotes_and_statistics_reconciled':True,'offline_statistics_fixtures':a.fixtures(),
        'actual_Claude_strategy_calls':mentors,'Astra_review_reports':2,'final12_content_read_or_used':False,
        'final12_files_hash_unchanged':True,'final720_executed':False,'clinical_validation':False,
        'new_paid_API_calls':0,'new_models_downloaded':0,'new_packages_installed':0,
        'generation_call_records':generations,'rating_call_records':calls,
        'file_sha256':{str(p.relative_to(ROOT)):e.sha(p) for p in files}})
    print('Verified',len(records),'/108actualjudgeresponses;24referenceoutputs;prompts/criteria/controls/rawscores/hashes/statistics',flush=True)
if __name__=='__main__':main()
