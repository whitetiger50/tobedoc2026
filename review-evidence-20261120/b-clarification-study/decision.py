"""Descriptive prespecified B+ vs B decisions; all uncertainty stays visible."""
from collections import Counter
from itertools import product
import json
from pathlib import Path
from statistics import mean

HERE=Path(__file__).resolve().parent
ARMS=('B','BC','T2')
CLASSES=('material','context_resolved','same_answer','clear')
READERS=('gpt','opus')
IDS=[f'C{i:02d}' for i in range(1,9)]
WAIT={'targeted_yield','generic_yield'}
UNKNOWN={'missing','uncertain','insufficient'}
def load(name): return json.loads((HERE/name).read_text())
def sums(values): return [sum(v[i] for v in values) for i in (0,1)]
def diff(x,y): return [x[0]-y[1],x[1]-y[0]]
def interval(value,positive):
    return [int(value in positive),int(value in positive or value in UNKNOWN)]
def direction(a,b):
    if a is None or b is None:return None
    return (a>b)-(a<b)
def stability(values):
    if None in values:return 'missing'
    return ('win' if values[0]>0 else 'tie' if values[0]==0 else 'loss') if values[0]==values[1] else 'unstable'
def reality(scores):
    flat=[x for c in scores.values() for a in ARMS for rep in ('1','2') for x in c[a][rep] if x is not None]
    saturation=bool(flat and max(Counter(flat).values())/len(flat)>=.8)
    out={'score_distribution':dict(Counter(flat)),'saturated':saturation,'contrasts':{}}
    for left,right in [('BC','B'),('BC','T2'),('T2','B')]:
        preserved=[];doubleloss=[];possible_doubleloss=[];missing=[];by_case={};by_rep={1:Counter(),2:Counter()};ds=[]
        for cid,cell in scores.items():
            per=[];signs=[];deltas=[]
            for rep in (1,2):
                l,r=cell[left][str(rep)],cell[right][str(rep)]
                v=[direction(a,b) for a,b in zip(l,r)]
                per.append(stability(v));signs.extend(v);by_rep[rep][per[-1]]+=1
                deltas.extend(a-b for a,b in zip(l,r) if a is not None and b is not None)
            if len(deltas)==4:ds.append(mean(deltas))
            if None in signs:missing.append(cid)
            elif min(signs)>=0:preserved.append(cid)
            if per==['loss','loss']:doubleloss.append(cid)
            if all(s is None or s<0 for s in signs):possible_doubleloss.append(cid)
            by_case[cid]={'by_replicate':per,'four_signs':signs,'mean_score_diff':mean(deltas) if len(deltas)==4 else None}
        out['contrasts'][left+'_vs_'+right]={'preserved_cases':preserved,'double_loss_cases':doubleloss,
          'incomplete_cases':missing,'case_mean_difference':mean(ds) if len(ds)==8 else None,'by_case':by_case,
          'by_replicate':by_rep,'possible_double_loss_cases':possible_doubleloss,'operational_preservation':len(preserved)>=6 and not possible_doubleloss}
    return out

def behavior(rows):
    grid={(r['case'],r['rep'],r['turn'],r['arm']):r for r in rows}
    assert len(rows)==len(grid)==576
    by_arm={};pairs={}
    for a in ARMS:
        by_arm[a]={}
        for cl in CLASSES:
            rr=[x for x in rows if x['arm']==a and x['planned']==cl]
            by_arm[a][cl]={'eligible':len(rr),'targeted':sum(x['action']=='targeted_yield' for x in rr),
              'wait_any':sum(x['action'] in WAIT for x in rr),'wait_including_incidental':sum(x['action'] in WAIT|{'incidental_yield'} for x in rr),'action':dict(Counter(x['action'] for x in rr)),
              'need':dict(Counter(x['need'] for x in rr))}
        rr=[x for x in rows if x['arm']==a]
        by_arm[a]['followup_substantive']=sum(x['followup'] and x['responsiveness']=='substantive' for x in rr)
        by_arm[a]['followup_eligible']=sum(x['followup'] for x in rr)
        by_arm[a]['harm_turns']=sum(x['harm']=='consequential' for x in rr)
        by_arm[a]['harm_cases']=sorted({x['case'] for x in rr if x['harm']=='consequential'})
        by_arm[a]['clear_offtarget']=sum(x['planned']=='clear' and x['responsiveness']=='off_target' for x in rr)
    for cl in CLASSES:
        selected={('targeted_yield')} if cl=='material' else WAIT
        vv=[];de=[];gained=lost=0;case_bounds={c:[] for c in IDS};rep_bounds={1:[],2:[]}
        for c,n,t in product(IDS,(1,2),range(1,13)):
            a,b=grid[c,n,t,'BC'],grid[c,n,t,'B']
            if a['planned']!=cl:continue
            assert b['planned']==cl
            xa,xb=a['action'],b['action'];d=diff(interval(xa,selected),interval(xb,selected))
            de.append(int(xa in selected)-int(xb in selected)); vv.append(d);case_bounds[c].append(d);rep_bounds[n].append(d)
            gained+=int(xa in selected and xb not in selected and xb not in UNKNOWN)
            lost+=int(xb in selected and xa not in selected and xa not in UNKNOWN)
        pairs[cl]={'observed_difference':sum(de),'bounds':sums(vv),'new_certain':gained,'lost_certain':lost,
            'by_case_bounds':{c:sums(v) for c,v in case_bounds.items()},'by_rep_bounds':{n:sums(v) for n,v in rep_bounds.items()}}
    def actual_shared(needset,actionset):
        obs=0; shared=0;case=set();usable=set();vals=[];possible=0
        for c,n,t in product(IDS,(1,2),range(1,13)):
            a,b=grid[c,n,t,'BC'],grid[c,n,t,'B']
            if a['planned']=='clear':continue
            na,nb=a['need'],b['need']
            if any(k not in needset|UNKNOWN for k in (na,nb)):continue
            d=diff(interval(a['action'],actionset),interval(b['action'],actionset))
            if na in needset and nb in needset:
                if a['action'] not in UNKNOWN and b['action'] not in UNKNOWN:usable.add(c)
                shared+=1;case.add(c);obs+=int(a['action'] in actionset)-int(b['action'] in actionset);vals.append(d)
            else:
                possible+=1;vals.append([min(0,d[0]),max(0,d[1])])
        return {'shared_count':shared,'shared_cases':len(case),'shared_decisive_cases':len(usable),'difference':obs,'possible_additional_shared':possible,'bounds':sums(vals)}
    needed=actual_shared({'material'},{'targeted_yield'}); unneeded=actual_shared({'resolved','same_answer'},WAIT)
    p=pairs['material'];lo=p['bounds'][0];downs=sum(b[0]<0 for b in p['by_case_bounds'].values());ups=sum(b[0]>0 for b in p['by_case_bounds'].values())
    function=lo>0 and ups>=4 and ups>downs and all(v[0]>=0 for v in p['by_rep_bounds'].values())
    extrapolated=needed['bounds'][0]>0 and needed['shared_decisive_cases']>=4
    noextra=all(pairs[cl]['bounds'][1]<=0 for cl in CLASSES[1:]) and unneeded['shared_count']>0 and unneeded['bounds'][1]<=0
    def arm_bounds(arm,field,labels,subset):
        return sums([interval(x[field],labels) for x in rows if x['arm']==arm and subset(x)])
    follow=diff(arm_bounds('BC','responsiveness',{'substantive'},lambda x:x['followup']),
                arm_bounds('B','responsiveness',{'substantive'},lambda x:x['followup']))
    def harm_bounds(arm):
        positive=set();possible=set()
        for x in rows:
            if x['arm']!=arm:continue
            if x['harm']=='consequential':positive.add(x['case'])
            if x['harm'] in UNKNOWN|{'consequential'}:possible.add(x['case'])
        return [len(positive),len(possible)]
    hdelta=diff(harm_bounds('BC'),harm_bounds('B'))
    return {'by_arm':by_arm,'paired_by_planned':pairs,'shared_actual_material':needed,'shared_actual_nonmaterial':unneeded,
            'followup_difference_bounds':follow,'consequential_harm_case_difference_bounds':hdelta,'gates':{
              'planned_targeted_improvement':function,'shared_actual_improvement':extrapolated,
              'no_excess_waits_on_negatives':noextra,'no_followup_reduction':follow[0]>=0,'no_harm_case_increase':hdelta[1]<=0}}

def main():
    primary=load('primary-results.json'); ctrl=load('challenge/results.json')
    out={'readers':{},'decision':{}}
    for reader in READERS:
        re=reality(primary['scores'][reader]);be=behavior(load('behavior/'+reader+'-turns.json'))
        out['readers'][reader]={'reality':re,'behavior':be,'calibration':ctrl[reader]}
    for key in ('realism','behavior','joint_research_candidate'):
        re_ok=all(r['calibration']['qualified'] and not r['reality']['saturated'] and
                  r['reality']['contrasts']['BC_vs_B']['operational_preservation'] for r in out['readers'].values())
        be_ok=all(all(r['behavior']['gates'].values()) for r in out['readers'].values())
        out['decision'][key]=re_ok if key=='realism' else be_ok if key=='behavior' else re_ok and be_ok
    (HERE/'decision.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    print(out['decision'])
if __name__=='__main__':main()
