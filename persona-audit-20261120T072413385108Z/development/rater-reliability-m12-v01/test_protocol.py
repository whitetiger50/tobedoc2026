"""Offline parser/statistic fixtures; not model-generated research ratings."""
from copy import deepcopy
import json
import experiment as e
import analysis_stats as s

def main():
 payload=e.read(e.HERE/'corpus.json')['items'][0]['payload']
 x={'realism_score':4,'realism_reason':'오프라인 스키마 검사 전용','realism_evidence':[],'facets':{name:{'rating':2,'uncertain':False,'reason':'스키마 검사','evidence':[],'context_refs':[]} for name in e.FACETS}}
 assert e.validate(x,payload)['fully_schema_valid']
 bad=deepcopy(x);bad['facets']['grounding'].update(rating=0,evidence=[{'patient_turn_id':'P04','quote':'원문에 없는 인용'}],context_refs=['fact:living']);v=e.validate(bad,payload)
 assert v['realism_score']==4 and v['facets']['grounding']['numeric_valid'] and len(v['quote_errors'])==1
 missing=deepcopy(x);del missing['facets']['naturalness'];v=e.validate(missing,payload);assert v['realism_score']==4 and not v['fully_schema_valid']
 na=deepcopy(x);na['facets']['continuity'].update(rating=None,uncertain=True,reason='적용자료 부족 검사');v=e.validate(na,payload);assert v['facets']['continuity']['semantic_NA'] and v['fully_schema_valid']
 assert e.parse('```json\n'+json.dumps(x)+'\n```')==x
 corpus=e.read(e.HERE/'corpus.json');slots=e.read(e.HERE/'schedule.json')['slots'];assert len(slots)==90 and len({a['opaque_id'] for a in slots})==90
 assert len(corpus['items'])==15 and sum(r['kind']=='natural' for r in corpus['items'])==12
 for item in corpus['items']:assert e.sha(e.HERE/'inputs'/f"{item['item_id']}.json")==item['input_sha256']
 stats=s.fixtures();print('PASS offline parser:evidence,NA,missing fields,score retention,fences;90slots/input hashes;4statistic fixture groups')
 print(json.dumps(stats,ensure_ascii=False))
if __name__=='__main__':main()
