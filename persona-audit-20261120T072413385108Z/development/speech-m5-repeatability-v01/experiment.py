"""Frozen 9-dialogue diagnostic, 2 official subscription judges x 3 independent sessions."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import statistics
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PARENT = ROOT / 'development/speech-m4-v02-v04-compare-v01'
sys.path.insert(0, str(ROOT))
from collaboration.subscription_call import call_once, dump

SPEC = importlib.util.spec_from_file_location('m1review', ROOT / 'development/speech-m1-v01/review_dev.py')
M1 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M1)
PROVIDERS = ('codex', 'claude')
EDITS = {
    'DEV-M0-01': ('어머니하고 같이 살아요.', '아버지하고 같이 살아요.', 'living'),
    'DEV-M0-02': ('누나가 와보라고 했어요.', '엄마가 와보라고 했어요.', 'visit'),
    'DEV-M0-03': ('아니요, 아버지랑 같이 살고 있어요.', '아니요, 어머니랑 같이 살고 있어요.', 'living'),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def freeze():
    previous = read(PARENT / 'verification.json')['file_sha256']
    parent_packet = read(PARENT / 'review-packet.json')
    parent_key = read(PARENT / 'review-key-private.json')
    items = []
    source_files = [PARENT / 'review-packet.json', PARENT / 'review-key-private.json',
                    PARENT / 'review-role.txt', PARENT / 'verification.json']
    for item in parent_packet['cases']:
        meta = parent_key[item['blind_id']]
        source = PARENT / 'runs' / meta['case_id'] / meta['condition'] / 'transcript.json'
        assert digest(source) == meta['transcript_sha256'] == previous[str(source.relative_to(ROOT))]
        assert read(source)['generated_dialogue'] == item['generated_dialogue']
        ident = meta['case_id'] + '-' + meta['condition']
        value = {'item_id': ident, 'case_id': meta['case_id'], 'condition': meta['condition'],
                 'kind': 'original', 'profile_ref': item['profile_ref'],
                 'generated_dialogue': deepcopy(item['generated_dialogue']),
                 'source_path': str(source.relative_to(ROOT)), 'source_sha256': digest(source)}
        items.append(value)
        source_files.append(source)
        if meta['condition'] == 'v02':
            before, after, fact = EDITS[meta['case_id']]
            variant = deepcopy(value)
            variant.update(item_id=meta['case_id'] + '-error', kind='synthetic_error_control',
                           condition='error', parent_item_id=ident,
                           manipulation={'patient_turn_id': 'P04', 'before': before, 'after': after,
                                         'contradicted_fact_id': fact,
                                         'unicode_character_count_delta': len(after) - len(before),
                                         'provenance': 'deterministic_author_edit_not_model_generated_patient_output'})
            turn = next(t for t in variant['generated_dialogue'] if t['turn_id'] == 'P04')
            assert turn['speaker'] == 'patient' and turn['text'] == before and len(before) == len(after)
            turn['text'] = after
            assert sum(a != b for a, b in zip(value['generated_dialogue'], variant['generated_dialogue'])) == 1
            items.append(variant)
    assert len(items) == 9
    items.sort(key=lambda x: x['item_id'])
    dump(HERE / 'items-private.json', items)
    role = (PARENT / 'review-role.txt').read_text().replace('여섯 대화를', '아홉 대화를').replace('M4-A', 'Q-A')
    # Same substantive evaluator instructions and anchors; only count and example identifier change.
    (HERE / 'review-role.txt').write_text(role)
    rounds = []
    for repeat in range(1, 4):
        rng = random.Random(2026111800 + repeat)
        order = items.copy()
        while True:
            rng.shuffle(order)
            if all(a['profile_ref'] != b['profile_ref'] for a, b in zip(order, order[1:])):
                break
        numbers = rng.sample(range(100, 999), 9)
        cases, key = [], {}
        for number, value in zip(numbers, order):
            blind = f'Q{number}'
            cases.append({k: deepcopy(value[k]) for k in ('profile_ref', 'generated_dialogue')})
            cases[-1]['blind_id'] = blind
            key[blind] = value['item_id']
        packet = {'purpose': 'independent_development_realism_review',
                  'score_anchors': parent_packet['score_anchors'],
                  'anchor_adaptation': parent_packet['anchor_adaptation'],
                  'profiles': parent_packet['profiles'], 'cases': cases}
        path = HERE / f'round{repeat:02d}-packet.json'
        dump(path, packet)
        dump(HERE / f'round{repeat:02d}-key-private.json', key)
        assert len(path.read_bytes()) < 32000
        rounds.append({'repeat': repeat, 'packet': path.name, 'packet_sha256': digest(path),
                       'key': f'round{repeat:02d}-key-private.json',
                       'key_sha256': digest(HERE / f'round{repeat:02d}-key-private.json')})
    protected = sorted((ROOT / 'speech_module').glob('patient_v*.txt'))
    protected += sorted((ROOT / 'share/PATIENTSIM-reliability-pilot-v01').glob('*'))
    protected = [p for p in protected if p.is_file()]
    frozen = source_files + protected + [Path(__file__).resolve(), ROOT / 'collaboration/subscription_call.py',
                                        ROOT / 'development/speech-m1-v01/review_dev.py']
    dump(HERE / 'plan.json', {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'kind': 'small_development_repeatability_and_fact_error_sensitivity_diagnostic',
        'authorization': 'explicit_user_request_9_dialogues_two_models_three_repetitions_each',
        'original_dialogues': 6, 'deterministic_error_variants': 3,
        'new_patient_generation_calls': 0, 'models': {'codex': 'gpt-6.1-sol_high', 'claude': 'claude-opus-5-5_medium'},
        'calls_per_model': 3, 'total_CLI_calls_planned': 6, 'total_rating_outputs_planned': 54,
        'rounds': rounds, 'role_sha256': digest(HERE / 'review-role.txt'),
        'items_sha256': digest(HERE / 'items-private.json'),
        'frozen_file_sha256': {str(p.relative_to(ROOT)): digest(p) for p in frozen},
        'aggregation_prespecified': {
            'item': 'retain 3 integer scores per model, mean, min/max, sample SD, exact pair agreement (3 pairs)',
            'repeatability_primary': 'original 6 dialogues only; mean exact pair agreement, all-three-equal count, range>=2 count, score4 frequency',
            'error_sensitivity': 'per model, error minus source score per repeat and mean; strict negative is detection; ties are not detection; 3 matched source/error pairs',
            'combined': 'equal-model arithmetic mean across all 6 scores per item; original v04-minus-v02 per case and equal-case overall mean; do not pool M4 scores',
            'cross_judge': 'same-round exact agreement on original six dialogues, descriptive only',
            'inference': 'no p-values, confidence intervals, threshold-based reliability certification, clinical validation, or final superiority claim; 3 cases remain 3 clusters',
        },
        'manipulation': 'one P04 family referent replacement in each v02 source; identical Unicode length, other turns/profiles unchanged; all controls from v02 for a common simple source rule, not condition-balanced error sensitivity',
        'masking': 'version, source, artificial-error status, previous scores and other reviewer responses hidden; shared profiles/text may reveal related items; 9-item batch context can influence scores',
        'repeats': 'fresh no-persistence CLI processes; no preceding scores; fixed content but randomized order/opaque IDs per round; provider packets byte-identical within round',
        'settings_limit': 'server snapshot and temperature not exposed; independent sessions do not establish independent clinical judgments; no wrapper retry or best-of',
        'final_720_ratings': 'not_run_and_plan_unchanged', 'clinical_validation': 'not_performed',
    })
    print('Frozen 9 items, 3 randomized rounds, 6 CLI calls / 54 ratings; zero patient generation calls', flush=True)


def verify():
    plan = read(HERE / 'plan.json')
    for path, h in plan['frozen_file_sha256'].items():
        assert digest(ROOT / path) == h, 'Frozen source changed: ' + path
    assert digest(HERE / 'review-role.txt') == plan['role_sha256']
    assert digest(HERE / 'items-private.json') == plan['items_sha256']
    for r in plan['rounds']:
        assert digest(HERE / r['packet']) == r['packet_sha256']
        assert digest(HERE / r['key']) == r['key_sha256']
    return plan


def review(provider, repeat):
    plan = verify()
    r = next(v for v in plan['rounds'] if v['repeat'] == repeat)
    packet = read(HERE / r['packet'])
    directory = HERE / 'reviews' / provider / f'round{repeat:02d}'
    out = call_once(provider, (HERE / r['packet']).read_text(), (HERE / 'review-role.txt').read_text(), directory)
    result = M1.parse_review(out['text'])
    M1.validate_review(result, packet)
    dump(directory / 'validated.json', result)
    print(f'{provider} repeat {repeat}: 9 ratings and exact evidence quotes validated', flush=True)


def describe(scores):
    assert len(scores) == 3 and all(type(s) is int and 1 <= s <= 4 for s in scores)
    pairs = [(scores[i], scores[j]) for i in range(3) for j in range(i + 1, 3)]
    return {'scores': scores, 'mean': statistics.mean(scores), 'min': min(scores), 'max': max(scores),
            'range': max(scores) - min(scores), 'sample_sd': statistics.stdev(scores),
            'exact_pair_agreements': sum(a == b for a, b in pairs), 'pair_count': 3,
            'exact_pair_agreement': sum(a == b for a, b in pairs) / 3}


def analyze_values(items, values):
    rows = []
    for item in items:
        judges = {p: describe(values[p][item['item_id']]) for p in PROVIDERS}
        rows.append({'item_id': item['item_id'], 'case_id': item['case_id'], 'condition': item['condition'],
                     'kind': item['kind'], 'judges': judges,
                     'equal_model_mean': statistics.mean(judges[p]['mean'] for p in PROVIDERS)})
    original = [r for r in rows if r['kind'] == 'original']
    repeatability = {}
    for p in PROVIDERS:
        frequencies = Counter(s for r in original for s in r['judges'][p]['scores'])
        repeatability[p] = {'original_dialogues': 6, 'ratings': 18,
            'all_three_equal_count': sum(r['judges'][p]['range'] == 0 for r in original),
            'exact_pair_agreements': sum(r['judges'][p]['exact_pair_agreements'] for r in original),
            'pair_count': 18,
            'exact_pair_agreement': statistics.mean(r['judges'][p]['exact_pair_agreement'] for r in original),
            'range_at_least_2_count': sum(r['judges'][p]['range'] >= 2 for r in original),
            'score_frequencies': {str(s): frequencies[s] for s in range(1, 5)},
            'score4_fraction': frequencies[4] / 18}
    index = {r['item_id']: r for r in rows}
    pairs = []
    for item in items:
        if item['kind'] != 'synthetic_error_control':
            continue
        parent = index[item['parent_item_id']]
        error = index[item['item_id']]
        judges = {}
        for p in PROVIDERS:
            a, b = parent['judges'][p], error['judges'][p]
            deltas = [y - x for x, y in zip(a['scores'], b['scores'])]
            judges[p] = {'source_scores': a['scores'], 'error_scores': b['scores'],
                          'error_minus_source_by_repeat': deltas,
                          'mean_error_minus_source': statistics.mean(deltas),
                          'lower_count': sum(d < 0 for d in deltas),
                          'tie_count': sum(d == 0 for d in deltas),
                          'higher_count': sum(d > 0 for d in deltas)}
        pairs.append({'case_id': item['case_id'], 'source_item_id': parent['item_id'],
                      'error_item_id': error['item_id'], 'judges': judges,
                      'combined_error_minus_source': error['equal_model_mean'] - parent['equal_model_mean']})
    sensitivity = {}
    for p in PROVIDERS:
        sensitivity[p] = {'matched_pairs': 3,
            'pairs_with_strictly_lower_error_mean': sum(r['judges'][p]['mean_error_minus_source'] < 0 for r in pairs),
            'mean_error_minus_source': statistics.mean(r['judges'][p]['mean_error_minus_source'] for r in pairs),
            'same_round_comparisons': 9,
            **{k: sum(r['judges'][p][k] for r in pairs) for k in ('lower_count', 'tie_count', 'higher_count')}}
    version_pairs = []
    for case in sorted({r['case_id'] for r in rows}):
        a, b = index[case + '-v02'], index[case + '-v04']
        version_pairs.append({'case_id': case, 'v02_mean': a['equal_model_mean'], 'v04_mean': b['equal_model_mean'],
            'v04_minus_v02': b['equal_model_mean'] - a['equal_model_mean'],
            'judges': {p: {'v02_mean': a['judges'][p]['mean'], 'v04_mean': b['judges'][p]['mean'],
                'v04_minus_v02_by_repeat': [y-x for x,y in zip(a['judges'][p]['scores'], b['judges'][p]['scores'])]}
                for p in PROVIDERS}})
    version_means = {v: statistics.mean(r['equal_model_mean'] for r in original if r['condition'] == v) for v in ('v02', 'v04')}
    return {'kind': 'descriptive_development_diagnostic_not_clinical_validation', 'rating_outputs': 54,
            'items': rows, 'repeatability_originals_only': repeatability,
            'error_pairs': pairs, 'error_sensitivity': sensitivity,
            'combined_error_pairs_lower_count': sum(r['combined_error_minus_source'] < 0 for r in pairs),
            'original_version_pairs': version_pairs, 'original_version_means': version_means,
            'v04_minus_v02': version_means['v04'] - version_means['v02'],
            'same_round_cross_judge_original_exact_agreement': {
                'equal': sum(x == y for r in original for x,y in zip(r['judges']['codex']['scores'], r['judges']['claude']['scores'])),
                'total': 18},
            'independent_case_clusters': 3,
            'limits': 'Original-only repeatability; all error controls derived from v02. Ordered-score means are descriptive. Batch-context and model-family dependence remain. No formal reliability certification or general prompt superiority.'}


def aggregate():
    plan = verify()
    items = read(HERE / 'items-private.json')
    values = {p: {i['item_id']: [] for i in items} for p in PROVIDERS}
    for r in plan['rounds']:
        packet = read(HERE / r['packet'])
        key = read(HERE / r['key'])
        for p in PROVIDERS:
            directory = HERE / 'reviews' / p / f"round{r['repeat']:02d}"
            metadata = read(directory / 'metadata.json')
            assert metadata['input_sha256'] == r['packet_sha256']
            assert metadata['instructions_sha256'] == plan['role_sha256']
            assert metadata['status'] == 'response_received'
            response = (directory / 'response.txt').read_text()
            assert hashlib.sha256(response.encode()).hexdigest() == metadata['response_sha256']
            parsed = M1.parse_review(response)
            assert parsed == read(directory / 'validated.json')
            for row in M1.validate_review(parsed, packet):
                values[p][key[row['blind_id']]].append(row['score'])
    result = analyze_values(items, values)
    dump(HERE / 'scores.json', result)
    print(json.dumps({k: result[k] for k in ('rating_outputs', 'repeatability_originals_only', 'error_sensitivity',
          'original_version_means', 'v04_minus_v02')}, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('action', choices=['freeze', 'review', 'aggregate', 'verify'])
    ap.add_argument('--provider', choices=PROVIDERS)
    ap.add_argument('--repeat', type=int, choices=[1, 2, 3])
    a = ap.parse_args()
    if a.action == 'freeze': freeze()
    elif a.action == 'verify': verify(); print('Frozen files and all packets verified')
    elif a.action == 'aggregate': aggregate()
    elif a.provider and a.repeat: review(a.provider, a.repeat)
    else: ap.error('review requires --provider and --repeat')


if __name__ == '__main__':
    main()
