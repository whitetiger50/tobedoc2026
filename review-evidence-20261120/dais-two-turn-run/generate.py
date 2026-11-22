"""Run the fixed two-turn design with the previously used native generators."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import fcntl
from functools import lru_cache
import hashlib
import importlib.util
import itertools
import json
import os
from pathlib import Path
import random
import secrets
import shutil
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
PRIVATE = HERE / 'private'
PLAN_FILE = BASE / 'dais-two-turn-design.json'
SYSTEMS = BASE / 'b-clarification-study'
SOURCE = BASE / 'english-12turn-run/generation.py'
sys.dont_write_bytecode = True
sys.path.insert(0, str(BASE / 'next-english-study'))
import resume_generation
from runner import gen, quota

load, save, check = gen.load, gen.save, gen.require
plan = load(PLAN_FILE)
arms = plan['design']['arms']
sequences = plan['interviewer_sequences']


def profiles(sequence):
    p = plan['synthetic_profiles']
    return [dict(id=c['id'], questions=sequences[sequence],
                 profile={**p['shared'], 'background':c['background'],
                          'facts':[{**p['fact_fields_shared_by_all_facts'], 'content':s} for s in c['facts']]})
            for c in p['cards']]


@lru_cache(maxsize=None)
def engine(sequence, arm):
    native = 'B' if arm == 'BC' else arm
    spec = importlib.util.spec_from_file_location('two_turn_engine_'+sequence+arm, SOURCE)
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    systems, core = g.sources()
    systems[native] = (SYSTEMS / (arm+'.txt')).read_text()
    g.sources = lambda: (systems, core)
    g.ARMS = (native,)
    g.CASE_IDS = {p['id'] for p in profiles(sequence)}
    g.CASES = PRIVATE / sequence / 'inputs.json'
    g.FREEZE = PRIVATE / sequence / (arm+'-freeze.json')
    g.turn_dir = lambda cid, a, t: PRIVATE / 'generation' / sequence / cid / arm / f'{t:02}'
    g.fallback_notices = resume_generation.validate
    return g, native


def prepare():
    for a,expected in plan['design']['prompt_sha256'].items():
        check(gen.digest((SYSTEMS/(a+'.txt')).read_bytes())==expected,'Changed system prompt: '+a)
    cards = [c['id'] for c in profiles(next(iter(sequences)))]
    combos = set(itertools.product(cards,sequences,arms))
    key = PRIVATE/'key.json'
    if not key.exists():
        rows = [dict(id='I'+secrets.token_hex(12), card=c,sequence=q,arm=a) for c,q,a in sorted(combos)]
        random.SystemRandom().shuffle(rows)
        save(key,rows)
    rows = load(key)
    check(len(rows)==len({r['id'] for r in rows})==len(combos)==12 and
          {(r['card'],r['sequence'],r['arm']) for r in rows}==combos,'Incomplete design')
    save(PRIVATE/'spec.json',{'design_sha256':gen.digest(PLAN_FILE.read_bytes()),
                              'generation_source_sha256':gen.digest(SOURCE.read_bytes()),
                              'key_sha256':gen.digest(key.read_bytes())})
    for q in sequences:
        cases = profiles(q)
        for a in arms:
            g,n = engine(q,a)
            save(g.CASES,cases)
            signatures = {c['id']+'-'+n:gen.digest(gen.encode(g.messages(c,n,1,[]))) for c in cases}
            save(g.FREEZE,{'generator_sha256':gen.digest(SOURCE.read_bytes()),
                           'cases_sha256':gen.digest(g.CASES.read_bytes()),'first_message_sha256':signatures})
    return rows


def meter():
    q=quota.read_quota()
    w=q['primary']
    check(q['limitId']=='codex' and w['windowDurationMins']==10080 and w['usedPercent']<66,
          'Study quota guard: verify weekly remaining before proceeding')
    return w['usedPercent']


def one(r,t):
    g,n=engine(r['sequence'],r['arm'])
    return g.one(r['card'],n,t)


def verify_and_blind(rows):
    sessions=set()
    for r in rows:
        g,n=engine(r['sequence'],r['arm'])
        c=next(x for x in profiles(r['sequence']) if x['id']==r['card'])
        pairs=[]
        current=[]
        for t in (1,2):
            req = g.messages(c,n,t,pairs)
            folder = g.turn_dir(c['id'],n,t)
            o=g.verify_result(folder, gen.digest(gen.encode(req)))
            check(o['trace_sha256']==gen.digest((folder/'events.jsonl').read_bytes()) and
                  o['question']==c['questions'][t-1] and o['visible_tool_events']==o['exit_code']==0,
                  'Output mismatch')
            pairs.append((o['question'],o['raw']))
            current.append(o['session'])
        check((current[0]==current[1])==(n=='B') and not sessions.intersection(current),'Unexpected session reuse')
        sessions.update(current)
        save(HERE/'blind'/(r['id']+'.json'),dict(profile=c['profile'],dialogue=[dict(question=q,answer=a) for q,a in pairs]))
        if n=='B':
            ptr=g.turn_dir(c['id'],n,1).parent/'isolated-runtime.json'
            runtime=Path(load(ptr)['path'])
            check(runtime.parent==Path('/private/tmp') and runtime.name.startswith('interview-cli-'),'Unexpected runtime location')
            if runtime.is_dir():
                shutil.rmtree(runtime)
    save(PRIVATE/'generation-complete.json',{'interviews':len(rows),'answers':2*len(rows),
         'blind_sha256':{r['id']:gen.digest((HERE/'blind'/(r['id']+'.json')).read_bytes()) for r in rows}})


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('op',choices=['prepare','generate'])
    op=ap.parse_args().op
    os.umask(0o077)
    PRIVATE.mkdir(parents=True,exist_ok=True)
    with (PRIVATE/'generate.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        rows=prepare()
        if op=='generate':
            for t in (1,2):
                pending=[]
                for r in rows:
                    g,n=engine(r['sequence'],r['arm'])
                    if not (g.turn_dir(r['card'],n,t)/'result.json').exists():
                        pending.append(r)
                if pending:
                    print('Weekly Codex used:',meter(),'percent. Generating turn',t,flush=True)
                    with ThreadPoolExecutor(max_workers=6) as pool:
                        list(pool.map(lambda r:one(r,t),pending))
            verify_and_blind(rows)
            print('Verified 12 interviews and 24 answers.',flush=True)


if __name__=='__main__':
    main()
