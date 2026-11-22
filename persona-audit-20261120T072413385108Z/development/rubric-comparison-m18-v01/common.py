from pathlib import Path
import hashlib, importlib.util, json, sys
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('M18base',ROOT/'development/rater-reliability-m12-v01/experiment.py')
BASE=importlib.util.module_from_spec(spec);spec.loader.exec_module(BASE)
FACETS=BASE.FACETS
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def dump(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

def fallback_validation(raw,error):
    """Preserve supplied numeric fields even if another malformed field crashes validation."""
    raw=raw if isinstance(raw,dict) else {};score=raw.get('realism_score');good=type(score)is int and 1<=score<=4
    dims={};fs=raw.get('facets') if isinstance(raw.get('facets'),dict) else {}
    for k in FACETS:
        d=fs.get(k) if isinstance(fs.get(k),dict) else {};v=d.get('rating');valid=type(v)is int and 0<=v<=2
        dims[k]={'rating':v if valid else None,'numeric_valid':valid,'semantic_NA':'rating'in d and v is None,
          'uncertain':d.get('uncertain') if type(d.get('uncertain'))is bool else None,'reason':d.get('reason'),
          'evidence':[],'context_refs':[]}
    return {'realism_score':score if good else None,'realism_numeric_valid':good,'realism_reason':raw.get('realism_reason'),
      'realism_evidence':[],'facets':dims,'schema_errors':['validation_exception:'+str(error)],'quote_errors':[],
      'fully_schema_valid':False,'all_provided_quotes_exact':False,'numeric_retention_after_other_field_error':True}

def validate_safe(raw,payload,criterion='realism'):
    try:return validate_ccf(raw,payload) if criterion=='ccf' else BASE.validate(raw,payload)
    except (ValueError,TypeError,KeyError,AssertionError) as error:return fallback_validation(raw,error)

def validate_ccf(raw,payload):
    value=BASE.validate(raw,payload);errors=[];warnings=[]
    turns={t['turn_id']:t['text'] for t in payload['dialogue'] if t['speaker']=='patient'}
    allturns={t['turn_id'] for t in payload['dialogue']};facts={f['id'] for f in payload['patient_profile']['facts']}
    def refs(x,label,needed=False):
        if not isinstance(x,list) or not all(isinstance(y,str) for y in x):errors.append(label+':bad_refs');return
        if needed and not x:errors.append(label+':missing_refs')
        for y in x:
            if y=='authored_context' or y.startswith('turn:') and y[5:] in allturns or y.startswith('fact:') and y[5:] in facts:continue
            errors.append(label+':unknown_ref:'+y)
    def quote(e,label):
        if not isinstance(e,dict):errors.append(label+':bad_quote');return
        tid=e.get('patient_turn_id');q=e.get('quote')
        if tid not in turns or not isinstance(q,str) or not q or q not in turns[tid]:
            value['quote_errors'].append({'dimension':label,'error':'not_exact_patient_quote','patient_turn_id':tid,'quote':q})
    if raw.get('criteria_version')!='CCF-R1-proposal':errors.append('criteria_version:wrong_or_missing')
    ev=raw.get('realism_evidence')
    if not isinstance(ev,list) or not ev:errors.append('realism:required_representative_evidence')
    else:
        for e in ev:
            if isinstance(e,dict):refs(e.get('context_refs'),'realism',True)
    obs=raw.get('observations');obs=obs if isinstance(obs,list) else []
    if not isinstance(raw.get('observations'),list):errors.append('observations:missing_array')
    if len(obs)>3:errors.append('observations:over3')
    ids=[]
    for i,o in enumerate(obs):
        label=f'observations[{i}]'
        if not isinstance(o,dict):errors.append(label+':not_object');continue
        if not isinstance(o.get('id'),str) or not o['id']:errors.append(label+':bad_id')
        else:ids.append(o['id'])
        if o.get('kind') not in ['meaning_repetition','form_repetition','both_repetition','non_repetition_issue']:errors.append(label+':bad_kind')
        if o.get('finding') not in ['supported_issue','supported_use','unclear']:errors.append(label+':bad_finding')
        if o.get('primary_facet') not in FACETS:errors.append(label+':bad_primary_facet')
        if type(o.get('used_in_global')) is not bool:errors.append(label+':bad_used_flag')
        for key in ['function','reason']:
            if not isinstance(o.get(key),str) or not o[key].strip():errors.append(label+':missing_'+key)
        quote(o,label);refs(o.get('context_refs'),label,True)
        rel=o.get('related_evidence')
        if not isinstance(rel,list):errors.append(label+':bad_related_evidence');rel=[]
        for e in rel:quote(e,label+'.related')
        if o.get('kind') in ['form_repetition','both_repetition'] and not rel:errors.append(label+':missing_form_comparison')
    if len(ids)!=len(set(ids)):errors.append('observations:duplicate_id')
    boundary=raw.get('boundary_34')
    if not isinstance(boundary,dict):errors.append('boundary:missing_object');boundary={}
    flag=boundary.get('flag');bid=boundary.get('observation_ids')
    if type(flag)is not bool:errors.append('boundary:bad_flag')
    if not isinstance(bid,list) or not all(isinstance(i,str) and i in ids for i in bid):errors.append('boundary:bad_ids')
    if not isinstance(boundary.get('reason'),str):errors.append('boundary:bad_reason')
    if flag is True and (raw.get('realism_score') not in [3,4] or not bid or not boundary.get('reason')):errors.append('boundary:invalid_true')
    if flag is False and (bid or boundary.get('reason')):errors.append('boundary:invalid_false')
    coverage=raw.get('coverage')
    if not isinstance(coverage,dict) or coverage.get('repetition_candidate_presence') not in ['present','absent','unclear'] or type(coverage.get('additional_candidates_unreported'))is not bool:errors.append('coverage:missing_or_invalid')
    score=value['realism_score'];fac=value['facets']
    if score==4 and any(fac[k]['rating']==0 for k in ['responsiveness','continuity','naturalness']):warnings.append('global4_with_communication0')
    if score is not None and score<4:
        used=[o for o in obs if isinstance(o,dict) and o.get('finding')=='supported_issue' and o.get('used_in_global')is True]
        if not used:warnings.append('global_lowered_without_supported_used_observation')
        for o in used:
            f=fac.get(o.get('primary_facet'),{})
            if f.get('rating') not in [0,1]:warnings.append('global_issue_primary_facet_not0or1:'+str(o.get('id')))
    value['ccf_schema_errors']=errors;value['consistency_warnings']=warnings
    value['schema_errors']+=errors;value['fully_schema_valid']=not value['schema_errors']
    value['all_provided_quotes_exact']=not value['quote_errors']
    value['ccf_extra']={'observations':obs,'boundary_34':boundary,'coverage':coverage}
    return value

def overlaps_quote(quote_text,turn_text,spans):
    """At least two shared letters/digits at exact positions; not a clinical threshold."""
    if not isinstance(quote_text,str) or not quote_text:return False
    start=0
    while True:
        pos=turn_text.find(quote_text,start)
        if pos<0:return False
        for a,b in spans:
            shared=turn_text[max(a,pos):min(b,pos+len(quote_text))]
            if sum(c.isalnum() for c in shared)>=2:return True
        start=pos+1

def quote_location(quote_text,turn_text,spans):
    locations=[];start=0
    if not isinstance(quote_text,str) or not quote_text:return {'target':False,'ambiguous':False}
    while True:
        pos=turn_text.find(quote_text,start)
        if pos<0:break
        target=any(sum(c.isalnum() for c in turn_text[max(a,pos):min(b,pos+len(quote_text))])>=2 for a,b in spans)
        locations.append(target);start=pos+1
    return {'target':bool(locations) and all(locations),'ambiguous':any(locations) and not all(locations)}

def target_flags(validated,payload,target,repeat_terms):
    turns={t['turn_id']:t['text'] for t in payload['dialogue'] if t['speaker']=='patient'}
    broad=[];candidates=[];turn_only=[];ambiguous=[];uncertain_mentions=[]
    sources=[]
    if validated.get('realism_score')in [1,2,3]:sources.append(('global',validated.get('realism_reason')or'',validated.get('realism_evidence',[])))
    for name,f in validated.get('facets',{}).items():
        if f.get('numeric_valid') and f.get('rating')in [0,1]:sources.append((name,f.get('reason')or'',f.get('evidence',[])))
    unresolved=False
    for name,reason,evidences in sources:
        if not evidences or any(not e.get('valid_quote') for e in evidences):unresolved=True
        for e in evidences:
            tid=e.get('patient_turn_id');q=e.get('quote')
            if not e.get('valid_quote') or tid not in target:continue
            record={'source':name,'reason':reason,'patient_turn_id':tid,'quote':q}
            turn_only.append(record)
            location=quote_location(q,turns[tid],target[tid])
            if location['ambiguous']:ambiguous.append(record)
            if location['target']:
                broad.append(record)
                if any(term.casefold() in reason.casefold() for term in repeat_terms):candidates.append(record)
    facets=validated.get('facets',{})
    for name,f in facets.items():
        if not ((f.get('rating')==2 and f.get('uncertain')is True) or f.get('semantic_NA')):continue
        for e in f.get('evidence',[]):
            tid=e.get('patient_turn_id')
            if e.get('valid_quote') and tid in target and overlaps_quote(e.get('quote'),turns[tid],target[tid]):
                uncertain_mentions.append({'source':name,'reason':f.get('reason'),'patient_turn_id':tid,'quote':e.get('quote')})
    readable=bool(validated.get('realism_numeric_valid') and isinstance(validated.get('realism_reason'),str)
      and all(k in facets and (facets[k].get('numeric_valid') or facets[k].get('semantic_NA'))
              and isinstance(facets[k].get('reason'),str) and facets[k]['reason'].strip() for k in FACETS))
    state='explicit_target_issue' if broad else 'uncertain_or_ambiguous_reference' if ambiguous or uncertain_mentions else 'unresolved_adverse_evidence' if unresolved else 'other_issues_only' if readable and sources else 'no_explicit_target_issue' if readable else 'uninterpretable_common_fields'
    return {'target_problem_explicit':bool(broad),'repeat_lexical_candidate':bool(candidates),
            'target_turn_problem_explicit':bool(turn_only),'target_evidence':broad,'repeat_candidates':candidates,
            'record_state':state,'target_record_usable':state in ['explicit_target_issue','no_explicit_target_issue','other_issues_only'],
            'unresolved_adverse_evidence':unresolved,
            'ambiguous_location_evidence':ambiguous,'uncertain_mentions':uncertain_mentions,
            'warning':'lexicalcandidatenotsemanticgold;noexplicitrecordnotproofinternalmiss'}
