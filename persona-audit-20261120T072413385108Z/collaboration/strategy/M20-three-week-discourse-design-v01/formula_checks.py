"""Offline design arithmetic only. No patient data, model calls or experiment results."""
from itertools import product
from pathlib import Path
import json

def score(a,b):return a-b
def goal_sensitivity(rows):
    mean=lambda x:sum(x)/len(x)
    return sum(g*mean([score(*x)for x in rows[g,o]])for g in [1,-1]for o in [0,1])/4
def order_sensitivity(rows):
    mean=lambda x:sum(x)/len(x)
    return sum(mean([score(*x)for x in rows[g,0]])-mean([score(*x)for x in rows[g,1]])for g in [1,-1])/4
def constant(a,b):return {(g,o):[(a,b)]*2 for g in [1,-1] for o in [0,1]}
def bounds(a,b):
    values=[score(x,y)for x in ([a]if a is not None else[0,1])for y in ([b]if b is not None else[0,1])]
    return [min(values),max(values)]

def main():
    follow_goal={(g,o):([(1,0)]*2 if g==1 else[(0,1)]*2)for g in [1,-1]for o in [0,1]}
    follow_last={(g,o):([(1,0)]*2 if o==0 else[(0,1)]*2)for g in [1,-1]for o in [0,1]}
    assert goal_sensitivity(follow_goal)==1 and order_sensitivity(follow_goal)==0
    assert goal_sensitivity(follow_last)==0 and order_sensitivity(follow_last)==1
    assert goal_sensitivity(constant(1,0))==0
    assert goal_sensitivity(constant(1,1))==goal_sensitivity(constant(0,0))==0
    # A drop in P need not mean less initiation of the assigned goal.
    for g in [1,-1]:
        target=(1,0)if g==1 else(0,1)
        assert target[0 if g==1 else 1]==(1,1)[0 if g==1 else 1]==1
    assert bounds(1,None)==[0,1] and bounds(None,1)==[-1,0]
    assert bounds(None,None)==[-1,1] and bounds(0,0)==[0,0]
    for p10,p01,p11,p00 in product(range(3),repeat=4):
        total=p10+p01+p11+p00
        if not total:continue
        E=(p10+p01)/total;S=(p10-p01)/total
        if E:assert abs(S-E*((p10-p01)/(p10+p01)))<1e-12
        target=(p10+p11)/total;alternative=(p01+p11)/total
        assert abs(S-(target-alternative))<1e-12
    assert 8*3*2*2*2==192
    assert 192*2+12*2*2+24*2==480
    assert 192+24==216 and 480+48==528
    out={'status':'offline_mathematical_fixtures_not_empirical_results','checked_groups':8,
      'goal_vs_order_separation':True,'both_vs_neither_preserved':True,'P_drop_without_goal_initiation_drop_counterexample':True,
      'partial_field_bounds':True,'ED_and_target_minus_alternative_identities':True,
      'main_generation':192,'planned_ratings_excluding_development':480,'maximum_generation_with_development':216,
      'maximum_ratings_with_development':528,'new_model_calls':0}
    (Path(__file__).resolve().parent/'formula-checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print('Offline formula and call-budget checks passed; no empirical outputs generated')
if __name__=='__main__':main()
