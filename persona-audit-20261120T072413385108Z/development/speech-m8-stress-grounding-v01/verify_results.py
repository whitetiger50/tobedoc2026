"""Verify fixed inputs, all 144 generation histories, two reviews and derived results."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import re
import shutil

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('m8',HERE/'experiment.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def main():
    plan=m.verify()
    old=m.read(m.PARENT/'plan.json')
    probes=m.read(HERE/'probes.json')['cases']
    for c,prior in zip(plan['cases'],old['cases']):
        for field in ['case_id','input']:assert c[field]==prior[field]
        assert c['questions'][:4]==prior['questions']
        assert c['required_fact_ids'][:4]==prior['required_fact_ids']
        assert c['questions'][4:]==[q['question'] for q in probes[c['case_id']]]
        assert c['required_fact_ids'][4:]==[q['required_fact_ids'] for q in probes[c['case_id']]]
        assert c['turn_types']==['original']*4+['time','person','cause','recovery']
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
    assert len(transcripts)==18 and len(generation_calls)==144
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
            spans=[row['reason'],row['uncertainty']]+[f['explanation'] for f in row['grounding_review']['findings']]+[f['explanation'] for f in row['avoidance_review']['findings']]
            spans.extend(i['issue'] for i in row['issues'])
            for text in spans:
                refs=set(re.findall(r'\bS[0-9]{3}\b',text))-{row['blind_id']}
                if refs:cross_references.append({'provider':provider,'blind_id':row['blind_id'],'other_ids':sorted(refs),'text':text})
        review_calls.append({'provider':provider,'ratings':len(parsed['reviews']),'timestamp_utc':meta['timestamp_utc'],
            'requested_model':meta['requested_model'],'effort':meta['settings']['reasoning_effort'],
            'cli_version':meta['cli_version'],'response_sha256':meta['response_sha256']})
    scores=m.read(HERE/'scores.json')
    # JSON serializes numeric score-frequency map keys as strings; normalize this
    # representation before equality, preserving the frozen analysis implementation.
    assert json.loads(m.canonical(m.analyze(transcripts,reviews)))==scores
    author=m.read(HERE/'author-stress-observations.json')
    transcript_index={t['item_id']:t for t in transcripts}
    assert len(author['rows'])==len({r['item_id'] for r in author['rows']})==18
    for row in author['rows']:
        turns={t['turn_id']:t['text'] for t in transcript_index[row['item_id']]['generated_dialogue'] if t['speaker']=='patient'}
        for e in row['evidence']+row['author_uncertain_findings']:assert e['quote'] in turns[e['patient_turn_id']]
    for version in m.VERSIONS:
        values=[reviews[p][t['item_id']]['score'] for t in transcripts if t['condition']==version for p in m.PROVIDERS]
        assert len(values)==18
        assert abs(sum(values)/18-scores['condition_means'][version])<1e-12
    for name in ['speech_module/patient_v02.txt','speech_module/patient_v05.txt','speech_module/core.py']:
        assert m.digest(m.ROOT/name)==old['frozen_file_sha256'][name]
    snapshot=HERE/'implementation-snapshot';snapshot.mkdir(exist_ok=False)
    for path in [HERE/'experiment.py',HERE/'test_analysis.py',HERE/'methods.md',HERE/'review-role.txt',HERE/'probes.json',
        m.ROOT/'speech_module/core.py',m.ROOT/'speech_module/patient_v02.txt',m.ROOT/'speech_module/patient_v05.txt',
        m.ROOT/'speech_module/patient_v05.sources.json',m.ROOT/'collaboration/subscription_call.py',
        m.ROOT/'development/speech-m1-v01/review_dev.py']:
        shutil.copyfile(path,snapshot/path.name)
    files=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='verification.json']
    m.dump(HERE/'verification.json',{'timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'same_M7_case_settings_starting_history_and_original_four_questions':True,'four_appended_questions_exactly_match_frozen_probes':True,
        'all_M7_prompts_runtime_and_pilot_unchanged_entire_M8':True,
        'same_first_turn_user_input_hash_in_all_six_starts_per_case':True,
        'own_actual_history_chain_and_raw_patient_text_verified_for_144_turns':True,
        'actual_new_complete_dialogues':18,'actual_new_generated_patient_turns':144,
        'generation_CLI_calls':generation_calls,'review_CLI_calls':review_calls,'actual_rating_outputs':36,
        'all_realism_grounding_avoidance_quotes_and_turn_labels_validated':True,
        'identical_review_input_and_role_between_providers':True,
        'original_score_anchors_and_profiles_preserved':True,
        'disclosure_and_repetition_text_identical_to_v02':True,'within_packet_other_ID_references_found':cross_references,
        'pre_score_author_observation_quotes_validated':True,
        'statistics_recomputed_from_raw_reviews_and_separate_condition_mean_check':True,
        'analysis_fixture_tests_passed':2,'prompt_and_core_byte_identical_to_M7':True,'new_paid_API_calls':0,'new_models_or_packages':0,
        'final_720_judgments':'not_performed','clinical_validation':'not_performed',
        'file_sha256':{str(p.relative_to(m.ROOT)):m.digest(p) for p in files}})
    print('Verified 18 fresh 8-turn dialogues / 144 actual generation calls / 2 reviews / 36 ratings; prompts unchanged')


if __name__=='__main__':main()
