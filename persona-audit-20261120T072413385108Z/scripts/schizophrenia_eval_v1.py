"""Offline aggregation of frozen LLM observations; never calls a model.

Manifest: planned opaque items with case_id, condition, repeat, targets,
transcript, fact_checks and interaction_checks. Observations are joined only
after blind annotation. Unknown judgments remain bounded, not imputed as absent.
"""
from collections import defaultdict
import argparse
import json
import re
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / 'config/schizophrenia-eval-v1.json'


def load(path):
    return json.loads(Path(path).read_text())


def bucket():
    return defaultdict(list)


def interval(value, minimum=0, maximum=1):
    return (minimum, maximum) if value is None else (value, value)


def summarize_values(rows):
    """Each row is (case_id, lower, upper, known). Cases have equal weight."""
    if not rows:
        return None
    by_case = defaultdict(list)
    for case, lo, hi, known in rows:
        by_case[case].append((lo, hi, known))
    per_case = {case: [mean(v[j] for v in values) for j in (0, 1)]
                for case, values in sorted(by_case.items())}
    return {'lower': mean(v[0] for v in per_case.values()),
            'upper': mean(v[1] for v in per_case.values()),
            'known_fraction': sum(r[3] for r in rows) / len(rows),
            'check_count': len(rows), 'case_count': len(by_case), 'case_bounds': per_case}


def add_metric(store, key, case, value, maximum=1):
    lo, hi = interval(value, maximum=maximum)
    store[key].append((case, lo, hi, value is not None))


def validate(data, allow_fixture=False):
    if data.get('kind') == 'arithmetic_fixture':
        if not allow_fixture:
            raise ValueError('Arithmetic fixture is not research data; explicit --allow-fixture required')
    elif data.get('kind') != 'research':
        raise ValueError('Explicit dataset kind required')
    if data.get('evaluation_id') != 'schizophrenia-eval-v1':
        raise ValueError('Wrong evaluation version')
    if not data.get('judge', {}).get('identifier') or not data.get('judge', {}).get('rubric_sha256'):
        raise ValueError('Actual evaluator identifier and rubric hash required')
    features = load(SPEC)['primary_features']
    plan = data['manifest']
    ids = [r['item_id'] for r in plan]
    if any(not re.fullmatch(r'J[0-9]{4,}', ident) for ident in ids):
        raise ValueError('Use opaque IDs J0001 etc.; do not expose condition in judge item IDs')
    records = data['observations']
    record_ids = [r['item_id'] for r in records]
    if len(set(ids)) != len(ids) or len(set(record_ids)) != len(record_ids):
        raise ValueError('Duplicate item ID')
    if set(ids) != set(record_ids):
        raise ValueError('Missing or extra planned observations; never silently drop failures')
    cells = [(p['case_id'], p['condition'], p['repeat']) for p in plan]
    if len(set(cells)) != len(cells):
        raise ValueError('Duplicate case/condition/repeat cell')
    conditions = {p['condition'] for p in plan}
    if len(conditions) < 2:
        raise ValueError('At least two comparison conditions required')
    case_plans = defaultdict(list)
    for p in plan:
        case_plans[p['case_id']].append(p)
        if set(p['targets']) != set(features):
            raise ValueError('All primary targets must be explicit; null means unspecified')
        for f in features:
            if p['targets'][f] is not None and (type(p['targets'][f]) is not int or p['targets'][f] not in range(4)):
                raise ValueError('Targets must be 0..3 or null')
    for case, rows in case_plans.items():
        signatures = {json.dumps({k: p[k] for k in ('targets', 'fact_checks', 'interaction_checks')}, sort_keys=True) for p in rows}
        if len(signatures) != 1:
            raise ValueError('Case targets/checks differ across conditions or repeats: ' + case)
        repeats = [{p['repeat'] for p in rows if p['condition'] == c} for c in conditions]
        if any(not r or r != repeats[0] for r in repeats):
            raise ValueError('Unbalanced planned case-condition repeats: ' + case)
    for f in features:
        targets = [p['targets'][f] for p in plan]
        if not any(v is not None and v > 0 for v in targets) or 0 not in targets:
            raise ValueError('Each primary feature needs positive and explicit-absent cases: ' + f)
    by_id = {r['item_id']: r for r in records}
    for p in plan:
        r = by_id[p['item_id']]
        if set(r['observed']) != set(features):
            raise ValueError('Observed feature keys differ')
        patient_turns = {t['turn_id']: t['text'] for t in p['transcript'] if t['speaker'] == 'patient'}
        if r['generation_status'] not in ('completed', 'failed', 'truncated'):
            raise ValueError('Unknown generation status')
        for f, obs in r['observed'].items():
            v = obs['severity']
            if v is not None and (type(v) is not int or v not in range(4)):
                raise ValueError('Observed severity must be 0..3 or null')
            if r['generation_status'] != 'completed' and v is not None:
                raise ValueError('Failed/truncated output must remain unknown')
            if not obs.get('reason'):
                raise ValueError('Observation reason required')
            if v is not None and not obs.get('evidence'):
                raise ValueError('Definite observation requires patient evidence')
            for ev in obs.get('evidence', []):
                if not ev.get('quote') or ev['quote'] not in patient_turns.get(ev['turn_id'], ''):
                    raise ValueError('Evidence is not an exact quote in the stated patient turn')
        for field, manifest_field, allowed in [
            ('facts', 'fact_checks', {'correct', 'contradicted', 'omitted', 'uncertain', 'not_applicable'}),
            ('interactions', 'interaction_checks', {'pass', 'fail', 'uncertain', 'not_applicable'})]:
            actual = r[field]
            if len({x['id'] for x in actual}) != len(actual) or {x['id'] for x in actual} != {x['id'] for x in p[manifest_field]}:
                raise ValueError('Check inventory mismatch')
            for check in actual:
                if check['status'] not in allowed or not check.get('reason'):
                    raise ValueError('Invalid check status/reason')
                if r['generation_status'] != 'completed' and check['status'] not in ('uncertain', 'not_applicable'):
                    raise ValueError('Checks for failed generation must remain unknown')
                if check['status'] in ('correct', 'contradicted', 'pass', 'fail') and not check.get('evidence'):
                    raise ValueError('Definite check requires evidence')
                for ev in check.get('evidence', []):
                    if not ev.get('quote') or ev['quote'] not in patient_turns.get(ev['turn_id'], ''):
                        raise ValueError('Check quote mismatch')
    return features, plan, by_id


def aggregate(data, allow_fixture=False):
    features, plan, by_id = validate(data, allow_fixture)
    stores = defaultdict(bucket)
    for p in plan:
        r = by_id[p['item_id']]
        store, case = stores[p['condition']], p['case_id']
        for f in features:
            target, observed = p['targets'][f], r['observed'][f]['severity']
            if target is None:
                continue
            present = None if observed is None else int(observed >= 1)
            if target > 0:
                add_metric(store, 'target_realization/' + f, case, present)
                error = None if observed is None else abs(observed - target)
                add_metric(store, 'severity_error/' + f, case, error, max(target, 3 - target))
            else:
                add_metric(store, 'unwanted_expression/' + f, case, present)
        for check in r['facts']:
            definition = next(c for c in p['fact_checks'] if c['id'] == check['id'])
            if not definition['required']:
                continue
            status = check['status']
            known = status not in ('uncertain', 'not_applicable')
            add_metric(store, 'fact_preservation', case, int(status == 'correct') if known else None)
            add_metric(store, 'fact_contradiction', case, int(status == 'contradicted') if known else None)
            add_metric(store, 'fact_preservation/' + check['id'], case, int(status == 'correct') if known else None)
        for check in r['interactions']:
            definition = next(c for c in p['interaction_checks'] if c['id'] == check['id'])
            if not definition['required']:
                continue
            status = check['status']
            value = None if status in ('uncertain', 'not_applicable') else int(status == 'pass')
            add_metric(store, 'interaction_adherence', case, value)
            add_metric(store, 'interaction_adherence/' + check['id'], case, value)
    output = {}
    for condition, store in sorted(stores.items()):
        metrics = {k: summarize_values(v) for k, v in sorted(store.items())}
        for name in ('target_realization', 'unwanted_expression', 'severity_error'):
            values = [metrics[name + '/' + f] for f in features]
            metrics[name + '/macro'] = {
                'lower': mean(v['lower'] for v in values), 'upper': mean(v['upper'] for v in values),
                'known_fraction': mean(v['known_fraction'] for v in values),
                'feature_count': len(features), 'equal_feature_weight': True}
        output[condition] = metrics
    return {'evaluation_id': 'schizophrenia-eval-v1', 'kind': data['kind'],
        'actual_judge': data['judge'], 'clinical_validation': False,
        'bounds_are_confidence_intervals': False, 'metrics_are_proportions_except_severity_error': True,
        'case_count': len({p['case_id'] for p in plan}), 'planned_items': len(plan),
        'technical_completion': {c: sum(by_id[p['item_id']]['generation_status'] == 'completed' for p in plan if p['condition'] == c) /
            sum(p['condition'] == c for p in plan) for c in stores}, 'conditions': output}


def packets(data):
    """Prepare blind-stage and contextual-stage inputs; never expose targets in stage 1."""
    one, two = [], []
    for p in data['manifest']:
        one.append({'item_id': p['item_id'], 'transcript': p['transcript']})
        two.append({'item_id': p['item_id'], 'transcript': p['transcript'],
                    'fact_checks': p['fact_checks'], 'interaction_checks': p['interaction_checks']})
    return one, two


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--allow-fixture', action='store_true')
    args = parser.parse_args()
    result = aggregate(load(args.input), args.allow_fixture)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'kind': result['kind'], 'cases': result['case_count'], 'items': result['planned_items'],
                      'conditions': list(result['conditions']), 'model_calls': 0}))


if __name__ == '__main__':
    main()
