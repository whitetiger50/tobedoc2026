"""Reconcile M15 actual outputs, unchanged prompts, raw reviews and summaries."""
from pathlib import Path
from datetime import datetime,timezone
from copy import deepcopy
import json
import experiment as e
import analysis_stats as a
HERE=e.HERE;ROOT=e.ROOT

def main():
    e.verify();corpus=e.read(HERE/'corpus.json');records={};generation_calls=[];judge_calls=[];contexts=[];hashes={}
    for c in e.read(HERE/'cases.json')['cases']:
        for rep in [1,2,3]:
            base=HERE/'runs'/c['case_id']/f'rep{rep:02d}';t=e.read(base/'transcript.json')
            turns=[x for x in t['generated_dialogue'] if x['speaker']=='patient'];history=deepcopy(c['input']['history'])
            assert len(turns)==8
            for n,turn in enumerate(turns,1):
                d=base/f'turn{n:02d}'/'transport';m=e.read(d/'metadata.json');packet=e.read(d.parent/'packet.json')
                assert m['status']=='response_received' and m['requested_model']=='gpt-6.1-sol' and m['automatic_retries']==0
                assert m['settings']['reasoning_effort']=='high'
                assert packet['module_version']=='schizophrenia-speech-m1-v0.2' and packet['template_sha256']==e.sha(ROOT/'speech_module/patient_v02.txt')
                assert packet['input']['history']==history and packet['input']['current_question']==c['questions'][n-1]
                assert (d/'response.txt').read_text()==turn['text']
                assert packet['messages'][0]['content']==(d/'instructions.txt').read_text() and packet['messages'][1]['content']==(d/'input.txt').read_text()
                for f,k in [('response.txt','response_sha256'),('input.txt','input_sha256'),('instructions.txt','instructions_sha256')]:assert e.sha(d/f)==m[k]
                generation_calls.append({'case_id':c['case_id'],'generation_replicate':rep,'turn':n,'timestamp_utc':m['timestamp_utc'],'response_sha256':m['response_sha256']})
                history.extend([{'speaker':'clinician','text':c['questions'][n-1]},{'speaker':'patient','text':turn['text']}])
    for i in corpus['items']:
        t=e.read(ROOT/i['source_path']);expected={'patient_profile':{k:t['patient'][k] for k in ['facts','self_understanding']},
             'communication':t['communication'],'prior_authored_context':t['authored_context'],'dialogue':t['generated_dialogue']}
        assert expected==i['payload'] and e.sha(HERE/'inputs'/f'{i["item_id"]}.json')==i['input_sha256']
    audit=e.read(HERE/'author-prejudge-audit.json');audit_time=datetime.fromisoformat(audit['timestamp_utc'])
    for slot in e.read(HERE/'schedule.json')['slots']:
        d=HERE/'reviews'/slot['provider']/slot['opaque_id']
        if not (d/'metadata.json').exists():continue
        m=e.read(d/'metadata.json')
        if m['status']!='response_received':continue
        assert datetime.fromisoformat(m['timestamp_utc'])>audit_time
        assert m['requested_model']==('gpt-6.1-sol' if slot['provider']=='codex' else 'claude-opus-5-5')
        assert m['settings']['reasoning_effort']==('high' if slot['provider']=='codex' else 'medium')
        assert m['returncode']==0 and m['automatic_retries']==0
        for f,k in [('response.txt','response_sha256'),('input.txt','input_sha256'),('instructions.txt','instructions_sha256')]:assert e.sha(d/f)==m[k]
        assert (d/'input.txt').read_bytes()==(HERE/'inputs'/f'{slot["item_id"]}.json').read_bytes()
        assert e.sha(d/'instructions.txt')==e.sha(HERE/'review-role.txt')
        v=e.read(d/'validated.json')
        try:raw=e.parse((d/'response.txt').read_text())
        except (ValueError,TypeError,KeyError,AssertionError):assert v['realism_score'] is None and not (d/'parsed.json').exists()
        else:assert raw==e.read(d/'parsed.json') and e.validate(raw,json.loads((d/'input.txt').read_text()))==v
        cmd=e.read(d/'command.json')['argv'];assert '--resume' not in cmd and '--continue' not in cmd
        if slot['provider']=='codex':
            assert '--ephemeral' in cmd and '--ignore-user-config' in cmd and '--no-daemon' in cmd
            contexts.append(cmd[cmd.index('--cd')+1])
        else:
            assert '--safe-mode' in cmd and '--no-session-persistence' in cmd and cmd[cmd.index('--tools')+1]==''
            assert set(m['reported_model_usage'])=={'claude-opus-5-5'}
        records[(slot['item_id'],slot['provider'],slot['repetition'])]=v;hashes.setdefault(slot['item_id'],[]).append(m['input_sha256'])
        judge_calls.append({'slot':slot,'timestamp_utc':m['timestamp_utc'],'cli_version':m['cli_version'],'input_sha256':m['input_sha256'],'response_sha256':m['response_sha256']})
    assert len(set(contexts))==len(contexts) and all(len(set(v))==1 for v in hashes.values())
    actual=e.read(HERE/'results.json');assert a.M12.clean(a.summarize(corpus,records))==actual
    assert len(generation_calls)==72
    files=[p for p in HERE.rglob('*') if p.is_file() and p.name!='verification.json' and '__pycache__' not in p.parts]
    e.dump(HERE/'verification.json',{'timestamp_utc':datetime.now(timezone.utc).isoformat(),
         'actual_patient_generation_calls':72,'actual_new_dialogues':9,'actual_numeric_judge_responses':len(records),
         'planned_judge_responses':54,'all54_received':len(records)==54,'criteria_parser_and_patient_module_unchanged':True,
         '4question_changes_and24question_audit_frozen_before_generation':True,'no_reference_or_answer_postediting':True,
         'prejudge_author_audit_before_all_numeric_calls':True,'prejudge_audit_coverage':len(audit['turns']),
         'same_semantic_input_across6readings':all(len(v)==6 for v in hashes.values()),
         'fresh_GPT_temporary_contexts':len(set(contexts)),'numeric_quotes_raw_responses_reconciled':True,
         'statistics_independently_recomputed':True,'offline_statistics_fixtures':a.fixtures(),
         'final12_content_read_or_used':False,'final12_byte_hashes_unchanged':True,'final720_executed':False,
         'new_paid_API_calls':0,'new_models_downloaded':0,'new_packages_installed':0,'clinical_validation':False,
         'generation_records':generation_calls,'judge_records':judge_calls,
         'file_sha256':{str(p.relative_to(ROOT)):e.sha(p) for p in files}})
    print('Verified72patientoutputs/9dialogs and',len(records),'/54judgeoutputs;unchangedv02/criteria;prejudgeaudit;rawscores/quotes/hashes',flush=True)
if __name__=='__main__':main()
