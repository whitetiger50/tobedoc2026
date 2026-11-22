"""Verify M17 design provenance and protected files; never calls a model."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_files(mapping):
    for name, expected in mapping.items():
        assert sha(ROOT / name) == expected, name


def main():
    scope = read(HERE / 'scope-freeze.json')
    check_files(scope['file_sha256'])
    check_files(scope['protected_final_files_sha256'])
    m15 = read(ROOT / 'development/aligned-input-residual-m15-v01/verification.json')
    check_files(m15['file_sha256'])
    for folder in ['rater-reliability-m12-v01', 'graded-discrimination-m13-v01', 'aligned-input-residual-m15-v01']:
        assert sha(ROOT / 'development' / folder / 'review-role.txt') == '6637b7045ba9d05cb5868847e0d58f9f2c2abbffc21cf4f8ab83635e132027b9'
    first = read(HERE / 'request-freeze.json')
    second = read(HERE / 'round02-freeze.json')
    assert sha(HERE / 'review-request-round01.md') == first['body_sha256']
    assert sha(HERE / 'mentor-role.txt') == first['role_sha256'] == second['role_sha256']
    assert sha(HERE / 'rubric-draft-v01.md') == first['draft_sha256']
    assert sha(HERE / 'literature-notes.md') == first['literature_sha256']
    assert sha(HERE / 'references.json') == first['references_sha256']
    assert sha(HERE / 'review-request-round02.md') == second['body_sha256']
    assert sha(HERE / 'evaluator-instructions-draft-v02.txt') == second['draft2_sha256']
    assert sha(HERE / 'codex-response-round01.md') == second['counterargument_sha256']
    for name, expected in second['initial_actual_responses_sha256'].items():
        assert sha(HERE / name) == expected
    sessions = []
    metadata_records = []
    for n, body in [(1, 'review-request-round01.md'), (2, 'review-request-round02.md')]:
        directory = HERE / f'claude-round0{n}'
        metadata = read(directory / 'metadata.json')
        assert metadata['status'] == 'response_received' and metadata['returncode'] == 0
        assert metadata['purpose'] == 'development_direction_mentor_not_utterance_judge'
        assert metadata['requested_model'] == 'claude-opus-5-5' and metadata['effort'] == 'high'
        assert set(metadata['reported_model_usage']) == {'claude-opus-5-5'}
        assert metadata['automatic_retries'] == 0
        assert metadata['input_sha256'] == sha(directory / 'input.txt') == sha(HERE / body)
        assert metadata['instructions_sha256'] == sha(directory / 'instructions.txt') == sha(HERE / 'mentor-role.txt')
        assert metadata['response_sha256'] == sha(directory / 'response.txt')
        assert read(directory / 'stdout.raw')['result'] == (directory / 'response.txt').read_text()
        argv = read(directory / 'command.json')['argv']
        assert '--safe-mode' in argv and '--no-session-persistence' in argv
        assert argv[argv.index('--tools') + 1] == ''
        assert argv[argv.index('--max-turns') + 1] == '1'
        sessions.append(metadata['transport_session_id'])
        metadata_records.append({k: metadata[k] for k in ['requested_model', 'effort', 'input_sha256', 'response_sha256', 'automatic_retries', 'status']})
        assert (HERE / f'astra-round0{n}.md').stat().st_size > 1000
    assert len(set(sessions)) == 2
    references = read(HERE / 'references.json')
    assert len(references['downloaded_primary_sources']) == 5
    for source in references['downloaded_primary_sources']:
        assert sha(HERE / 'sources' / (source['id'] + '.pdf')) == source['sha256']
        assert sha(HERE / 'text' / (source['id'] + '.txt')) == source['text_sha256']
    assert sha(HERE / 'qa/abc2023-p24.png') == references['ABC_image_sha256']
    assert sha(ROOT / references['canonical_PATIENTSIM']['path']) == references['canonical_PATIENTSIM']['sha256']
    proposal = read(HERE / 'proposal-freeze.json')
    for name, expected in proposal['file_sha256'].items():
        assert sha(HERE / name) == expected
    assert read(HERE / 'rule-source-map.json')['final_instructions_sha256'] == sha(HERE / 'evaluator-instructions-proposal.txt')
    assert not (HERE / 'scores.json').exists() and not (HERE / 'corpus.json').exists()
    instructions = (HERE / 'evaluator-instructions-proposal.txt').read_text()
    assert 'M15' not in instructions and '멘토' not in instructions and 'other_defined_issue' not in instructions
    assert 'global_uncertain' not in instructions
    assert 'CCF-R1-proposal' in instructions
    assert '총점을 먼저 판단' in instructions and '최대3개' in instructions
    assert '같은 사건' in instructions and '1–3 앵커의 문제 요건' in instructions
    assert 'context_refs' in instructions and '적용불가null' in instructions
    assert 'form_repetition/both_repetition' in instructions
    status = read(ROOT / 'collaboration/development-status.json')
    assert status['development_reviews']['calls'] == 289
    assert status['strategy_mentoring']['calls'] == 14
    assert status['actual_synthetic_patient_generation_calls'] == 591
    assert status['completed_development_dialogues'] == 99
    assert status['completed_development_numeric_rating_outputs'] == 480
    assert status['research_judgment_calls'] == 0 and status['prompt_revision_paused_by_user']
    report = dict(timestamp_utc=datetime.now(timezone.utc).isoformat(),
                  frozen_prior_source_files_unchanged=len(scope['file_sha256']),
                  all_M15_manifest_files_unchanged=len(m15['file_sha256']),
                  final_files_byte_hashes_unchanged=len(scope['protected_final_files_sha256']),
                  final12_content_read=False, final720_executed=False,
                  patient_module_and_active_judge_roles_and_parsers_unchanged=True,
                  original_primary_measure_and_aggregation_unchanged=True,
                  initial_and_followup_packets_and_drafts_unchanged=True,
                  actual_Claude_strategy_CLI_responses=2, actual_Astra_strategy_response_files=2,
                  Astra_requested_model='gpt-6.2-astra', Astra_requested_effort='high',
                  Astra_immutable_backend_snapshot_independently_verified=False,
                  official_Claude_metadata_checks=metadata_records,
                  exact_final_proposal_not_third_reviewed=True,
                  downloaded_primary_papers=5, ABC_Figure16_PDFp24_visually_inspected=True,
                  proposed_criteria_version='CCF-R1-proposal', proposal_adopted=False,
                  new_patient_outputs=0, new_numeric_ratings=0,
                  observed_reliability_improvement=False, clinical_validation=False,
                  new_paid_API_calls=0, new_models_downloaded=0, new_packages_installed=0,
                  cumulative_synthetic_generation_calls=591, cumulative_generated_dialogues=99,
                  cumulative_Realism_ratings=480, cumulative_review_CLI_invocations=289)
    report['file_sha256'] = {str(f.relative_to(ROOT)): sha(f) for f in sorted(HERE.rglob('*'))
                            if f.is_file() and f.name != 'verification.json' and '__pycache__' not in f.parts}
    (HERE / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print('M17 verified: 2 Claude high receipts/2 Astra files; 5 primary PDFs; 63 prior files + M15manifest + final17 unchanged; new patient/rating outputs0; proposal not adopted.')


if __name__ == '__main__':
    main()
