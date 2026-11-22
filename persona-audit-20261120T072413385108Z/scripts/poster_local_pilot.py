"""Run the preselected 24-response assessment block, not the full 96-response study."""
import argparse
from collections import Counter
import json
import random
import time

import poster_local_study as s


def prepare():
    rows, payloads = s.prepare()
    selected = [r for r in rows if r['split'] == 'confirmation' and r['expert_plan']]
    assert len(selected) == 24
    assert Counter(r['case'] for r in selected) == {f'H0{i}': 6 for i in range(1, 5)}
    assert Counter(r['condition'] for r in selected) == {f'C{i}': 4 for i in range(6)}
    assert len({(r['question'], r['seed']) for r in selected}) == 4
    plan = {'id': 'bounded-feasibility-amendment-20261117',
        'frozen_before_assessment_generation': True,
        'reason': 'User requested an initial autonomous local study to inform the next direction, not an entire poster confirmatory study. Scope is bounded before assessment outcomes.',
        'actual_scope': '6 fresh technical-development responses plus 24 preselected matched assessment responses.',
        'candidate_full_design_requests': 120,
        'selected_assessment_ids': [r['id'] for r in selected],
        'selection': 'Reuse the 24 consultation slots fixed in main-freeze-v01 before this session: one question/seed block per case, all six conditions; four question/seed combinations represented once.',
        'analysis_denominator': '4 cases x 6 conditions = 24; not a random sample of the 96 candidate responses.',
        'inference_limit': 'No within-case replication; four closely templated fictional cases; exploratory assistant ratings, not clinical validation.',
        'development_gate_n': 6,
        'gate_does_not_depend_on_target_feature_presence': True,
        'ratings': 'Primary B/A/C observation by current assistant after removing condition metadata. No independent person, no new Qwen judge.',
        'fact_audit': 'Supplied-fact literal/alias presence is secondary and never treated as clinical truth or a contradiction detector.',
        'other_candidate_requests': 'Not released by this pilot; not missing observations in its denominator.',
        'paid_api_calls': 0, 'model_downloads': 0,
        'parent_protocol_sha256': s.fp(s.read(s.OUT / 'protocol.json'))}
    s.save(s.OUT / 'pilot-amendment.json', plan, frozen=True)
    return selected, payloads


def run():
    selected, payloads = prepare()
    gate = s.read(s.OUT / 'technical-gate.json')
    if not gate.get('passed') or gate.get('responses_reviewed') != 6:
        raise ValueError('Six-response technical review required')
    lock = s.read(s.OUT / 'runtime.json')
    current = s.runtime()
    for key in ('model', 'digest', 'details', 'server', 'template_sha256', 'parameters_sha256'):
        if current[key] != lock[key]:
            raise ValueError('Runtime changed: ' + key)
    random.Random(2026111724).shuffle(selected)
    for i, row in enumerate(selected, 1):
        path = s.OUT / 'responses' / (row['id'] + '.json')
        payload = payloads[row['id']]
        if path.exists():
            if s.read(path)['request_sha256'] != s.fp(payload):
                raise ValueError('Saved request mismatch')
            continue
        attempt = s.OUT / 'attempts' / (row['id'] + '.json')
        if attempt.exists():
            raise ValueError('Unresolved attempt; no automatic retry')
        s.save(attempt, {'started_at_utc': s.now(), 'request_sha256': s.fp(payload), 'payload': payload}, frozen=True)
        started = time.monotonic()
        result = {'id': row['id'], 'request_sha256': s.fp(payload), 'started_at_utc': s.now()}
        try:
            raw = s.api('/api/chat', payload, timeout=240)
            result['raw'] = raw
            result['status'] = ('provider_error' if raw.get('error') else 'model_mismatch' if raw.get('model') != s.MODEL else
                'incomplete' if not raw.get('done') else 'truncated' if raw.get('done_reason') == 'length' else
                'empty' if not raw.get('message', {}).get('content', '').strip() else 'completed')
        except Exception as exc:
            result.update(status='request_error', error=type(exc).__name__ + ': ' + str(exc))
        result['seconds'] = round(time.monotonic() - started, 3)
        result['finished_at_utc'] = s.now()
        s.save(path, result, frozen=True)
        print(json.dumps({'assessment_response': i, 'status': result['status'], 'seconds': result['seconds']}), flush=True)
        if result['status'] != 'completed':
            break
    print(json.dumps(s.analyze()), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['prepare', 'run'])
    a = p.parse_args()
    if a.action == 'prepare':
        selected, _ = prepare()
        print('Pilot assessment sample frozen:', len(selected), 'responses, 4 matched six-condition blocks.')
    else:
        run()
