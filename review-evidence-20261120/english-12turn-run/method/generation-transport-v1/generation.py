"""One auditable generation turn. The caller controls concurrency, quota and release."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import fcntl
from functools import lru_cache
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / 'persona-audit-20261120T072413385108Z/speech_module'
B_FILE = ROOT / 'tobedoc2026/config/main-freeze-v01/system-template.txt'
T_FILE = SOURCE / 'patient_v02.txt'
T1_FILE = HERE.parent / 'first-turn-revision-proposal/proposed-prompt.txt'
CORE_FILE = SOURCE / 'core.py'
DISABLED = ('apps', 'plugins', 'memories', 'shell_tool', 'unified_exec', 'multi_agent',
            'multi_agent_v2', 'browser_use', 'browser_use_external', 'computer_use', 'view_image',
            'image_generation', 'hooks', 'goals', 'skill_search', 'tool_suggest',
            'workspace_dependencies', 'shell_snapshot', 'in_app_browser')
SOURCE_HASHES = {
    B_FILE: 'd6817b61c31655b58f021a0cb2168d60473641659e289fe8300fd73e40ad52f6',
    T_FILE: '721203cb5a1ece9c3f93dfb1fb3ed172fc734439a6ed89a7e47f86ab2bf9e269',
    T1_FILE: '755dcc39be74dbe41ce61b2e3e145c7af97a4558cbbad85f3a9ab3c0d4829fb8',
    CORE_FILE: '746780923ce885c7c21e4eed71a5c5df1aa9d5696fb8b792fa849f4aa836bc0b',
}
T0_HASH = 'a68a9ec0f9228395f6739791ef268ac7e4ffa57797076e50868fea688bca5261'
MODEL = 'gpt-6.1-sol'
PROVENANCE = 'independently_authored_fictional_english_case'
GEN = HERE / 'private/generation'
CASES = HERE / 'cases.json'
FREEZE = HERE / 'generation-freeze.json'
ARMS = ('B', 'T0', 'T1')
CASE_IDS = {f'D{i:02d}' for i in range(1,5)} | {f'H{i:02d}' for i in range(1,9)}


def require(ok, why):
    if not ok:
        raise ValueError(why)


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(raw):
    return sha256(raw).hexdigest()


def encode(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def load(path):
    return json.loads(path.read_bytes())


def save(path, value):
    """No silent replacement, even if a caller restarts after a crash."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as f:
        tmp = Path(f.name)
        try:
            json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
    try:
        try:
            os.link(tmp, path)
        except FileExistsError:
            require(load(path) == value, f'Immutable file differs: {path.name}')
    finally:
        tmp.unlink(missing_ok=True)


@lru_cache
def sources():
    for path, expected in SOURCE_HASHES.items():
        require(digest(path.read_bytes()) == expected, 'Frozen source changed: '+path.name)
    before = '외부에는 환자가 실제로 말하는 한국어 텍스트만 출력한다.'
    after = before.replace('한국어', '영어')
    old = T_FILE.read_text()
    require(old.count(before) == 1, 'Language adaptation clause missing')
    t0 = old.replace(before, after)
    require(digest(t0.encode()) == T0_HASH, 'English T0 source changed')
    spec = importlib.util.spec_from_file_location('study_native_patient_module', CORE_FILE)
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    return { 'B': B_FILE.read_text(), 'T0': t0, 'T1': T1_FILE.read_text() }, core


def partition(case):
    return 'development' if case['id'].startswith('D') else 'heldout_confirmation'


def profile_inputs(case):
    p = case['profile']
    # Keep every authored content string and disclosure/knowledge/clinical-kind tag in both views.
    facts = [dict(id='background', kind='background', content=p['background'], patient_knows=True, disclosure='on_topic'),
             dict(id='history', kind='background', content=p['history'], patient_knows=True, disclosure='on_topic')]
    for i, f in enumerate(p['facts'], 1):
        require(set(f) == {'kind','content','patient_knows','disclosure','disclosure_context'}, 'Incomplete authored fact')
        content = f['content'] + ' Disclosure context: ' + f['disclosure_context']
        facts.append(dict(id=f'F{i:02d}', kind=f['kind'], content=content,
                          patient_knows=f['patient_knows'], disclosure=f['disclosure']))
    prod = p['verbal_productivity']
    require(prod in {'Normal','Increased','Decreased'}, 'Unknown verbal productivity')
    communication = {k:p[k] for k in ('organization','spontaneity','guardedness','expression')}
    communication['expression'] += ' Verbal productivity: ' + prod + '.'
    patient = dict(case_id=case['id'], partition=partition(case), provenance=PROVENANCE,
                   facts=facts, self_understanding=p['self_understanding'])
    mfc = {'MFC-Profile': {'Identifying data': p['background'], 'Clinical and personal facts': p['facts']},
           'MFC-History': p['history'],
           'MFC-Behavior': {'Thought process': p['organization'], 'Spontaneity': p['spontaneity'],
                            'General appearance/attitude/behavior': p['guardedness'], 'Tone of voice': p['expression'],
                            'Verbal productivity': prod, 'Insight': p['self_understanding']}}
    require(set(p) == {'background','history','facts','organization','spontaneity','guardedness','expression',
                       'verbal_productivity','self_understanding'}, 'Unexpected profile field')
    return mfc, patient, communication


def messages(case, arm, turn, pairs):
    systems, core = sources()
    require(arm in (('T0',) if partition(case) == 'development' else ARMS)
            and 1 <= turn <= 12 and len(pairs) == turn-1, 'Illegal arm/turn/history')
    question = case['questions'][turn-1]
    mfc, patient, comm = profile_inputs(case)
    for i, (q, a) in enumerate(pairs):
        require(q == case['questions'][i] and isinstance(a, str) and a.strip(), 'Invalid preceding turn')
    if arm == 'B':
        system = systems[arm]
        require(system.count('{{data.mfc}}') == 1, 'Original B marker invalid')
        system = system.replace('{{data.mfc}}', json.dumps(mfc, ensure_ascii=False, indent=2))
        history = [dict(role=r, content=v) for q,a in pairs for r,v in [('user',q),('assistant',a)]]
        return [dict(role='system',content=system), *history, dict(role='user',content=question)]
    history = [dict(speaker=s,text=v) for q,a in pairs for s,v in [('clinician',q),('patient',a)]]
    body = dict(patient=patient, communication=comm, history=history, current_question=question)
    original = core.build_packet(body, expected_partition=partition(case), module_version=core.V02_VERSION)
    require(original['template_sha256']==SOURCE_HASHES[T_FILE], 'Packet template identity mismatch')
    return [dict(role='system', content=systems[arm]), original['messages'][1]]


def assemble():
    cases = load(CASES)
    require(len(cases)==12 and {c['id'] for c in cases} == CASE_IDS, 'Unexpected cases')
    for initial, expected in [('D', 1), ('H', 2)]:
        strata = Counter(c['stratum'] for c in cases if c['id'][0] == initial)
        require(len(strata)==4 and set(strata.values())=={expected}, 'Unbalanced strata')
    rows = {}
    for case in cases:
        qs = case['questions']
        require(len(qs)==len(set(qs))==12 and all(isinstance(q,str) and q.strip() for q in qs), 'Invalid schedule')
        arms = ('T0',) if partition(case)=='development' else ARMS
        pairs = [(q, 'Offline history integrity marker '+str(i)) for i,q in enumerate(qs[:-1])]
        for arm in arms:
            first = messages(case, arm, 1, [])
            final = messages(case, arm, 12, pairs)
            if arm == 'B':
                require(len(final)==24 and final[1:-1:2] == [dict(role='user',content=q) for q,a in pairs]
                        and final[2:-1:2] == [dict(role='assistant',content=a) for q,a in pairs], 'B history lost')
            else:
                payload = json.loads(final[-1]['content'])
                require([(x['text'],y['text']) for x,y in zip(payload['history'][::2],payload['history'][1::2])]==pairs,
                        'Team history lost')
            require('Offline history integrity marker' not in first[0]['content'], 'QA leakage')
            rows[case['id']+'-'+arm] = digest(encode(first))
        if 'B' in arms:
            require(messages(case,'T0',12,pairs)[1] == messages(case,'T1',12,pairs)[1], 'T inputs differ')
    return dict(model=MODEL, effort='medium', frozen_sources={str(p.relative_to(ROOT)):h for p,h in SOURCE_HASHES.items()},
                T0_english_sha256=T0_HASH, generator_sha256=digest(Path(__file__).read_bytes()),
                cases_sha256=digest(CASES.read_bytes()), first_message_sha256=rows,
                turns_per_interview=12, total_interviews=len(rows), generation_turns=len(rows)*12,
                B_history='native persistent Codex conversation, current interviewer question only; verify saved transcript before continuing',
                team_history='fresh ephemeral conversation, original v0.2 build_packet user JSON with authentic prior turns',
                shared_fact_mapping='MFC preserves authored facts, on-topic/sensitive, known status and kind. Same clinical facts plus two tagged background/history entries in T. Authored productivity category available to both. Compact MFC does not populate unspecified schema fields.',
                sampling='CLI defaults; no seed or temperature override; first response preserved')


def prepare():
    save(FREEZE, assemble())


def turn_dir(cid, arm, turn):
    return GEN / cid / arm / f'{turn:02d}'


def verify_result(folder, packet_hash=None):
    row = load(folder/'result.json')
    require(row['model'] == MODEL and row['effort']=='medium' and row['session']
            and isinstance(row['raw'],str) and row['raw'].strip()
            and row['raw_sha256'] == digest(row['raw'].encode())
            and row['request_sha256'] == digest(encode(load(folder/'request.json')))
            and (packet_hash is None or row['request_sha256']==packet_hash), 'Invalid result receipt')
    return row


def scratch(folder, arm, turn):
    pointer = folder.parent / 'isolated-runtime.json' if arm == 'B' else folder/'isolated-runtime.json'
    if pointer.exists():
        path = Path(load(pointer)['path'])
        require(path.exists() and path.is_dir(), 'Isolated session directory lost')
    else:
        require(arm!='B' or turn==1, 'Missing B native history')
        path = Path(tempfile.mkdtemp(dir='/private/tmp', prefix='interview-cli-'))
        work, cfg = path/'work', path/'config'
        work.mkdir(); cfg.mkdir(mode=0o700)
        # No bearer token or account credentials copied into the research project.
        (cfg/'auth.json').symlink_to(Path.home()/'.codex/auth.json')
        shutil.copyfile(Path.home()/'.codex/models_cache.json', cfg/'models_cache.json')
        save(pointer, {'path':str(path)})
    return path


def native_history(cfg, session, pairs):
    paths = list((cfg/'sessions').rglob('*'+session+'*.jsonl'))
    require(len(paths)==1, 'Cannot uniquely locate B native session')
    events, contexts = [], []
    for line in paths[0].read_text().splitlines():
        x = json.loads(line)
        if x.get('type')=='turn_context':
            contexts.append(x['payload'])
        if x.get('type')=='event_msg':
            event = x['payload']
            if event.get('type') in ('user_message','agent_message'):
                events.append((event['type'],event['message']))
    expected = [(r,v) for q,a in pairs for r,v in [('user_message',q),('agent_message',a)]]
    require(events==expected, 'Persistent B native transcript differs from recorded prior turns')
    require(contexts and all(c.get('model') == MODEL and c.get('effort') == 'medium'
                             for c in contexts), 'Observed CLI session model or effort changed')
    return digest(encode(events))


def record_result(folder, req, turn, cid, arm, code, native_session, expected_pairs, cfg):
    if (folder/'result.json').is_file():
        return verify_result(folder,digest(encode(req)))
    require(code==0, f'CLI exit {code}; inspect retained first trace')
    events = [json.loads(l) for l in (folder/'events.jsonl').read_text().splitlines() if l.strip()]
    start = [e.get('thread_id') for e in events if e.get('type')=='thread.started']
    require(len(start)==1 and (not native_session or start[0]==native_session), 'Unexpected CLI session')
    end = [e for e in events if e.get('type')=='turn.completed']
    require(len(end)==1 and not any(e.get('type')=='turn.failed' for e in events), 'No unique completed turn')
    items = [e['item'] for e in events if e.get('type')=='item.completed']
    require(all(i.get('type') in ('agent_message','reasoning') for i in items), 'Unexpected tool or other item')
    answers = [i['text'] for i in items if i['type']=='agent_message']
    require(len(answers)==1 and answers[0].strip(), 'Expected one nonempty patient output')
    raw = answers[0]
    last = (folder/'last.txt').read_text()
    require(last in (raw, raw+'\n'), 'Final output disagrees with CLI event')
    history_hash = native_history(cfg,start[0],(expected_pairs if arm=='B' else [])+[(req[-1]['content'],raw)])
    stamp = load(folder/'started.json')
    row = dict(case=cid, arm=arm, turn=turn, question=stamp['question'], model=MODEL, effort='medium',
               model_evidence='model and effort in native CLI rollout turn_context record',
               session=start[0], raw=raw, raw_sha256=digest(raw.encode()), request_sha256=digest(encode(req)),
               started_utc=stamp['utc'], completed_utc=now(), usage=end[0].get('usage'), exit_code=code,
               visible_tool_events=0, native_transcript_sha256=history_hash,
               trace_sha256=digest((folder/'events.jsonl').read_bytes()))
    save(folder/'result.json',row)
    return row


def one(cid, arm, turn):
    frozen = load(FREEZE)
    require(frozen['generator_sha256']==digest(Path(__file__).read_bytes())
            and frozen['cases_sha256']==digest(CASES.read_bytes()), 'Generation freeze invalid')
    case = next(c for c in load(CASES) if c['id']==cid)
    require(cid in CASE_IDS and arm in (('T0',) if cid[0]=='D' else ARMS) and 1<=turn<=12,'Invalid job')
    folder = turn_dir(cid,arm,turn)
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (folder.parent/'interview.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        rows = [verify_result(turn_dir(cid,arm,i)) for i in range(1,turn)]
        pairs = [(r['question'],r['raw']) for r in rows]
        req = messages(case,arm,turn,pairs)
        signature = digest(encode(req))
        if turn==1:
            require(signature==frozen['first_message_sha256'][cid+'-'+arm],'First turn changed')
        save(folder/'request.json',req)
        if (folder/'result.json').exists():
            return verify_result(folder,signature)
        native_session = rows[-1]['session'] if arm=='B' and rows else None
        runtime = scratch(folder,arm,turn)
        cfg, work = runtime/'config', runtime/'work'
        if (folder/'started.json').exists():
            # Recover a completed first turn, but never dispatch twice after an ambiguous outcome.
            if (folder/'exit.json').exists():
                return record_result(folder,req,turn,cid,arm,load(folder/'exit.json')['code'],native_session,pairs,cfg)
            if (folder/'events.jsonl').is_file() and (folder/'last.txt').is_file():
                if any('"turn.completed"' in l for l in (folder/'events.jsonl').read_text().splitlines()):
                    return record_result(folder,req,turn,cid,arm,0,native_session,pairs,cfg)
            raise RuntimeError('Prior dispatch unresolved; retained trace requires review')
        if native_session:
            native_history(cfg,native_session,pairs)
        system = runtime/'instructions.txt'
        if system.exists():
            require(system.read_text()==req[0]['content'],'Resumed system prompt mismatch')
        else:
            system.write_text(req[0]['content'])
        env = {k:os.environ[k] for k in ('PATH','HOME','USER','LOGNAME','TMPDIR','LANG') if k in os.environ}
        env['CODEX_HOME']=str(cfg)
        args=['codex','--no-daemon','-a','never','exec','--sandbox','read-only','--cd',str(work),'--color','never',
              '--skip-git-repo-check','--ignore-user-config','--ignore-rules','--enable','skip_host_skill_discovery',
              '--enable','omit_skill_descriptions','-c','web_search="disabled"','-c','mcp_servers={}',
              '-c','project_doc_max_bytes=0','-c','forced_login_method="chatgpt"','-c','model_reasoning_effort="medium"',
              '-c','model_instructions_file='+json.dumps(str(system))]
        for feature in DISABLED:
            args.extend(['--disable',feature])
        if native_session:
            args.extend(['resume','--skip-git-repo-check'])
        args.extend(['--model',MODEL,'--json','--output-last-message',str(folder/'last.txt')])
        if native_session:
            args.append(native_session)
        args.append('-')
        save(folder/'started.json',dict(utc=now(),question=case['questions'][turn-1],request_sha256=signature,
                                       cli=shutil.which('codex'),args=args,history_count=turn-1))
        with (folder/'events.jsonl').open('xb') as out,(folder/'stderr.log').open('xb') as err:
            run=subprocess.run(args,input=req[-1]['content'].encode(),cwd=work,env=env,stdout=out,stderr=err,timeout=190)
        save(folder/'exit.json',dict(code=run.returncode))
        row = record_result(folder,req,turn,cid,arm,run.returncode,native_session,pairs,cfg)
        if arm!='B' or turn==12:
            shutil.rmtree(runtime)
        return row


if __name__ == '__main__':
    os.umask(0o077)
    sys.dont_write_bytecode = True
    cli=argparse.ArgumentParser(description=__doc__)
    subs=cli.add_subparsers(dest='op',required=True)
    subs.add_parser('prepare')
    job=subs.add_parser('one')
    job.add_argument('case')
    job.add_argument('arm',choices=ARMS)
    job.add_argument('turn',type=int,choices=range(1,13))
    args=cli.parse_args()
    if args.op=='prepare':
        prepare()
        print('Frozen 28 interviews, 336 generation turns')
    else:
        row=one(args.case,args.arm,args.turn)
        print(json.dumps({k:row[k] for k in ('case','arm','turn','session','raw_sha256')}))
