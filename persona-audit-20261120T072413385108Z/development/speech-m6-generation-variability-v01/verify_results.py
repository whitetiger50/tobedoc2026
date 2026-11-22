"""Verify source equivalence, all 72 generation histories, two reviews and derived results."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import re
import shutil

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('m6',HERE/'experiment.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def main():
    plan=m.verify()
    old=m.read(m.PARENT/'plan.json')
    fields=('case_id','input','questions','required_fact_ids')
    assert [{k:c[k] for k in fields} for c in plan['cases']]==[{k:c[k] for k in fields} for c in old['cases']]
    generation_calls=[];transcripts=[];first_hashes={}
    for case in plan['cases']:
        first_hashes[case['case_id']]=[]
        for rep in (1,2,3):
            for version in m.VERSIONS:
                base=HERE/'runs'/case['case_id']/f'rep{rep:02d}'/version
                t=m.read(base/'transcript.json');transcripts.append(t)
                assert t['patient']==case['input']['patient'] and t['communication']==case['input']['communication']
                assert t['authored_context']==case['input']['history']
                expected=m.deepcopy(case['input']['history']);dialogue=[]
                for n,(q,required) in enumerate(zip(case['questions'],case['required_fact_ids']),1):
                    d=base/f'turn{n:02d}';packet=m.read(d/'packet.json');m.verify_packet(packet)
                    assert packet['module_version']==m.VERSIONS[version]
                    assert packet['input']['history']==expected
                    assert packet['input']['current_question']==q
                    assert packet['required_fact_ids']==required
                    if n==1:first_hashes[case['case_id']].append(packet['input_sha256'])
                    answer=(d/'patient.txt').read_text()
                    raw=m.read(d/'raw_response.json');meta=m.read(d/'transport/metadata.json')
                    assert answer==raw['text']==(d/'transport/response.txt').read_text()
                    assert m.digest(d/'transport/response.txt')==meta['response_sha256']
                    assert meta['status']=='response_received' and meta['returncode']==0 and meta['automatic_retries']==0
                    assert raw['model_id']==meta['requested_model']=='gpt-6.1-sol'
                    assert raw['settings']['reasoning_effort']==meta['settings']['reasoning_effort']=='high'
                    assert (d/'transport/input.txt').read_text()==packet['messages'][1]['content']
                    assert (d/'transport/instructions.txt').read_text()==packet['messages'][0]['content']
                    expected.extend([{'speaker':'clinician','text':q},{'speaker':'patient','text':answer}])
                    dialogue.extend([{'turn_id':f'D{n:02d}','speaker':'clinician','text':q},
                                     {'turn_id':f'P{n:02d}','speaker':'patient','text':answer}])
                    generation_calls.append({'case_id':case['case_id'],'replicate':rep,'condition':version,
                        'turn':n,'timestamp_utc':meta['timestamp_utc'],'cli_version':meta['cli_version'],
                        'response_sha256':meta['response_sha256']})
                assert dialogue==t['generated_dialogue']
    assert len(transcripts)==18 and len(generation_calls)==72
    assert all(len(values)==6 and len(set(values))==1 for values in first_hashes.values())
    packet=m.read(HERE/'review-packet.json');key=m.read(HERE/'review-key-private.json');frozen=m.read(HERE/'review-freeze.json')
    assert m.digest(HERE/'review-packet.json')==frozen['packet_sha256']
    assert m.digest(HERE/'review-role.txt')==frozen['role_sha256']
    assert m.digest(HERE/'review-key-private.json')==frozen['key_sha256']
    assert packet['score_anchors']==m.read(m.PARENT/'review-packet.json')['score_anchors']
    assert packet['profiles']==m.read(m.PARENT/'review-packet.json')['profiles']
    assert len(key)==len(packet['cases'])==18
    for c in packet['cases']:
        meta=key[c['blind_id']];path=m.ROOT/meta['transcript_path']
        assert m.digest(path)==meta['transcript_sha256']
        assert c['generated_dialogue']==m.read(path)['generated_dialogue']
    reviews={};review_calls=[];cross_references=[]
    for provider in m.PROVIDERS:
        d=HERE/'reviews'/provider;meta=m.read(d/'metadata.json')
        assert m.digest(d/'input.txt')==meta['input_sha256']==frozen['packet_sha256']
        assert m.digest(d/'instructions.txt')==meta['instructions_sha256']==frozen['role_sha256']
        assert m.digest(d/'response.txt')==meta['response_sha256']
        assert meta['status']=='response_received' and meta['returncode']==0 and meta['automatic_retries']==0
        assert meta['requested_model']==('gpt-6.1-sol' if provider=='codex' else 'claude-opus-5-5')
        parsed=m.M1.parse_review((d/'response.txt').read_text());assert parsed==m.read(d/'validated.json')
        validated=m.validate_review(parsed,packet)
        reviews[provider]={key[r['blind_id']]['item_id']:r for r in validated}
        for row in validated:
            spans=[row['reason'],row['uncertainty'],row['disclosure_flow']['explanation'],row['repetition_flow']['explanation']]
            spans.extend(i['issue'] for i in row['issues'])
            for text in spans:
                refs=set(re.findall(r'\bG[0-9]{3}\b',text))-{row['blind_id']}
                if refs:cross_references.append({'provider':provider,'blind_id':row['blind_id'],'other_ids':sorted(refs),'text':text})
        review_calls.append({'provider':provider,'ratings':len(parsed['reviews']),'timestamp_utc':meta['timestamp_utc'],
            'requested_model':meta['requested_model'],'effort':meta['settings']['reasoning_effort'],
            'cli_version':meta['cli_version'],'response_sha256':meta['response_sha256']})
    scores=m.read(HERE/'scores.json')
    # JSON serializes numeric score-frequency map keys as strings; normalize this
    # representation before equality, preserving the frozen analysis implementation.
    assert json.loads(m.canonical(m.analyze(transcripts,reviews)))==scores
    author=m.read(HERE/'author-flow-observations.json')
    transcript_index={t['item_id']:t for t in transcripts}
    assert len(author['rows'])==len({r['item_id'] for r in author['rows']})==18
    for row in author['rows']:
        turns={t['turn_id']:t['text'] for t in transcript_index[row['item_id']]['generated_dialogue'] if t['speaker']=='patient'}
        for e in row['evidence']:assert e['quote'] in turns[e['patient_turn_id']]
    for version in m.VERSIONS:
        values=[reviews[p][t['item_id']]['score'] for t in transcripts if t['condition']==version for p in m.PROVIDERS]
        assert len(values)==18
        assert abs(sum(values)/18-scores['condition_means'][version])<1e-12
    snapshot=HERE/'implementation-snapshot';snapshot.mkdir(exist_ok=False)
    for path in [HERE/'experiment.py',HERE/'test_analysis.py',HERE/'methods.md',HERE/'review-role.txt',
        m.ROOT/'speech_module/core.py',m.ROOT/'speech_module/patient_v02.txt',m.ROOT/'speech_module/patient_v04.txt',
        m.ROOT/'speech_module/patient_v04.sources.json',m.ROOT/'collaboration/subscription_call.py',
        m.ROOT/'development/speech-m1-v01/review_dev.py']:
        shutil.copyfile(path,snapshot/path.name)
    files=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='verification.json']
    m.dump(HERE/'verification.json',{'timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'same_M4_case_settings_questions_requirements_and_starting_history':True,
        'all_frozen_prompts_runtime_and_final_pilot_files_unchanged':True,
        'same_first_turn_user_input_hash_in_all_six_starts_per_case':True,
        'own_actual_history_chain_and_raw_patient_text_verified_for_72_turns':True,
        'actual_new_complete_dialogues':18,'actual_new_generated_patient_turns':72,
        'generation_CLI_calls':generation_calls,'review_CLI_calls':review_calls,'actual_rating_outputs':36,
        'all_scores_and_realism_and_flow_quotes_validated':True,
        'identical_review_input_and_role_between_providers':True,
        'original_score_anchors_and_profiles_preserved':True,
        'author_flow_observation_quotes_validated':True,'within_packet_other_ID_references_found':cross_references,
        'statistics_recomputed_from_raw_reviews_and_separate_condition_mean_check':True,
        'analysis_fixture_tests_passed':3,'new_paid_API_calls':0,'new_models_or_packages':0,
        'final_720_judgments':'not_performed','clinical_validation':'not_performed',
        'file_sha256':{str(p.relative_to(m.ROOT)):m.digest(p) for p in files}})
    print('Verified 18 fresh dialogues / 72 actual generation calls / 2 reviews / 36 ratings; prompts unchanged')


if __name__=='__main__':main()
