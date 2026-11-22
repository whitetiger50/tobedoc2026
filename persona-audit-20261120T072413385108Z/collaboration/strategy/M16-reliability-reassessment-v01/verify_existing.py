"""Verify the bounded M16 reassessment without regenerating frozen analysis."""
from pathlib import Path
from datetime import datetime, timezone
from itertools import combinations
import hashlib
import importlib.util
import json
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def main():
    scope = read(HERE / 'scope-freeze.json')
    for key in ['file_sha256', 'protected_final_files_sha256']:
        for name, expected in scope[key].items():
            assert sha(ROOT / name) == expected, name
    assert scope['final12_content_read'] is False
    old = read(ROOT / 'development/aligned-input-residual-m15-v01/verification.json')
    for name, expected in old['file_sha256'].items():
        assert sha(ROOT / name) == expected, name
    initial = read(HERE / 'request-freeze.json')
    follow = read(HERE / 'round02-freeze.json')
    for name, expected in [('request.md', initial['body_sha256']),
                           ('mentor-role.txt', initial['role_sha256']),
                           ('analysis.json', initial['analysis_sha256']),
                           ('round02-request.md', follow['body_sha256']),
                           ('codex-response-round01.md', follow['counterargument_sha256']),
                           ('criterion-mapping.json', follow['mapping_sha256'])]:
        assert sha(HERE / name) == expected, name
    sessions = []
    for n, packet in [(1, 'request.md'), (2, 'round02-request.md')]:
        directory = HERE / f'claude-round0{n}'
        metadata = read(directory / 'metadata.json')
        raw = read(directory / 'stdout.raw')
        assert metadata['status'] == 'response_received'
        assert metadata['effort'] == 'high' and metadata['automatic_retries'] == 0
        assert metadata['requested_model'] == 'claude-opus-5-5'
        assert set(metadata['reported_model_usage']) == {'claude-opus-5-5'}
        assert metadata['input_sha256'] == sha(directory / 'input.txt') == sha(HERE / packet)
        assert metadata['instructions_sha256'] == sha(directory / 'instructions.txt') == sha(HERE / 'mentor-role.txt')
        assert metadata['response_sha256'] == sha(directory / 'response.txt')
        assert raw['result'] == (directory / 'response.txt').read_text()
        argv = read(directory / 'command.json')['argv']
        assert argv[argv.index('--tools') + 1] == ''
        assert '--no-session-persistence' in argv and '--safe-mode' in argv
        sessions.append(metadata['transport_session_id'])
        assert (HERE / f'astra-round0{n}.md').stat().st_size > 1000
    assert len(set(sessions)) == 2
    spec = importlib.util.spec_from_file_location('m12stats', ROOT / 'development/rater-reliability-m12-v01/analysis_stats.py')
    stats = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stats)
    analysis = read(HERE / 'analysis.json')
    for name, expected in analysis['source_sha256'].items():
        assert sha(ROOT / name) == expected
    for group in analysis['groups']:
        assert stats.clean(stats.matrix_summary(group['matrix'])) == group['statistics']
        matrix = group['matrix']
        pairs = [a == b for row in matrix for a, b in combinations(row, 2)]
        assert sum(pairs) == group['statistics']['exact_numeric_pair_matches']
        assert len(pairs) == group['statistics']['numeric_pair_count']
    m13 = read(ROOT / 'development/graded-discrimination-m13-v01/results.json')
    expected_conditions = {
        'M13_all': ['R', 'I', 'F1', 'F2', 'N1', 'N2'],
        'M13_generated_R_only': ['R'],
        'M13_R_plus_authored_meaning_preserving_I': ['R', 'I'],
        'M13_authored_graded_controls_only': ['F1', 'F2', 'N1', 'N2'],
    }
    groups = {g['group']: g for g in analysis['groups']}
    for name, conditions in expected_conditions.items():
        matrix = [i['judges']['claude']['scores'] for i in m13['items'] if i['condition'] in conditions]
        assert matrix == groups[name]['matrix']
    m15 = read(ROOT / 'development/aligned-input-residual-m15-v01/results.json')
    assert groups['M15_natural_all']['matrix'] == [i['judges']['claude']['scores'] for i in m15['items']]
    for round_index in range(3):
        scores = [i['judges']['claude']['scores'][round_index] for i in m15['items']]
        assert sum(scores) == 30 and scores.count(4) == 3
    variable = [i for i in m15['items'] if len(set(i['judges']['claude']['scores'])) > 1]
    assert [i['judges']['claude']['scores'] for i in variable] == [[3, 4, 4], [4, 3, 4], [4, 4, 3]]
    assert len(analysis['technical_records']) == 27
    for record in analysis['technical_records']:
        assert record['role_sha256'] == sha(ROOT / 'development/aligned-input-residual-m15-v01/review-role.txt')
    assert len(read(HERE / 'criterion-mapping.json')['rows']) == 12
    canvas = HERE / 'patient-speech-reliability-reassessment-m16.canvas.tsx'
    managed = Path('/Users/ohs/.cursor/projects/empty-window/canvases') / canvas.name
    assert canvas.read_text().rstrip('\n') == managed.read_text().rstrip('\n')
    result = subprocess.run(['/Users/ohs/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node',
                             str(HERE / 'check_canvas.cjs')], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == 'TypeScript diagnostics: 0'
    status = read(ROOT / 'collaboration/development-status.json')
    assert status['actual_synthetic_patient_generation_calls'] == 591
    assert status['completed_development_dialogues'] == 99
    assert status['completed_development_numeric_rating_outputs'] == 480
    assert status['development_reviews']['calls'] == 287
    assert status['strategy_mentoring']['calls'] == 12
    assert status['research_judgment_calls'] == 0 and status['prompt_revision_paused_by_user']
    assert (HERE / 'mapping-interpretation-addendum.md').is_file()
    checks = dict(timestamp_utc=datetime.now(timezone.utc).isoformat(),
                  source_scope_files_unchanged=len(scope['file_sha256']),
                  final_files_byte_hashes_unchanged=len(scope['protected_final_files_sha256']),
                  all_M15_previous_manifest_files_unchanged=len(old['file_sha256']),
                  frozen_packets_role_analysis_and_original_mapping_unchanged=True,
                  actual_Claude_high_strategy_responses=2, distinct_Claude_transport_sessions=True,
                  actual_Astra_response_files=2, Astra_requested_model='gpt-6.2-astra',
                  Astra_backend_snapshot_independently_verified=False,
                  source_matrices_and_statistics_recomputed_without_overwriting_analysis=True,
                  all8_group_pair_counts_independently_recomputed=True,
                  original_12record_mapping_preserved_with_public_interpretation_corrections=True,
                  actual_new_patient_outputs=0, actual_new_numeric_ratings=0,
                  patient_prompt_or_judge_criteria_changes=False,
                  natural_fine_total_score_ranking_reliability_established=False,
                  clinical_validation=False, final12_content_read=False, final720_executed=False,
                  canvas_typescript_diagnostics=0, canvas_open_status='queued_not_visual_render_verified',
                  source_and_managed_canvas_identical_except_terminal_newline=True,
                  cumulative_synthetic_generation_calls=591, cumulative_generated_dialogues=99,
                  cumulative_Realism_ratings=480, cumulative_review_CLI_invocations=287,
                  paid_API_calls=0, new_models_downloaded=0, packages_installed=0)
    checks['file_sha256'] = {str(f.relative_to(ROOT)): sha(f) for f in sorted(HERE.rglob('*'))
                            if f.is_file() and f.name != 'verification.json' and '__pycache__' not in f.parts}
    dump(HERE / 'verification.json', checks)
    print('Verified M16: 8 strata, 2 actual Claude high responses, 2 Astra reports; prior sources/prompts/final17 unchanged; M15 manifest preserved; TypeScript0.')


if __name__ == '__main__':
    main()
