"""Collect independent forms for the frozen, authored nonclinical challenge only."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[2] / 'tobedoc2026/docs/2026-11-20-english-clinical-profile/reader.py'
MODEL = 'claude-opus-5-5'
SYSTEM = 'Return the completed form as a single JSON object.'
CASES = ('B14', 'B42', 'B37', 'B61', 'B28', 'B83', 'B75', 'B46', 'B19', 'B54', 'B32', 'B92')
BUILTINS = ('cc-plugin-agents-md', 'cc-plugin-privacy', 'cc-plugin-plugin-authoring')
SETTINGS = {'disableAllHooks': True, 'autoMemoryEnabled': False, 'enabledPlugins': {k+'@builtin':False for k in (*BUILTINS, 'cc-plugin-telemetry')}, 'forceLoginMethod': 'claudeai'}
FLAGS = ['--print', '--safe-mode', '--restricted', '--no-session-persistence', '--no-chrome',
         '--disable-slash-commands', '--setting-sources', '', '--settings', json.dumps(SETTINGS),
         '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}', '--permission-mode', 'dontAsk',
         '--tools', '', '--system-prompt', SYSTEM, '--model', MODEL, '--prompt-suggestions', 'false',
         '--output-format', 'stream-json', '--verbose', '--include-hook-events']


def original_reader():
    spec = importlib.util.spec_from_file_location('original_reader', SOURCE)
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    assert set(reader.EXAMPLES) == set(CASES)
    return reader


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def runtime():
    # Preserve only the account identity and normal system paths for the installed CLI's keychain lookup.
    env = {k: os.environ[k] for k in ('PATH', 'HOME', 'USER', 'LOGNAME', 'TMPDIR', 'LANG', 'LC_ALL') if k in os.environ}
    env.update({'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1', 'DISABLE_AUTOUPDATER': '1',
                'DISABLE_TELEMETRY': '1', 'DISABLE_ERROR_REPORTING': '1'})
    cli = shutil.which('claude', path=env['PATH'])
    with tempfile.TemporaryDirectory() as cwd:
        auth = subprocess.run([cli, '--safe-mode', 'auth', 'status', '--json'], cwd=cwd, env=env,
                              text=True, capture_output=True, timeout=30)
        obj = json.loads(auth.stdout)
        account = {k: obj.get(k) for k in ('loggedIn', 'authMethod', 'apiProvider', 'subscriptionType')}
        if auth.returncode or account['loggedIn'] is not True or account['authMethod'] != 'claude.ai' or account['apiProvider'] != 'firstParty' or account['subscriptionType'] != 'pro':
            raise RuntimeError('Expected existing first-party Claude Pro subscription: ' + repr(account))
        version = subprocess.check_output([cli, '--version'], env=env, cwd=cwd, text=True).strip()
    return cli, env, account, version


def record(sample, reader, cli, env):
    raw_dir = HERE / 'raw'
    receipts = HERE / 'receipts'
    forms = HERE / 'forms'
    for folder in (raw_dir, receipts, forms):
        folder.mkdir(exist_ok=True)
    path = raw_dir / (sample + '.jsonl')
    if path.exists():
        raise RuntimeError('Original trace exists; refusing to rerun ' + sample)
    data = reader.EXAMPLES[sample][0]
    packet = reader.packet(data)
    assert set(packet) == {'instructions', 'dialogue', 'form'} and packet['form'] == reader.blank_form() and packet['instructions'] == reader.RUBRIC
    payload = json.dumps(packet, ensure_ascii=False, indent=2) + '\n'
    start = datetime.now(timezone.utc).isoformat()
    with tempfile.TemporaryDirectory() as cwd, path.open('xb') as out, (raw_dir / (sample + '.stderr')).open('xb') as err:
        assert not any(Path(cwd).iterdir())
        p = subprocess.run([cli, *FLAGS], env=env, cwd=cwd, input=payload.encode(), stdout=out, stderr=err, timeout=600)
    events = [json.loads(s) for s in path.read_text().splitlines() if s.strip()]
    init = next((e for e in events if e.get('type') == 'system' and e.get('subtype') == 'init'), {})
    end = next((e for e in reversed(events) if e.get('type') == 'result'), {})
    assistant = [e['message'] for e in events if e.get('type') == 'assistant']
    models = sorted({a['model'] for a in assistant if a.get('model')})
    uses = [b['type'] for a in assistant for b in a.get('content', []) if 'tool' in b.get('type', '')]
    hooks = [e.get('subtype') for e in events if 'hook' in str(e.get('subtype', ''))]
    receipt = {'case_id': sample, 'started_utc': start, 'ended_utc': datetime.now(timezone.utc).isoformat(),
               'packet_sha256': sha256(payload.encode()).hexdigest(), 'raw_sha256': sha256(path.read_bytes()).hexdigest(),
               'exit_code': p.returncode, 'session_id': init.get('session_id'), 'init_model': init.get('model'),
               'assistant_models': models, 'tools': init.get('tools'), 'mcp_servers': init.get('mcp_servers'),
               'plugins': init.get('plugins'), 'skills': init.get('skills'), 'tool_blocks': uses, 'hook_events': hooks,
               'result_subtype': end.get('subtype'), 'is_error': end.get('is_error'), 'turns': end.get('num_turns'),
               'model_usage': end.get('modelUsage'), 'server_tool_use': end.get('usage', {}).get('server_tool_use')}
    save(receipts / (sample + '.json'), receipt)
    if p.returncode or end.get('is_error') or end.get('subtype') != 'success':
        raise RuntimeError(f'{sample} runtime failure ({p.returncode}): {str(end.get("result", ""))[:600]}')
    if (models != [MODEL] or init.get('model') != MODEL or init.get('tools') != [] or init.get('mcp_servers') != [] or init.get('plugins') or init.get('skills') or uses or hooks or any((receipt['server_tool_use'] or {}).values()) or end.get('num_turns') != 1):
        raise RuntimeError(sample + ' unexpected model, tool exposure or turn count: ' + repr(receipt))
    preserve_form(sample, end['result'])
    print(sample, 'collected;', models, flush=True)


def preserve_form(sample, raw_text):
    (HERE / 'raw' / (sample + '.txt')).write_text(raw_text, encoding='utf-8')
    # Strip at most one outer Markdown code fence. Preserve model JSON exactly, including evidence and labels.
    stripped = raw_text.strip()
    fence = re.fullmatch(r'```(?:json)?\s*\n(.*?)\n```', stripped, re.DOTALL | re.IGNORECASE)
    form_text = fence.group(1) if fence else raw_text
    (HERE / 'forms' / (sample + '.json')).write_text(form_text, encoding='utf-8')


def preserve_initial():
    sample = CASES[0]
    r = json.loads((HERE / 'receipts' / (sample + '.json')).read_text())
    assert r['exit_code'] == 0 and r['turns'] == 1 and r['result_subtype'] == 'success' and not r['is_error']
    assert r['assistant_models'] == [MODEL] and r['init_model'] == MODEL and r['tools'] == [] and r['mcp_servers'] == []
    assert not r['skills'] and not r['hook_events'] and not r['tool_blocks'] and not any(r['server_tool_use'].values())
    assert {v['name'] for v in r['plugins']} == set(BUILTINS) and all(v['path'] == 'builtin' for v in r['plugins'])
    trace = (HERE / 'raw' / (sample + '.jsonl')).read_bytes()
    assert sha256(trace).hexdigest() == r['raw_sha256']
    events = list(map(json.loads, trace.splitlines()))
    assert not (HERE / 'forms' / (sample + '.json')).exists()
    preserve_form(sample, next(e['result'] for e in events if e.get('type') == 'result'))


def score(reader):
    forms = HERE / 'forms'
    if not all((HERE / 'receipts' / (s + '.json')).is_file() for s in CASES):
        raise RuntimeError('Complete collection before scoring')
    results = {}
    for s in CASES:
        try:
            raw = reader.read_json(forms / (s + '.json'))
            results[s] = reader.validate(reader.EXAMPLES[s][0], raw)
        except FileNotFoundError:
            results[s] = reader.validate(reader.EXAMPLES[s][0], None)
        except (json.JSONDecodeError, UnicodeError):
            results[s] = {'form_status':'invalid_rating','items':{},'errors':['Invalid JSON or encoding']}
    firsts = [json.loads((HERE / 'receipts' / (s + '.json')).read_text()) for s in CASES]
    assert len({r['session_id'] for r in firsts}) == len(CASES)
    for r in firsts:
        s = r['case_id']
        payload = json.dumps(reader.packet(reader.EXAMPLES[s][0]), ensure_ascii=False, indent=2) + '\n'
        assert r['packet_sha256'] == sha256(payload.encode()).hexdigest()
        assert r['raw_sha256'] == sha256((HERE / 'raw' / (s + '.jsonl')).read_bytes()).hexdigest()
    save(HERE / 'validation.json', results)
    save(HERE / 'calibration.json', reader.calibrate(forms))
    discrepancies = []
    abstentions = []
    for s in CASES:
        for feature, expected in reader.EXAMPLES[s][1].items():
            row = results[s]['items'].get(feature, {})
            observed = row.get('status', 'missing')
            item = {'id': s, 'feature': feature, 'expected': expected, 'observed': observed, 'reason': row.get('reason')}
            if observed != expected:
                discrepancies.append(item)
            if expected in ('uncertain', 'not_assessable') or observed in ('uncertain', 'not_assessable'):
                abstentions.append(item)
    wrapped = [s for s in CASES if (HERE / 'raw' / (s + '.txt')).read_text() != (forms / (s + '.json')).read_text()]
    save(HERE / 'boundary-audit.json', {'discrepancies': discrepancies, 'authored_or_observed_abstentions': abstentions,
         'outer_markdown_fence_removed_for_json_decoding': wrapped,
         'session_count': len(firsts), 'unique_sessions': len({r['session_id'] for r in firsts}),
         'one_turn_each': all(r['turns'] == 1 for r in firsts),
         'zero_tools': all(r['tools'] == [] and r['mcp_servers'] == [] and not r['tool_blocks'] and not any(r['server_tool_use'].values()) for r in firsts),
         'b14_registered_cli_builtins': firsts[0]['plugins'], 'remaining_zero_plugins': all(r['plugins'] == [] for r in firsts[1:]),
         'runtime_note': 'B14 used CLI safe mode and disabled all hooks, but built-ins registered at initialization. Hook event reporting was explicitly enabled on the remaining 11 sessions. Each form is the first and only output for its case.'})


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('initial', 'preserve-initial', 'remaining', 'score'))
    args = parser.parse_args()
    reader = original_reader()
    if args.mode == 'score':
        score(reader)
    elif args.mode == 'preserve-initial':
        preserve_initial()
    else:
        cli, env, account, version = runtime()
        if args.mode == 'initial':
            if (HERE / 'collection.json').exists():
                raise RuntimeError('Initial run already recorded')
            save(HERE / 'collection.json', {'reader_sha256': sha256(SOURCE.read_bytes()).hexdigest(), 'cli_version': version,
                 'account': account, 'requested_model': MODEL, 'command_flags': FLAGS, 'source': str(SOURCE.relative_to(HERE.parents[2])),
                 'user_payload': 'Exact reader.challenge JSON serialization, no identifier or operator labels', 'case_ids': CASES})
            record(CASES[0], reader, cli, env)
        else:
            assert (HERE / 'forms' / (CASES[0] + '.json')).is_file()
            if (HERE / 'remaining-collection.json').exists():
                raise RuntimeError('Remaining runs already started')
            save(HERE / 'remaining-collection.json', {'case_ids': CASES[1:], 'command_flags': FLAGS, 'account': account, 'cli_version': version,
                 'initial_case_runtime': 'B14 used the original collection.json flags. Safe mode registered three CLI built-ins, named in its receipt; no tools were exposed. Its first and only response was retained without rescoring. Explicit built-in disables were added for the remaining cases.'})
            with ThreadPoolExecutor(max_workers=3) as pool:
                list(pool.map(lambda s: record(s, reader, cli, env), CASES[1:]))
