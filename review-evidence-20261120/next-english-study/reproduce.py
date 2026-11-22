"""Recalculate the primary paired outcomes and turn-level semantic totals offline."""
import hashlib
import math
from statistics import mean, median
import json
from collections import Counter
from pathlib import Path
import re
import unicodedata

ARMS = ('B', 'T1', 'T2')
READERS = ('gpt', 'opus')
CASES = tuple('N%02d' % i for i in range(1, 9))
CONTRASTS = (('T2', 'T1'), ('T2', 'B'), ('T1', 'B'))
LABELS = ('positive', 'uncertain', 'missing', 'negative')
PUNCT = str.maketrans({'“':'"', '”':'"', '„':'"', '’':"'", '‘':"'", '–':'-', '—':'-', '‐':'-', '…':'...'})

def require(condition, message):
    if not condition:
        raise ValueError(message)

def load(path):
    return json.loads(path.read_bytes())

def digest(data):
    return hashlib.sha256(data).hexdigest()

def check_manifest(root):
    manifest = load(root / 'SHA256.json')
    paths = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    require(set(manifest) == paths - {'SHA256.json'}, 'Manifest inventory mismatch')
    for name, expected in manifest.items():
        require(expected == digest((root / name).read_bytes()), 'Hash mismatch: '+name)

def compare(left, right):
    if None in left + right:
        return 'missing'
    signs = ['win' if a > b else 'loss' if a < b else 'tie' for a,b in zip(left, right)]
    return signs[0] if signs[0] == signs[1] else 'unstable'

def scopes(op):
    return {'avoidable_recap':range(2,13), 'evasive':op['clear'],
            'consequential_invention':range(1,13), 'unsupported_stereotype':range(1,13),
            'first_recital':[1], 'clarify_yield':op['ambiguous'], 'concrete_example':op['example']}

def normalize(s):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC',s).translate(PUNCT)).strip()

def verify_quote(quote, answer):
    require(isinstance(quote,str) and re.search('[a-zA-Z0-9]',quote), 'Empty quote')
    if quote in answer:
        return
    q = normalize(quote)
    if len(q) > 2 and q[0] == q[-1] and q[0] in ('"', "'"):
        q = q[1:-1].strip()
    require(q and q in normalize(answer), 'Evidence outside cited synthetic answer')

RECON_DOMAINS = ('experience_or_function', 'appraisal_or_response')

def reconstruction_targets(rows, cases):
    paths = {}
    require(len(rows) == len(CASES), 'Reconstruction case count')
    for row in rows:
        c = row['case']
        require(c in CASES and c not in paths, 'Duplicate or unexpected reconstruction case')
        targets = {t['domain']:t for t in row['targets']}
        require(len(row['targets'])==2 and set(targets)==set(RECON_DOMAINS), 'Reconstruction target domains')
        for domain, t in targets.items():
            fields = ('stem','gold','foil','source_field','source_quote')
            require(all(isinstance(t[f],str) and t[f].strip() for f in fields), 'Target definition')
            require(t['gold']!=t['foil'], 'Indistinguishable reconstruction options')
            profile = cases[c]['profile']
            match = re.fullmatch(r'profile\.facts\[(\d+)\]\.content', t['source_field'])
            source = profile['facts'][int(match[1])]['content'] if match else profile[t['source_field'][len('profile.'):]]
            require(t['source_quote'] in source, 'Reconstruction source citation')
            ix = t['opportunities']
            require(ix and len(ix)==len(set(ix)) and all(type(t) is int and 1<=t<=12 for t in ix), 'Target opportunity indices')
        paths[c] = targets
    return paths

RECON_ARMS = (*ARMS, 'Q')
RECON_LABELS = ('correct','foil','insufficient','conflict','invalid','missing_form')

def reconstruction_counts(values):
    freq = Counter(values)
    return {**{k:freq[k] for k in RECON_LABELS}, 'n':len(values)}

def reconstruction_summary(rows, selected):
    by_arm = {a:reconstruction_counts([rows[c][a][d] for c,d in selected]) for a in RECON_ARMS}
    by_domain = {d:{a:reconstruction_counts([rows[c][a][d] for c,dom in selected if dom==d])
                    for a in RECON_ARMS} for d in RECON_DOMAINS}
    contrasts = {}
    for left,right in CONTRASTS:
        by_case = {}
        dirs = Counter()
        for c in CASES:
            domains = [d for cid,d in selected if cid==c]
            if not domains:
                continue
            a = Counter(rows[c][left][d] for d in domains)
            b = Counter(rows[c][right][d] for d in domains)
            delta = a['correct']-b['correct']
            lo = delta-b['invalid']-b['missing_form']
            hi = delta+a['invalid']+a['missing_form']
            by_case[c] = {'eligible':len(domains),'difference':delta,'possible':[lo,hi]}
            dirs['more' if lo>0 else 'fewer' if hi<0 else 'equal' if lo==hi==0 else 'indeterminate']+=1
        contrasts[left+'_vs_'+right]={'by_case':by_case, 'counts':dict(dirs)}
    return {'eligible_targets':len(selected),'by_arm':by_arm,'by_domain':by_domain,'contrasts':contrasts}

def verify_reconstruction(root, cases, dialogue):
    dest = root/'reconstruction'
    targets = reconstruction_targets(load(dest/'targets.json'),cases)
    first = load(dest/'first_decisions.json')
    report = load(dest/'results.json')
    all_targets = [(c,d) for c in CASES for d in sorted(RECON_DOMAINS)]
    require(len(first)==128 and report['planned_forms']==64 and report['planned_targets_per_arm_per_reader']==16,'Reconstruction coverage')
    rows = {r:{c:{a:{} for a in RECON_ARMS} for c in CASES} for r in READERS}
    order = {}
    missing_forms = set()
    present_forms = set()
    for rec in first:
        c,a,r,d = (rec[key] for key in ('case','arm','reader','domain'))
        require(d in targets[c] and d not in rows[r][c][a], 'Duplicate reconstruction item')
        require(rec['condition']==('questions_only' if a=='Q' else 'full'),'Reconstruction mode')
        gold,choice,status = (rec[k] for k in ('gold_option','choice','outcome'))
        require(gold in ('A','B') and status in RECON_LABELS,'Reconstruction item coding')
        require(order.setdefault((r,c,d),gold)==gold,'Gold position differs across conditions')
        require(choice in ('A','B','insufficient','both_or_conflicting',None),'Unknown public choice')
        if status=='missing_form':
            missing_forms.add((r,c,a))
        else:
            present_forms.add((r,c,a))
        if status not in ('invalid','missing_form'):
            expected={'A':'correct' if gold=='A' else 'foil','B':'correct' if gold=='B' else 'foil',
                      'insufficient':'insufficient','both_or_conflicting':'conflict'}
            require(choice in expected and expected[choice]==status,'Incorrect decoded choice')
            require(isinstance(rec['reason'],str) and rec['reason'].strip(),'Missing decision rationale')
            supports = {'A','B'} if status=='conflict' else set() if status=='insufficient' else {choice}
            attributed = {e['supports'] for e in rec['evidence'] if e['role']==('interviewer' if a=='Q' else 'patient')}
            require(attributed==supports and bool(rec['evidence'])==bool(supports),'Evidence for supported choices')
        for e in rec['evidence']:
            turn,role,support=e['turn'],e['role'],e['supports']
            require(type(turn) is int and 1<=turn<=12 and role in ('interviewer','patient') and support in ('A','B'),'Evidence role, location, or alternative')
            require(a!='Q' or role=='interviewer','Questions-only citation contains patient speech')
            source=cases[c]['questions'][turn-1] if role=='interviewer' else dialogue[c][a][turn-1]['answer']
            verify_quote(e['quote'],source)
        rows[r][c][a][d]=status
    require(not (missing_forms & present_forms) and len(present_forms)==report['forms'],'Partial reconstruction first-form receipt')
    require(all(order['gpt',c,d]!=order['opus',c,d] for c,d in all_targets),'Option reversal between readers')
    for r in READERS:
        for d in RECON_DOMAINS:
            require(sum(order[r,c,d]=='A' for c in CASES)==4,'Option position imbalance')
        out=report['readers'][r]
        require(rows[r]==out['by_case'],'Reconstruction item outcomes differ')
        kept=[(c,d) for c,d in all_targets if rows[r][c]['Q'][d] in ('foil','insufficient','conflict')]
        correct=[[c,d] for c,d in all_targets if rows[r][c]['Q'][d]=='correct']
        unknown=[[c,d] for c,d in all_targets if rows[r][c]['Q'][d] in ('invalid','missing_form')]
        require(correct==out['control_recoverable'] and unknown==out['unassessable_controls_excluded'],'Questions-only exclusions')
        require(reconstruction_summary(rows[r],all_targets)==out['all'],'Raw reconstruction aggregates')
        require(reconstruction_summary(rows[r],kept)==out['excluding_control_correct'],'Control-adjusted reconstruction aggregates')
    concordance=load(dest/'reader_concordance.json')
    for a in RECON_ARMS:
        counts=Counter()
        same=0
        details=[]
        for c,d in all_targets:
            g,o=(rows[r][c][a][d] for r in READERS)
            if 'missing_form' in (g,o) or 'invalid' in (g,o):
                group='unresolved'
            else:
                same+=int(g==o)
                match={(True,True):'both_correct',(True,False):'gpt_only_correct',(False,True):'opus_only_correct',(False,False):'neither_correct'}
                group=match[g=='correct',o=='correct']
            counts[group]+=1
            upstream_name={'gpt_only_correct':'gpt_only','opus_only_correct':'opus_only'}.get(group,group)
            details.append({'case':c,'domain':d,'gpt':g,'opus':o,'group':upstream_name})
        official=report['cross_reader_by_arm'][a]
        require(official=={'items':details,'counts':dict(Counter(row['group'] for row in details)),
                'scheduled':16,'paired_valid':16-counts['unresolved'],'same_status':same},'Original reconstruction reader agreement')
        published=concordance[a]
        require(published['scheduled_targets']==sum(counts.values())==16 and
                all(published[k]==counts[k] for k in ('both_correct','gpt_only_correct','opus_only_correct','neither_correct','unresolved')),'Cross-reader reconstruction denominator')
    print('Verified reconstruction of 16 targets in four conditions for each of two readers (%d of 64 first forms).'%report['forms'])


def near_or_null(a,b):
    if a is None or b is None:
        return a is b
    return math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-14)

def verify_external_lengths(root):
    report=load(root/'external-task/release.json')
    expected_refs={'means':{'patient':{'story':237,'laundry':139},'nonclinical':{'story':452,'laundry':162}},
                   'n':{'patient':{'story':26,'laundry':26},'nonclinical':{'story':24,'laundry':25}}}
    require(all(report['reference'][k]==v for k,v in expected_refs.items()),'Published reference denominators or means')
    arms=(*ARMS,'Short')
    tasks=('story','laundry')
    index={}
    for row in report['synthetic']:
        c,a,t=row['case'],row['condition'],row['task']
        require((c,a,t) not in index and c in CASES and a in arms and t in tasks,'External benchmark cell')
        text=row['answer']
        require(isinstance(text,str) and text.strip(),'Missing synthetic answer to external task')
        index[c,a,t]={'english':len(re.findall(r"[A-Za-z]+(?:['’][A-Za-z]+)*",text)), 'whitespace':len(text.split())}
        require(index[c,a,t]==row['counts'],'External benchmark cell word counts')
    require(len(index)==64 and report['integrity']['verified_first_outputs']==64,'External benchmark denominator')
    for metric in ('english','whitespace'):
        table=report['analysis'][metric]
        for a in arms:
            for t in tasks:
                vals=[index[c,a,t][metric] for c in CASES]
                summary={'mean':mean(vals),'median':median(vals),'range':[min(vals),max(vals)]}
                require(summary==table['arms'][a]['task'][t],'External benchmark task word summary')
            arm=table['arms'][a]
            story=arm['task']['story']['mean']
            wash=arm['task']['laundry']['mean']
            ratio=story/wash if wash else None
            require(ratio==arm['story_over_laundry_ratio_of_means'],'External task ratio of means')
            for name,ref in expected_refs['means'].items():
                distance=arm['distance'][name]
                errors={task:abs(math.log(arm['task'][task]['mean']/ref[task])) if arm['task'][task]['mean']>0 else None for task in tasks}
                expected_mean=mean(errors.values()) if all(e is not None for e in errors.values()) else None
                shape=abs(math.log(ratio/(ref['story']/ref['laundry']))) if ratio and ratio>0 else None
                require(all(near_or_null(distance['task_abs_log_error'][t],errors[t]) for t in tasks) and
                        near_or_null(distance['mean_abs_log_error'],expected_mean) and near_or_null(shape,distance['ratio_abs_log_error']),
                        'External benchmark distances')
            for c in CASES:
                expected=index[c,a,'story'][metric]-index[c,a,'laundry'][metric]
                require(expected==table['case_paired_differences'][c][a]['story_minus_laundry_words'],'External paired case difference')
    print('Verified 64 external task outputs, two word-count rules, published reference denominators and task-average distances.')


def verify(root):
    check_manifest(root)
    cases = {x['id']:x for x in load(root / 'cases.json')}
    require(set(cases)==set(CASES), 'Case identifiers')
    dialogues = load(root / 'interviews.json')
    scores = load(root / 'first_scores.json')
    events = load(root / 'semantic_turns.json')
    primary = load(root / 'aggregate/primary.json')
    semantic = load(root / 'aggregate/semantic.json')
    for c in CASES:
        for a in ARMS:
            require([p['question'] for p in dialogues[c][a]] == cases[c]['questions'], 'Interview questions')
            require(all(isinstance(p['answer'],str) and p['answer'].strip() for p in dialogues[c][a]), 'Interview answer')
    all_results = {}
    all_labels = {}
    for reader in READERS:
        p = primary['readers'][reader]
        s = semantic['readers'][reader]
        arm_totals = {a:{} for a in ARMS}
        joint = {left+'_vs_'+right:{} for left,right in CONTRASTS}
        for c in CASES:
            scopes_for_case = scopes(cases[c]['opportunities'])
            vals = {}
            for a in ARMS:
                rounds = scores[reader][c][a]
                require(len(rounds)==2, 'First-score round count')
                vals[a] = [r['score'] for r in rounds]
                for i,r in enumerate(rounds,1):
                    require(r['round']==i, 'First-score ordering')
                    if r['status']=='valid':
                        require(type(r['score']) is int and r['score'] in range(1,5), 'Rating scale')
                        require(r['evidence'], 'Missing primary evidence')
                        for e in r['evidence']:
                            require(1<=e['turn']<=12 and e['quote'] in dialogues[c][a][e['turn']-1]['answer'], 'Primary citation mismatch')
                    else:
                        require(r['status']=='invalid_first_form' and r['score'] is None, 'Invalid first-form handling')
                require(vals[a]==p['by_case'][c][a], 'Raw score mismatch')
                require(set(events[reader][c][a])==set(scopes_for_case), 'Semantic category coverage')
                for metric, turns in scopes_for_case.items():
                    block = events[reader][c][a][metric]
                    labels = block['labels']
                    require(set(labels)=={str(t) for t in turns} and set(labels.values())<=set(LABELS), 'Eligible semantic turns')
                    require(set(block['evidence'])=={t for t,v in labels.items() if v in ('positive','uncertain')}, 'Flag evidence coverage')
                    for t,e in block['evidence'].items():
                        answer = dialogues[c][a][int(t)-1]['answer']
                        verify_quote(e['quote'], answer)
                        require(e['reason'].strip(), 'Semantic justification')
                        if metric=='avoidable_recap':
                            require(1<=e['earlier_turn']<int(t), 'Earlier turn for recap')
                            verify_quote(e['earlier_quote'], dialogues[c][a][e['earlier_turn']-1]['answer'])
                    n = Counter(labels.values())
                    row = {v:n[v] for v in LABELS}
                    row['eligible'] = len(labels)
                    require(row == s['by_case'][c][a][metric], 'Semantic case counts')
                    arm_totals[a].setdefault(metric,Counter()).update(row)
                    all_labels[reader,c,a,metric] = labels
            for left,right in CONTRASTS:
                joint[left+'_vs_'+right][c] = compare(vals[left],vals[right])
        for k, by_case in joint.items():
            require(p['contrasts'][k] == {'by_case':by_case, 'counts':dict(Counter(by_case.values()))}, 'Primary contrast: '+k)
        require(arm_totals == s['by_arm'], 'Semantic arm totals')
        all_results[reader] = {k:dict(Counter(v.values())) for k,v in joint.items()}
    for metric, report in semantic['cross_reader'].items():
        counts = Counter()
        for c in CASES:
            for a in ARMS:
                other = all_labels['opus',c,a,metric]
                for turn, x in all_labels['gpt',c,a,metric].items():
                    y=other[turn]
                    if x in ('uncertain','missing') or y in ('uncertain','missing'):
                        counts['missing_or_uncertain']+=1
                    elif x==y:
                        counts['both_'+x]+=1
                    else:
                        counts['gpt_only' if x=='positive' else 'opus_only']+=1
        den = 2*counts['both_positive']+counts['gpt_only']+counts['opus_only']
        ratio = 2*counts['both_positive']/den if den else None
        require(counts==report['paired_counts'] and ratio==report['positive_agreement'], 'Semantic inter-reader agreement')
    verify_reconstruction(root, cases, dialogues)
    verify_external_lengths(root)
    print('Verified 8 cases, 24 interviews, 96 first ratings and 7 semantic categories across two readers.')
    print(json.dumps(all_results,indent=2,sort_keys=True))

if __name__ == '__main__':
    verify(Path(__file__).resolve().parent)
