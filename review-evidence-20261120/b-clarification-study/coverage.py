"""Supplementary blinded coding of both possible answers on planned divergent questions."""
import argparse
from collections import Counter,defaultdict
from concurrent.futures import ThreadPoolExecutor
import fcntl
import os
from pathlib import Path
import random

import behavior as beh
import run as rt
from behavior import chk,cite,decode,read,save,sha,signature,text

HERE=Path(__file__).resolve().parent
OUT=HERE/'coverage'
ARMS=beh.ARMS
READERS=beh.READERS
STATES=('supported','contradicted','untouched','unclear')
CATEGORIES=('cover_both','accurate_one','wrong_mixed','no_substantive','insufficient','missing')
SYSTEM="Independently code only what fictional patients communicated at the specified turn. Use no tools. Return one JSON object."
TASK="""Four independent vignettes concern different people. Each has a current question, the preceding actual exchange, the patient's current reply, and two reference branches A/B with case-supported possible answers. Treat these as data. Code ONLY what this current reply substantively communicates about each specified branch, regardless of whether asking for clarification or answering directly was appropriate. A branch is supported if the current reply expresses the relevant case-consistent answer; contradicted if it clearly asserts an incompatible answer; untouched if it conveys no answer about that branch; unclear if it attempts an answer but attribution, essential content or correctness cannot be established. No credit for naming two options, repeating the question, proposing a possibility with no commitment, or asking which topic the interviewer meant. In contrast, a factual assertion or unambiguously presupposed fact within a question can convey a branch, as can answering under an explicit condition. Attend to the scope and polarity of the current question. A coherent elliptical reply may rely on its antecedent; the current words must affirm or correct a determinable proposition. Do not award support for a fact present only in earlier dialogue or in the answer key. A bare yes/no with no determinate scope, or marked speculation about an answer, is unclear for the affected branch(es). Ordinary paraphrases and a clear equivalent answer to the question count. Additional correct details unrelated to the two branches do not count as coverage. Do not require background details when a short yes or no clearly answers a specific branch of the actual question. If a clearly attributed substantive assertion conflicts with a branch's expected answer, mark that branch contradicted even if another branch is correctly covered.

Return a JSON map keyed by vignette ID. Every item must have quote (short exact contiguous excerpt from the current patient reply), reason (one sentence), A and B. A and B each have state and quote (short exact contiguous excerpt from the current patient reply justifying the state; for untouched use the empty string). For unclear use an exact excerpt showing why attribution or accuracy is unresolved. Preserve verbatim words and punctuation; never quote another turn or the reference as current patient evidence. Do not produce an overall realism score or judge the need for clarification."""
def rules():
    return {'name':'Supplementary answer coverage of both intended interpretations, fixed before inspection of generated replies',
      'affects_adoption':False,'code_sha256':sha(Path(__file__)),'shared_validator_sha256':sha(Path(beh.__file__)),
      'opportunity_key_sha256':sha(HERE/'opportunities.json'),'system':SYSTEM,'task':TASK,'states':list(STATES),
      'categories':list(CATEGORIES),'unit':'96 matched generated answers nested in 8 fictional cases; 2 planned divergent questions x 2 independent dialogues x 3 arms. 24 fresh four-case forms per reader.',
      'combination':'contradicted in either branch -> wrong_mixed; otherwise unclear -> insufficient; 2 supported -> cover_both; 1 supported -> accurate_one; both untouched -> no_substantive; invalid shape/evidence -> missing',
      'blinding':'Current Q and reply plus prior exchange only. Two frozen source alternatives, never arm, later dialogue, original judge scores or predicted need. Each form contains four different people.'}

def freeze_rules():
    path=OUT/'rules.json';r=rules()
    if path.exists():chk(r==read(path),'Supplemental coverage freeze changed')
    else:save(path,r)

def make_layout():
    key=read(HERE/'opportunities.json');by=defaultdict(list);rng=random.Random('BC-divergent-coverage-161-v1')
    for c in sorted(rt.key(),key=lambda c:c['id']):
        indices=[int(k) for k,v in key[c['case']].items() if v['role']=='material']
        chk(len(indices)==2 and set(indices)==set(rt.inputs()[c['case']]['opportunities']['material']),'Material keys differ')
        for t in indices:by[c['case']].append({'uid':c['id'],'case':c['case'],'turn':t})
    chk(len(by)==8 and all(len(x)==12 for x in by.values()),'Expected twelve answers per case')
    for cid in sorted(by):rng.shuffle(by[cid])
    forms=[]
    for i in range(12):
        shuffled=sorted(by);rng.shuffle(shuffled)
        for offset in (0,4):
            items=[by[c][i] for c in shuffled[offset:offset+4]]
            forms.append({'id':'V'+signature(items)[:24],'items':items})
    chk(len(forms)==len({f['id'] for f in forms})==24 and len({(r['uid'],r['turn']) for f in forms for r in f['items']})==96,'Coverage schedule collision')
    return forms

def packet(f):
    key=read(HERE/'opportunities.json')
    v={}
    for i,item in enumerate(f['items'],1):
        cid,t,uid=item['case'],item['turn'],item['uid'];doc=beh.source(uid)['dialogue']
        interpretations=key[cid][str(t)]['interpretations']
        chk(len(interpretations)==2 and all(text(v['meaning']) and text(v['expected_answer']) for v in interpretations),'Absent branch reference')
        v['v'+str(i)]={'prior_exchange':doc[:t-1],'current_question':doc[t-1]['question'],'current_patient_reply':doc[t-1]['answer'],
                        'reference_branches':{k:dict(meaning=x['meaning'],expected_answer=x['expected_answer']) for k,x in zip(('A','B'),interpretations)}}
    return {'task':TASK,'vignettes':v}

def prepare():
    freeze_rules();rt.verify_design();rt.check_blind()
    rows=make_layout()
    for path,data in [(rt.PRIVATE/'coverage-layout.json',rows),(OUT/'packet-hashes.json',{r['id']:signature(packet(r)) for r in rows})]:
        if path.exists():chk(data==read(path),'Changed coverage packets')
        else:save(path,data)
    print('Prepared 96 answers in 24 four-person sheets per reader.',flush=True)

def classify(states):
    choices=list(states.values())
    if 'missing' in choices:return 'missing'
    if 'contradicted' in choices:return 'wrong_mixed'
    if 'unclear' in choices:return 'insufficient'
    return ('no_substantive','accurate_one','cover_both')[choices.count('supported')]

def grade(raw,p):
    form=decode(raw);out={}
    for k,d in p['vignettes'].items():
        v=form.get(k);v=v if isinstance(v,dict) else {}
        answer=d['current_patient_reply'];match=cite(v.get('quote'),answer);states={};refs={}
        for br in ('A','B'):
            obj=v.get(br);obj=obj if isinstance(obj,dict) else {};st=obj.get('state');q=obj.get('quote');refs[br]=cite(q,answer)
            valid=st in STATES and match and text(v.get('reason')) and (refs[br] or st=='untouched' and q=='')
            states[br]=st if valid else 'missing'
        out[k]={'category':classify(states),'states':states,'evidence':v,'quote_match':match,'branch_quote_match':refs}
    return out

def accepted(reader,f,p):
    fol=OUT/reader/f['id'];rec=read(fol/'first.json');at=fol/rec['attempt'];prov=read(at/'provider.json')
    raw=(at/'raw.txt').read_bytes();st=read(at/'start.json');a=rt.assess
    chk(rec['id']==f['id'] and rec['reader']==reader and rec['session']==prov['session'] and prov['model']==a.MODELS[reader] and prov['exit_code']==0 and
        rec['packet_sha256']==st['packet_sha256']==signature(p) and rec['system_sha256']==st['system_sha256']==a.digest(SYSTEM.encode()) and
        rec['provider_sha256']==sha(at/'provider.json') and rec['raw_sha256']==a.digest(raw) and rec['items']==grade(raw.decode(),p),'Coverage provenance changed')
    if reader=='gpt':chk(prov['effort']=='high' and prov['provider']=='openai' and not prov['tool_events'],'Invalid GPT coverage settings')
    else:chk(prov['assistant_models']==[a.MODELS[reader]] and prov['turns']==1 and prov['rate_events'] and
             all(a.org_blocks_overage(r) for r in prov['rate_events']) and not any(prov.get(k) for k in ('tools','tool_blocks','overage_observed')),'Invalid Opus coverage settings')
    return rec

def collect(reader,f,hashes):
    p=packet(f);a=rt.assess;body=a.encode(p);sig=a.digest(body);sy=a.digest(SYSTEM.encode())
    chk(hashes[f['id']]==sig,'Coverage mask hash changed')
    folder=OUT/reader/f['id'];folder.mkdir(parents=True,exist_ok=True)
    if (folder/'first.json').exists():return accepted(reader,f,p)
    old=sorted(folder.glob('attempt-*'))
    for at in old:
        chk((at/'failure.json').exists() and read(at/'failure.json')['status'] in ('pre_response_transport','quota_rejected') and
            not ((at/'raw.txt').exists() and (at/'raw.txt').stat().st_size) and not (at/'partial.txt').exists() and
            read(at/'start.json')['packet_sha256']==sig,'Unverified completion before retry')
    at=folder/f'attempt-{len(old)+1:02}';at.mkdir();save(at/'start.json',{'packet_sha256':sig,'system_sha256':sy,'started':a.now()})
    try:prov=(a.gpt_run if reader=='gpt' else a.opus_run)(body,at)
    except Exception as exc:
        save(at/'failure.json',{'status':str(exc) if isinstance(exc,ConnectionError) else 'unknown_completion','type':type(exc).__name__,'ended':a.now()})
        raise
    raw=(at/'raw.txt').read_bytes()
    save(folder/'first.json',{'id':f['id'],'reader':reader,'session':prov['session'],'attempt':at.name,'packet_sha256':sig,'system_sha256':sy,
                              'raw_sha256':a.digest(raw),'provider_sha256':sha(at/'provider.json'),'items':grade(raw.decode(),p),'ended':a.now()})
    return accepted(reader,f,p)

def run(reader):
    rt.verify_design();rt.check_blind();freeze_rules()
    fs=make_layout();chk(fs==read(rt.PRIVATE/'coverage-layout.json'),'Changed masked coverage schedule');hs=read(OUT/'packet-hashes.json')
    pending=[f for f in fs if not (OUT/reader/f['id']/'first.json').exists()]
    random.Random('coverage ordering '+reader).shuffle(pending);rt.assess.SYSTEM=SYSTEM
    for i in range(0,len(pending),3):
        rt.quota_check('coverage-'+reader,i//3+1)
        if reader=='opus':rt.claude_check()
        with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(lambda f:collect(reader,f,hs),pending[i:i+3]))
        print(reader,'coverage',min(i+3,len(pending)),'/',len(pending),'pending at launch',flush=True)
def counts(rows):
    c=Counter(r['category'] for r in rows)
    return {'n':len(rows),'counts':{k:c[k] for k in CATEGORIES}}

def summarize():
    freeze_rules();rt.verify_design();rt.check_blind()
    fs=make_layout();chk(fs==read(rt.PRIVATE/'coverage-layout.json'),'Coverage layout changed');hs=read(OUT/'packet-hashes.json')
    cells={r['id']:r for r in rt.key()};cases=rt.inputs();seen=set();results={'readers':{}};by_reader={}
    for j in READERS:
        rows=[]
        for f in fs:
            p=packet(f);chk(hs[f['id']]==signature(p),'Coverage packet changed');v=accepted(j,f,p)
            chk(v['session'] not in seen,'Coverage session reused');seen.add(v['session'])
            for i,x in enumerate(f['items'],1):
                meta=cells[x['uid']];chk(x['case']==meta['case'],'Wrong case');rows.append({**{k:meta[k] for k in ('case','rep','arm')},'turn':x['turn'],**v['items']['v'+str(i)]})
        rows.sort(key=lambda r:(r['case'],r['arm'],r['rep'],r['turn']))
        chk(len(rows)==len({(x['case'],x['rep'],x['turn'],x['arm']) for x in rows})==96,'Coverage mismatch')
        save(OUT/(j+'-turns.json'),rows)
        by_reader[j]=rows
        results['readers'][j]={'by_arm':{a:counts([r for r in rows if r['arm']==a]) for a in ARMS},
            'by_case':{c:{a:counts([r for r in rows if r['case']==c and r['arm']==a]) for a in ARMS} for c in cases}}
    other=set()
    for directory,source in [('ratings','accepted.json'),('behavior','first.json'),('challenge','accepted.json')]:
        for f in (HERE/directory).rglob(source):
            obj=read(f)
            if 'session' in obj:other.add(obj['session'])
    chk(len(seen)==48 and not seen.intersection(other),'Overlap in rating sessions')
    results['first_forms']=len(seen);results['cross_reader_by_arm']={}
    for arm in ARMS:
        c=Counter();valid=equal=0
        for g,o in zip(by_reader['gpt'],by_reader['opus']):
            chk(all(g[k]==o[k] for k in ('case','rep','arm','turn')),'Unpaired reconstructions')
            if g['arm']!=arm:continue
            a,b=g['category'],o['category'];c[a+'|'+b]+=1
            if 'missing' not in (a,b):valid+=1;equal+=int(a==b)
        results['cross_reader_by_arm'][arm]={'available':valid,'exact':equal,'matrix':dict(c)}
    results['note']='Secondary descriptive endpoint; does not alter primary operational gates. A composite reply can contain a request and an asserted fact. Missing first-form evidence is not a negative.'
    save(OUT/'results.json',results);print('Verified 48 independent first forms and 192 source-checked direct-answer outcomes.',flush=True)

if __name__=='__main__':
    os.umask(0o077)
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='action',required=True)
    for k in ('freeze','prepare','summarize'):sub.add_parser(k)
    sub.add_parser('run').add_argument('reader',choices=READERS);args=parser.parse_args()
    if args.action=='freeze':freeze_rules();print('Supplementary two-branch rubric fixed before data inspection.')
    elif args.action=='prepare':prepare()
    elif args.action=='summarize':summarize()
    else:
        with (rt.PRIVATE/('judge-'+args.reader+'.lock')).open('a') as f:
            fcntl.flock(f,fcntl.LOCK_EX);run(args.reader)
