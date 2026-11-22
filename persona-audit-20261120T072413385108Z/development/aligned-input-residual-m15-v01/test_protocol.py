"""Offline checks; fixture records never become research outputs."""
from pathlib import Path
from copy import deepcopy
import json
from experiment import HERE,ROOT,read,sha,validate
from analysis_stats import fixtures,summarize

def run():
    c=read(HERE/'corpus.json');slots=read(HERE/'schedule.json')['slots'];q=read(HERE/'question-audit.json')
    assert len(c['items'])==9 and len(slots)==54 and len({s['opaque_id'] for s in slots})==54
    assert q['changed_questions']==4 and all(r['patient_known'] and r['author_checked'] for r in q['rows'])
    for n in ['review-role.txt','score-anchors.json']:assert sha(HERE/n)==sha(ROOT/'development/rater-reliability-m12-v01'/n)
    for row in c['items']:
        assert sha(HERE/'inputs'/f'{row["item_id"]}.json')==row['input_sha256']
        assert read(HERE/'inputs'/f'{row["item_id"]}.json')==row['payload']
        subset=[s for s in slots if s['item_id']==row['item_id']]
        assert len(subset)==6 and len({(s['provider'],s['repetition']) for s in subset})==6
    # Two quotations of the same turn in one facet/read are one reported location.
    first=c['items'][0];record={'realism_score':3,'realism_numeric_valid':True,'facets':{
         'naturalness':{'rating':1,'numeric_valid':True,'uncertain':False,'reason':'explicitofflinefixture',
         'evidence':[{'patient_turn_id':'P01','quote':'a','valid_quote':True},{'patient_turn_id':'P01','quote':'b','valid_quote':True}]}}}
    result=summarize({'items':[first]},{(first['item_id'],'codex',1):record})
    assert len(result['reported_locations'])==1 and result['reported_locations'][0]['readings_with_location']==1
    x={'realism_score':3,'realism_reason':'fixture','realism_evidence':[{'patient_turn_id':'P01','quote':'notactualquote'}],'facets':{}}
    v=validate(x,first['payload']);assert v['realism_score']==3 and v['quote_errors']
    return {'9dialogues_54_unique_slots':True,'4question_changes_audited':True,'criteria_M12_byte_identical':True,
            'each_item6identical_semantic_inputs':True,'same_turn_multiquote_not_double_counted':True,
            'existing_parser_preserves_valid_numeric':True,'statistics':fixtures()}
if __name__=='__main__':
    x=run();(HERE/'fixture-results.json').write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');print(json.dumps(x))
