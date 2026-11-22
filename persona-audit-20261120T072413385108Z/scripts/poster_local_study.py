"""Bounded local continuation of the frozen six-condition experiment.

Only installed qwen3:14b on loopback Ollama. No paid API, pulls or packages.
New responses are isolated from all historical runs; every attempt is retained.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import re
import time
import urllib.request

from freeze_main_inputs import build

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/poster-local-20261117'
BASE = 'http://127.0.0.1:11434'
MODEL = 'qwen3:14b'
WORD = re.compile(r"[A-Za-z0-9]+(?:['’\-][A-Za-z0-9]+)*")


def now():
    return datetime.now(timezone.utc).isoformat()


def fp(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def save(path, value, frozen=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    if frozen and path.exists():
        if read(path) != value:
            raise ValueError('Immutable artifact changed: ' + str(path))
        return
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)


def api(route, payload=None, timeout=10):
    if route not in ('/api/version', '/api/tags', '/api/show', '/api/ps', '/api/chat'):
        raise ValueError('Route not allowed')
    request = urllib.request.Request(BASE + route,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=timeout) as response:
        raw = response.read(4_000_001)
    if len(raw) > 4_000_000:
        raise ValueError('Response exceeds limit')
    return json.loads(raw)


def runtime():
    tags = api('/api/tags')['models']
    selected = next(m for m in tags if m['name'] == MODEL)
    detail = api('/api/show', {'model': MODEL})
    return {'model': MODEL, 'digest': selected['digest'], 'details': selected['details'],
        'server': api('/api/version'), 'template_sha256': fp(detail.get('template', '')),
        'parameters_sha256': fp(detail.get('parameters', '')), 'template': detail.get('template'),
        'parameters': detail.get('parameters'), 'capabilities': detail.get('capabilities'),
        'model_info': detail.get('model_info'), 'active_before': api('/api/ps')}


def prepare():
    rows, payloads = build()
    files = [*sorted((ROOT / 'config/main-freeze-v01').glob('*')),
        ROOT / 'share/main-comparison-v01/AI판독기준_v1.md', Path(__file__)]
    spec = {'id': 'poster-local-20261117', 'authorization_date': '2026-11-17',
        'authorization': 'User requested autonomous local research using existing Mac and Qwen-14B.',
        'design': 'Previously frozen six-condition PSYCHE-style prompt port, newly executed in isolation.',
        'scope': 'Exploratory AI-assisted textual observation; no independent human/clinical validation.',
        'planned_calls': {'development': 24, 'confirmation': 96},
        'case_count': {'development': 1, 'confirmation': 4},
        'generation_unit': 'Independent first response; NOT a multi-turn interview.',
        'context': 'Full shared profile and one question; fresh context per request; no truncation of context.',
        'analysis': 'Equal case weighting; matched question/seed blocks; do not treat outputs as independent patients.',
        'primary_observation': 'Evidence-backed unclear transition between separately interpretable adjacent clauses.',
        'rater': 'Current assistant with condition identifiers removed; not independent or clinically validated.',
        'rating_categories': ['yes', 'no', 'uncertain', 'unassessable'],
        'missing_policy': 'Uncertain, unassessable and missing remain unknown; report conservative bounds.',
        'primary_contrast': '(C4-C3)-(C2-C1); also C4-C2 and C5 control-positive rate.',
        'secondary': ['Question response', 'Within-clause intelligibility', 'Supplied-fact preservation',
            'Word count', 'Literal label leakage', 'Repetition'],
        'gate': 'First six development responses: all completed/nonempty/nontruncated, English text, no template dump. Target-feature presence is NOT a gate.',
        'historical_outputs_reused': 0, 'new_model_downloads': 0, 'paid_api_calls': 0,
        'retry_policy': 'No automatic retries, best-of selection or overwrites. Failed attempts stay recorded.',
        'input_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        'requests_sha256': fp([{'row': r, 'payload': payloads[r['id']]} for r in rows])}
    save(OUT / 'protocol.json', spec, frozen=True)
    save(OUT / 'requests.json', [{'row': r, 'payload': payloads[r['id']]} for r in rows], frozen=True)
    return rows, payloads


def measures(text):
    words = WORD.findall(text)
    toks = [w.lower() for w in words]
    trigrams = list(zip(toks, toks[1:], toks[2:]))
    return {'words': len(words), 'within_100_140': 100 <= len(words) <= 140,
        'trigram_repeat_rate': 1 - len(set(trigrams)) / len(trigrams) if trigrams else None,
        'label_hits': re.findall(r'\b(?:schizophren\w*|psychosis|psychotic|derailment|tangentiality|MFC|PSYCHE|thought.process)\b', text, re.I),
        'cjk_characters': len(re.findall(r'[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]', text)),
        'template_dump': bool(re.search(r'SECTION [123]|MFC.Profile|MFC.Behavior|HOW YOU SPEAK', text, re.I))}


def analyze():
    rows, payloads = prepare()
    data = []
    for row in rows:
        path = OUT / 'responses' / (row['id'] + '.json')
        if not path.exists():
            continue
        result = read(path)
        if result['request_sha256'] != fp(payloads[row['id']]):
            raise ValueError('Request mismatch')
        text = result.get('raw', {}).get('message', {}).get('content', '')
        data.append({**row, 'status': result['status'], 'text': text,
            'text_sha256': hashlib.sha256(text.encode()).hexdigest(), **measures(text),
            'seconds': result.get('seconds'), 'eval_count': result.get('raw', {}).get('eval_count'),
            'prompt_eval_count': result.get('raw', {}).get('prompt_eval_count')})
    save(OUT / 'measurements.json', data)
    summaries = []
    for split in ('development', 'confirmation'):
        for condition in [f'C{i}' for i in range(6)]:
            d = [r for r in data if r['split'] == split and r['condition'] == condition]
            if d:
                summaries.append({'split': split, 'condition': condition, 'n': len(d),
                    'statuses': dict(Counter(r['status'] for r in d)),
                    'mean_words': sum(r['words'] for r in d) / len(d),
                    'length_compliant': sum(r['within_100_140'] for r in d),
                    'label_response_count': sum(bool(r['label_hits']) for r in d),
                    'template_dumps': sum(r['template_dump'] for r in d)})
    save(OUT / 'technical-summary.json', summaries)
    # Opaque identifiers; only the masked file is read during primary annotation.
    for split in ('development', 'confirmation'):
        d = [r for r in data if r['split'] == split]
        random.Random(261117 if split == 'development' else 261118).shuffle(d)
        masked, key = [], []
        for i, r in enumerate(d, 1):
            ident = ('D' if split == 'development' else 'E') + f'{i:03d}'
            question = payloads[r['id']]['messages'][-1]['content']
            masked.append({'id': ident, 'question': question, 'text': r['text'], 'sha256': r['text_sha256']})
            key.append({'blind_id': ident, **{k: r[k] for k in ('id', 'case', 'condition', 'question', 'seed')}})
        save(OUT / f'{split}-masked.json', masked)
        save(OUT / f'{split}-key.json', key)
    elapsed = sum(r.get('seconds') or 0 for r in data)
    total = {'recorded': len(data), 'statuses': dict(Counter(r['status'] for r in data)),
        'generation_seconds': round(elapsed, 2), 'prompt_eval_tokens': sum(r['prompt_eval_count'] or 0 for r in data),
        'output_tokens': sum(r['eval_count'] or 0 for r in data),
        'paid_api_calls': 0, 'downloads': 0, 'clinical_ratings': 0}
    save(OUT / 'progress.json', total)
    return total


def run(split, limit):
    rows, payloads = prepare()
    current = runtime()
    lock_path = OUT / 'runtime.json'
    if lock_path.exists():
        lock = read(lock_path)
        for key in ('model', 'digest', 'details', 'server', 'template_sha256', 'parameters_sha256'):
            if current[key] != lock[key]:
                raise ValueError('Runtime changed: ' + key)
    else:
        save(lock_path, current, frozen=True)
    if split == 'confirmation':
        gate = read(OUT / 'technical-gate.json')
        if not gate.get('passed'):
            raise ValueError('Development technical gate must pass first')
        dev = [read(OUT / 'responses' / (r['id'] + '.json')) for r in rows if r['split'] == 'development']
        if not all(r['status'] == 'completed' for r in dev):
            raise ValueError('Development incomplete')
    chosen = [r for r in rows if r['split'] == split]
    random.Random(261117).shuffle(chosen)
    # First six span every condition at the same question and seed.
    if split == 'development':
        first = sorted([r for r in chosen if r['question'] == 1 and r['seed'] == 20261105], key=lambda r: r['condition'])
        chosen = first + [r for r in chosen if r not in first]
    count = 0
    for row in chosen:
        path = OUT / 'responses' / (row['id'] + '.json')
        if path.exists():
            if read(path)['request_sha256'] != fp(payloads[row['id']]):
                raise ValueError('Saved request mismatch')
            continue
        if count >= limit:
            break
        request_path = OUT / 'attempts' / (row['id'] + '.json')
        if request_path.exists():
            raise ValueError('Unresolved attempt: review before retrying ' + row['id'])
        save(request_path, {'started_at_utc': now(), 'request_sha256': fp(payloads[row['id']]),
            'payload': payloads[row['id']]}, frozen=True)
        started = time.monotonic()
        result = {'id': row['id'], 'request_sha256': fp(payloads[row['id']]), 'started_at_utc': now()}
        try:
            raw = api('/api/chat', payloads[row['id']], timeout=240)
            result['raw'] = raw
            result['status'] = ('provider_error' if raw.get('error') else 'model_mismatch' if raw.get('model') != MODEL else
                'incomplete' if not raw.get('done') else 'truncated' if raw.get('done_reason') == 'length' else
                'empty' if not raw.get('message', {}).get('content', '').strip() else 'completed')
        except Exception as exc:
            result.update(status='request_error', error=type(exc).__name__ + ': ' + str(exc))
        result['seconds'] = round(time.monotonic() - started, 3)
        result['finished_at_utc'] = now()
        save(path, result, frozen=True)
        count += 1
        print(json.dumps({'split': split, 'new_call': count, 'status': result['status'], 'seconds': result['seconds']}) , flush=True)
        if result['status'] != 'completed':
            break
    print(json.dumps(analyze()), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['prepare', 'metadata', 'run', 'analyze'])
    p.add_argument('--split', choices=['development', 'confirmation'], default='development')
    p.add_argument('--limit', type=int, default=6)
    args = p.parse_args()
    if args.action == 'prepare':
        rows, _ = prepare()
        print('Frozen', len(rows), 'requests; no inference.')
    elif args.action == 'metadata':
        r = runtime()
        save(OUT / 'runtime.json', r, frozen=True)
        print(json.dumps({k: r[k] for k in ('model', 'digest', 'details', 'server', 'template_sha256')}))
    elif args.action == 'run':
        if not 1 <= args.limit <= 96:
            p.error('limit must be 1..96')
        run(args.split, args.limit)
    else:
        print(json.dumps(analyze()))


if __name__ == '__main__':
    main()
