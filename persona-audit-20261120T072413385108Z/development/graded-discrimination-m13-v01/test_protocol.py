"""Offline invariants needed for the controlled comparison; never calls models."""
from pathlib import Path
import json
from copy import deepcopy
from experiment import read, sha, validate, parse, ROOT, HERE, CONDITIONS
from analysis_stats import fixtures

def run():
    corpus=read(HERE/'corpus.json');schedule=read(HERE/'schedule.json')
    assert len(corpus['items'])==18 and len(schedule['slots'])==108
    assert len({s['opaque_id'] for s in schedule['slots']})==108
    for name in ['review-role.txt','score-anchors.json']:
        assert sha(HERE/name)==sha(ROOT/'development/rater-reliability-m12-v01'/name)
    for case in ['DEV-M13-01','DEV-M13-02','DEV-M13-03']:
        rows=[r for r in corpus['items'] if r['case_id']==case]
        base=next(r for r in rows if r['condition']=='R')['payload']
        for r in rows:
            altered=r['payload'];a=deepcopy(altered);b=deepcopy(base)
            for x in [a,b]:next(t for t in x['dialogue'] if t['turn_id']=='P02')['text']='MASK'
            assert a==b
            assert read(HERE/'inputs'/f'{r["item_id"]}.json')==altered
            assert sha(HERE/'inputs'/f'{r["item_id"]}.json')==r['input_sha256']
            slots=[s for s in schedule['slots'] if s['item_id']==r['item_id']]
            assert len(slots)==6 and len({(s['provider'],s['repetition']) for s in slots})==6
    for provider in ['codex','claude']:
        allslots=[s for s in schedule['slots'] if s['provider']==provider]
        key={r['item_id']:r['case_id'] for r in corpus['items']}
        assert all(key[a['item_id']]!=key[b['item_id']] for a,b in zip(allslots,allslots[1:]))
    assert parse('```json\n{"x":1}\n```')=={'x':1}
    # A malformed quotation must not remove an otherwise valid primary score.
    payload=corpus['items'][0]['payload'];x={'realism_score':3,'realism_reason':'fixture','realism_evidence':[{'patient_turn_id':'P02','quote':'not an actual phrase'}],'facets':{}}
    v=validate(x,payload);assert v['realism_score']==3 and v['quote_errors']
    return {'corpus_has_exact18texts_108slots':True,'all_variants_only_P02_changed':True,
            'judge_criteria_byte_identical_M12':True,'same_input_across6calls_per_text':True,
            'opaque_ids_unique_and_profile_order_checked':True,'existing_parser_numeric_retention':True,
            'statistics':fixtures()}

if __name__=='__main__':
    x=run();(HERE/'fixture-results.json').write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');print(json.dumps(x))
