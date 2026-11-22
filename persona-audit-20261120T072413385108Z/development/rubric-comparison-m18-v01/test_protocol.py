"""Offline fixtures for numeric retention, quotations and frozen extraction, not patient ratings."""
from copy import deepcopy
from common import BASE,FACETS,HERE,read,dump,validate_safe,target_flags,overlaps_quote,canonical,quote_location

def main():
    patient=read(HERE/'cases.json')['cases'][0]['input']['patient']
    payload={'patient_profile':patient,'communication':{},'prior_authored_context':[],
      'dialogue':[{'turn_id':'D01','speaker':'clinician','text':'Q'},
                  {'turn_id':'P01','speaker':'patient','text':'앞구절 중복구절 뒤구절'}]}
    base={'realism_score':3,'realism_reason':'국소 반복 문제','realism_evidence':[{'patient_turn_id':'P01','quote':'중복구절'}],
      'facets':{k:{'rating':2,'uncertain':False,'reason':'문제 미지적','evidence':[],'context_refs':[]} for k in FACETS}}
    base['facets']['naturalness']={'rating':1,'uncertain':False,'reason':'정형 반복','evidence':[{'patient_turn_id':'P01','quote':'중복구절'}],'context_refs':['turn:D01']}
    v=validate_safe(base,payload);assert v['fully_schema_valid'] and not v['quote_errors']
    f=target_flags(v,payload,{'P01':[[4,8]]},['반복']);assert f['target_problem_explicit'] and f['repeat_lexical_candidate']
    assert not overlaps_quote('앞구절',payload['dialogue'][1]['text'],[[4,8]])
    assert not overlaps_quote(' ',payload['dialogue'][1]['text'],[[3,4]])
    altered=deepcopy(base);altered['facets']['naturalness']['evidence'][0]['patient_turn_id']='P99'
    bad=validate_safe(altered,payload);assert bad['realism_score']==3 and bad['quote_errors']
    malformed=deepcopy(base);malformed['realism_evidence'][0]['patient_turn_id']=[]
    bad=validate_safe(malformed,payload);assert bad['realism_score']==3 and bad['facets']['naturalness']['rating']==1 and not bad['fully_schema_valid']
    partial=deepcopy(base);partial['realism_evidence'][0]['quote']='notintheturn'
    pv=validate_safe(partial,payload);flags=target_flags(pv,payload,{'P01':[[4,8]]},['반복'])
    assert flags['target_problem_explicit'] and flags['target_record_usable'] and flags['unresolved_adverse_evidence']
    partial['facets']['naturalness']['evidence'][0]['quote']='alsonotintheturn'
    pv=validate_safe(partial,payload);flags=target_flags(pv,payload,{'P01':[[4,8]]},['반복'])
    assert not flags['target_record_usable'] and flags['record_state']=='unresolved_adverse_evidence'
    ccf=deepcopy(base);ccf.update(criteria_version='CCF-R1-proposal',observations=[{'id':'e1','kind':'form_repetition',
      'patient_turn_id':'P01','quote':'중복구절','related_evidence':[{'patient_turn_id':'P01','quote':'중복구절'}],
      'context_refs':['turn:D01'],'function':'unclear','finding':'supported_issue','primary_facet':'naturalness',
      'reason':'명시한 국소 문제','used_in_global':True}],boundary_34={'flag':False,'observation_ids':[],'reason':''},
      coverage={'repetition_candidate_presence':'present','additional_candidates_unreported':False})
    ccf['realism_evidence'][0]['context_refs']=['turn:D01']
    cv=validate_safe(ccf,payload,'ccf');assert cv['fully_schema_valid'] and not cv['consistency_warnings']
    ccf['boundary_34']={'flag':True,'observation_ids':['missing'],'reason':'불확실'}
    cv=validate_safe(ccf,payload,'ccf');assert cv['realism_score']==3 and not cv['fully_schema_valid']
    ccf=deepcopy(base);cv=validate_safe(ccf,payload,'ccf');assert cv['realism_score']==3 and cv['ccf_schema_errors']
    assert canonical({'a':1,'b':2})==canonical({'b':2,'a':1}) and canonical({'a':1})!=canonical({'a':2})
    four=deepcopy(base);four['realism_score']=4;four['realism_reason']='반복을 포함해 자연스러운 반응'
    four['facets']['naturalness']={'rating':2,'uncertain':False,'reason':'문제 없음','evidence':[],'context_refs':[]}
    fv=validate_safe(four,payload);assert not target_flags(fv,payload,{'P01':[[4,8]]},['반복'])['target_problem_explicit']
    four['facets']['naturalness'].update(uncertain=True,evidence=[{'patient_turn_id':'P01','quote':'중복구절'}])
    fv=validate_safe(four,payload);assert target_flags(fv,payload,{'P01':[[4,8]]},['반복'])['record_state']=='uncertain_or_ambiguous_reference'
    four['facets']['naturalness'].update(rating=0,uncertain=False,evidence=[])
    fv=validate_safe(four,payload);assert fv['realism_score']==4 and target_flags(fv,payload,{'P01':[[4,8]]},['반복'])['record_state']=='unresolved_adverse_evidence'
    twoturns=deepcopy(payload);twoturns['dialogue'].append({'turn_id':'P02','speaker':'patient','text':'중복구절'})
    assert not target_flags(v,twoturns,{'P02':[[0,4]]},['반복'])['target_problem_explicit']
    assert quote_location('중복구절','중복구절 그리고 중복구절',[[0,4]])['ambiguous']
    dump(HERE/'fixture-results.json',{'offline_fixture_groups':15,'passed':True,'new_patient_or_judge_calls':0,
      'scope':'spanmatching/numericretention/commonvsCCFschema/boundaryid;notclinicalvalidation'})
    print('Fifteen offline fixture groups passed; no model calls')

if __name__=='__main__':main()
