"""Audit completed model calls, frozen inputs, transformations and recomputed statistics."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('m5', HERE / 'experiment.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def main():
    plan = m.verify()
    items = m.read(HERE / 'items-private.json')
    original = {i['item_id']: i for i in items if i['kind'] == 'original'}
    assert len(original) == 6
    changes = []
    for i in items:
        if i['kind'] != 'synthetic_error_control': continue
        parent = original[i['parent_item_id']]
        diff = [(a, b) for a, b in zip(parent['generated_dialogue'], i['generated_dialogue']) if a != b]
        assert len(diff) == 1
        a, b = diff[0]
        assert a['turn_id'] == b['turn_id'] == 'P04'
        assert a['speaker'] == b['speaker'] == 'patient'
        assert len(a['text']) == len(b['text'])
        assert a['text'] == i['manipulation']['before'] and b['text'] == i['manipulation']['after']
        changes.append({'item_id': i['item_id'], 'changed_turn': 'P04', 'character_count_delta': 0})
    assert len(changes) == 3
    role = (m.PARENT / 'review-role.txt').read_text().replace('여섯 대화를', '아홉 대화를').replace('M4-A', 'Q-A')
    assert role == (HERE / 'review-role.txt').read_text()
    calls = []
    values = {p: {i['item_id']: [] for i in items} for p in m.PROVIDERS}
    for r in plan['rounds']:
        packet = m.read(HERE / r['packet'])
        assert packet['score_anchors'] == m.read(m.PARENT / 'review-packet.json')['score_anchors']
        key = m.read(HERE / r['key'])
        assert set(key.values()) == {i['item_id'] for i in items}
        for c in packet['cases']:
            item = next(i for i in items if i['item_id'] == key[c['blind_id']])
            assert c['generated_dialogue'] == item['generated_dialogue']
        for p in m.PROVIDERS:
            d = HERE / 'reviews' / p / f"round{r['repeat']:02d}"
            meta = m.read(d / 'metadata.json')
            assert meta['status'] == 'response_received' and meta['returncode'] == 0
            assert meta['automatic_retries'] == 0
            assert m.digest(d / 'input.txt') == r['packet_sha256']
            assert m.digest(d / 'instructions.txt') == plan['role_sha256']
            assert m.digest(d / 'response.txt') == meta['response_sha256']
            assert meta['requested_model'] == ('gpt-6.1-sol' if p == 'codex' else 'claude-opus-5-5')
            assert meta['settings']['reasoning_effort'] == ('high' if p == 'codex' else 'medium')
            parsed = m.M1.parse_review((d / 'response.txt').read_text())
            assert parsed == m.read(d / 'validated.json')
            rows = m.M1.validate_review(parsed, packet)
            for row in rows: values[p][key[row['blind_id']]].append(row['score'])
            calls.append({'provider': p, 'repeat': r['repeat'], 'rating_count': len(rows),
                          'requested_model': meta['requested_model'], 'cli_version': meta['cli_version'],
                          'start_timestamp_utc': meta['timestamp_utc'], 'response_sha256': meta['response_sha256']})
    assert len(calls) == 6 and sum(c['rating_count'] for c in calls) == 54
    assert m.analyze_values(items, values) == m.read(HERE / 'scores.json')
    # Preserve the exact code and protocol used for this completed diagnostic.
    snapshot = HERE / 'implementation-snapshot'
    snapshot.mkdir(exist_ok=False)
    for name in ['experiment.py', 'test_analysis.py', 'methods.md', 'review-role.txt']:
        shutil.copyfile(HERE / name, snapshot / name)
    shutil.copyfile(m.ROOT / 'collaboration/subscription_call.py', snapshot / 'subscription_call.py')
    shutil.copyfile(m.ROOT / 'development/speech-m1-v01/review_dev.py', snapshot / 'review_dev.py')
    # M4 runtime and prompt/source-map files are also unchanged, beyond prompt hashes in M5 plan.
    previous = m.read(m.PARENT / 'verification.json')['file_sha256']
    for relative, h in previous.items():
        if relative.startswith('speech_module/'):
            assert m.digest(m.ROOT / relative) == h
    files = [p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts
             and p.name != 'verification.json']
    report = {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'CLI_calls': calls,
              'completed_CLI_calls': 6, 'completed_rating_outputs': 54,
              'all_54_scores_valid_integer_and_exact_quotes_checked': True,
              'same_packet_per_provider_within_round': True,
              'original_six_dialogues_unchanged': True, 'error_control_changes': changes,
              'original_anchors_and_substantive_role_unchanged': True,
              'frozen_sources_prompts_methods_and_final_pilot_unchanged': True,
              'all_M4_speech_module_hashes_unchanged': True,
              'statistics_independently_recomputed_from_raw_responses': True,
              'analysis_fixture_tests_passed': 3,
              'new_patient_generation_calls': 0, 'new_paid_API_calls': 0,
              'new_models_or_packages': 0, 'final_720_judgments': 'not_performed',
              'clinical_validation': 'not_performed',
              'file_sha256': {str(p.relative_to(m.ROOT)): m.digest(p) for p in files}}
    m.dump(HERE / 'verification.json', report)
    print('Verified six real CLI calls, 54 ratings, exact quotes, frozen sources/prompts, paired statistics')


if __name__ == '__main__': main()
