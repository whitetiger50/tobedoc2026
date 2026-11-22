"""Frozen descriptive analysis. Each criterion is kept separate; no model calls."""
from collections import Counter
from datetime import datetime,timezone
import hashlib,importlib.util
from common import HERE,ROOT,BASE,FACETS,read,dump,sha,target_flags,validate_safe,canonical
spec=importlib.util.spec_from_file_location('m18stats',HERE/'analysis_stats.py')
ST=importlib.util.module_from_spec(spec);spec.loader.exec_module(ST)

def summary(matrix):return ST.clean(ST.matrix_summary(matrix))

def main():
    corpus=read(HERE/'corpus.json');schedule=read(HERE/'schedule.json')['slots'];terms=read(HERE/'perturbation-spec.json')['repeat_terms']
    author_audit=read(HERE/'author-prejudge-audit.json');eligibility={r['item_id']:r for r in author_audit['rows']}
    collected={};completion=Counter();audit=[];audit_keys={};completion_cells={}
    for slot in schedule:
        completion['planned']+=1;directory=HERE/'reviews'/slot['provider']/slot['opaque_id']
        cell=completion_cells.setdefault(f"{slot['criterion']}:{slot['provider']}:r{slot['repetition']}",Counter());cell['planned']+=1
        if (directory/'started.json').exists():completion['submitted']+=1;cell['submitted']+=1
        if not (directory/'validated.json').exists():continue
        v=read(directory/'validated.json');raw=read(directory/'parsed.json') if (directory/'parsed.json').exists() else None
        completion['recorded']+=1;completion['numeric_valid']+=bool(v.get('realism_numeric_valid'))
        cell['recorded']+=1;cell['numeric_valid']+=bool(v.get('realism_numeric_valid'))
        completion['fully_schema_valid']+=bool(v.get('fully_schema_valid'))
        completion['responses_with_schema_errors']+=bool(v.get('schema_errors'))
        completion['quote_errors']+=len(v.get('quote_errors',[]))
        completion['consistency_warnings']+=len(v.get('consistency_warnings',[]))
        collected[slot['item_id'],slot['criterion'],slot['provider'],slot['repetition']]={'slot':slot,'v':v,'raw':raw,
            'directory':str(directory.relative_to(ROOT)),'response_characters':len((directory/'response.txt').read_text()),
            'timestamp_utc':read(directory/'metadata.json')['timestamp_utc']}
    result_items=[]
    for row in corpus['items']:
        item={k:row[k] for k in ['item_id','case_id','condition','kind','semantic_id','parent_id','manipulation_realized']}
        item['prejudge_target_status']=eligibility[row['item_id']]['status'];item['prejudge_target_eligible']=eligibility[row['item_id']]['target_eligible'];item['cells']={}
        for criterion in ['realism','ccf']:
            item['cells'][criterion]={}
            for provider in ['codex','claude']:
                scores=[];records=[]
                for repetition in [1,2,3]:
                    found=collected.get((row['semantic_id'],criterion,provider,repetition))
                    if not found:scores.append(None);records.append(None);continue
                    v=found['v'];scores.append(v.get('realism_score'))
                    common=validate_safe(found['raw'],row['payload']) if isinstance(found['raw'],dict) else None
                    common_schema_valid=bool(common and common['fully_schema_valid'] and not common['quote_errors'])
                    flags=target_flags(v,row['payload'],row['targets'],terms)
                    usable=flags['target_record_usable']
                    natural_goal=None
                    if row['condition']=='N':
                        p08=next(t['text'] for t in row['payload']['dialogue'] if t['turn_id']=='P08')
                        natural_goal=target_flags(v,row['payload'],{'P08':[[0,len(p08)]]},terms)
                    key=hashlib.sha256(f'audit:M18:{row["semantic_id"]}:{canonical(row["targets"])}:{criterion}:{provider}:{repetition}'.encode()).hexdigest()[:18]
                    records.append({'repetition':repetition,'score':v.get('realism_score'),'validated':v,'author_audit_id':key,
                        'target_flags':flags,'common_output_usable':usable,'common_schema_quote_valid':common_schema_valid,'source':found['directory'],
                        'natural_goal_turn_flags':natural_goal,'response_characters':found['response_characters']})
                    # Labels, scores and CCF-only fields withheld from author extraction view.
                    if key in audit_keys:
                        audit_keys[key]['logical_item_ids'].append(row['item_id']);continue
                    target_turns=list(row['targets']);dialogue=row['payload']['dialogue'];related=[]
                    include=set(target_turns+['P01','P02','P03','D04','D06','D08'])
                    for t in dialogue:
                        if t['turn_id'] in target_turns or t['turn_id'].replace('D','P',1) in target_turns or t['turn_id'] in include:related.append(t)
                    audit.append({'audit_id':key,'target_ranges':row['targets'],'dialogue_excerpt':related,
                      'communication':row['payload']['communication'],
                      'common_claims':[{'field':'global','adverse':v.get('realism_score')in[1,2,3],
                         'reason':v.get('realism_reason'),'evidence':v.get('realism_evidence',[]) if v.get('realism_score')in[1,2,3] else []}]+
                         [{'field':name,'adverse':f.get('rating')in[0,1],'reason':f.get('reason'),'evidence':f.get('evidence',[])} for name,f in v.get('facets',{}).items()],
                      'common_output_usable':usable,'record_state':flags['record_state']})
                    audit_keys[key]={'item_id':row['item_id'],'logical_item_ids':[row['item_id']],
                      'criterion':criterion,'provider':provider,'repetition':repetition}
                finite=[s for s in scores if s is not None]
                item['cells'][criterion][provider]={'scores':scores,'mean':sum(finite)/len(finite) if finite else None,'readings':records}
        item['two_model_mean_by_criterion']={c:(item['cells'][c]['codex']['mean']+item['cells'][c]['claude']['mean'])/2
          if all(s is not None for p in ['codex','claude'] for s in item['cells'][c][p]['scores']) else None for c in ['realism','ccf']}
        result_items.append(item)
    groups=[];unique_ids=set(corpus['unique_item_ids'])
    for criterion in ['realism','ccf']:
        for provider in ['codex','claude']:
            for label,selected in [('natural',[i for i in result_items if i['condition']=='N']),
                                   ('all_unique',[i for i in result_items if i['item_id']in unique_ids])]+[(c,[i for i in result_items if i['condition']==c]) for c in ['P','G','U','F','X']]:
                # Deduplicate within a stratum, never inflate by shared aliases.
                dedup={i['semantic_id']:i for i in selected};selected=list(dedup.values())
                matrix=[i['cells'][criterion][provider]['scores'] for i in selected]
                stats=summary(matrix);flat=[v for row in matrix for v in row if v is not None]
                states=Counter('missing' if any(v is None for v in row) else 'all4' if row==[4,4,4] else 'all_same_below4' if len(set(row))==1 else 'crosses4' if 4 in row else 'varies_below4' for row in matrix)
                target=[]
                for i in selected:
                    for rec in i['cells'][criterion][provider]['readings']:
                        if rec is not None:target.append(rec)
                usable=[x for x in target if x['common_output_usable']]
                eligible_items=[i for i in selected if i['prejudge_target_eligible'] and (i['condition']=='N' or i['manipulation_realized'])]
                eligible_records=[r for i in eligible_items for r in i['cells'][criterion][provider]['readings'] if r is not None]
                eligible_usable=[r for r in eligible_records if r['common_output_usable']]
                groups.append({'criterion':criterion,'provider':provider,'stratum':label,
                  'item_ids':[i['item_id'] for i in selected],'statistics':stats,
                  'score_counts':dict(Counter(flat)),'mean':sum(flat)/len(flat) if flat else None,
                  'ceiling4':{'n':flat.count(4),'denominator':len(flat),'proportion':flat.count(4)/len(flat) if flat else None},
                  'text_repeat_states':dict(states),'target_counts':{'returned':len(target),'common_usable':len(usable),
                    'unusable':len(target)-len(usable),'target_problem_explicit':sum(x['target_flags']['target_problem_explicit'] for x in usable),
                    'repeat_lexical_candidate':sum(x['target_flags']['repeat_lexical_candidate'] for x in usable),
                    'no_explicit_target_problem':sum(not x['target_flags']['target_problem_explicit'] for x in usable)},
                  'target_record_states':dict(Counter(r['target_flags']['record_state'] for r in target)),
                  'eligible_target_counts':{'texts':len(eligible_items),'planned_readings':3*len(eligible_items),
                    'returned_readings':len(eligible_records),'assessable':len(eligible_usable),
                    'target_problem_explicit':sum(r['target_flags']['target_problem_explicit'] for r in eligible_usable),
                    'repeat_lexical_candidate':sum(r['target_flags']['repeat_lexical_candidate'] for r in eligible_usable),
                    'no_explicit_target_problem':sum(not r['target_flags']['target_problem_explicit'] for r in eligible_usable)},
                  'leave_one_profile_out':[{'omitted':case,'statistics':summary([i['cells'][criterion][provider]['scores'] for i in selected if i['case_id']!=case])} for case in ['DEV-M18-01','DEV-M18-02','DEV-M18-03']] if label=='natural' else []})
    comparisons=[]
    for i in result_items:
        if not i['parent_id']:continue
        parent=next(p for p in result_items if p['item_id']==i['parent_id'])
        for criterion in ['realism','ccf']:
            for provider in ['codex','claude']:
                a=parent['cells'][criterion][provider];b=i['cells'][criterion][provider]
                comparisons.append({'item_id':i['item_id'],'parent_id':i['parent_id'],'condition':i['condition'],
                    'criterion':criterion,'provider':provider,'parent_scores':a['scores'],'control_scores':b['scores'],
                    'mean_difference':b['mean']-a['mean'] if i['manipulation_realized'] and a['mean']is not None and b['mean']is not None else None,
                    'identical_input_alias':i['semantic_id']==parent['semantic_id'],
                    'inserted_span_parent_detection':'not_applicable' if i['condition']in['F','X'] else 'content_changed_or_relocated_not_same_span'})
    paired=[]
    for provider in ['codex','claude']:
        natural=[i for i in result_items if i['condition']=='N']
        natural=list({i['semantic_id']:i for i in natural}.values())
        complete=[i for i in natural if all(v is not None for c in ['realism','ccf'] for v in i['cells'][c][provider]['scores'])]
        below=[i for i in complete if any(v<4 for c in ['realism','ccf'] for v in i['cells'][c][provider]['scores'])]
        paired.append({'provider':provider,'same_natural_inputs_both_three_complete':len(complete),
          'item_ids':[i['item_id'] for i in complete],
          'paired_natural_statistics':{c:summary([i['cells'][c][provider]['scores'] for i in complete]) for c in ['realism','ccf']},
          'at_least_one_below4_in_either_criterion':{'texts':len(below),'item_ids':[i['item_id'] for i in below],
            'statistics':{c:summary([i['cells'][c][provider]['scores'] for i in below]) for c in ['realism','ccf']}},
          'vectors':[{'item_id':i['item_id'],'realism':i['cells']['realism'][provider]['scores'],'ccf':i['cells']['ccf'][provider]['scores']} for i in complete]})
    result={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'completion':dict(completion),'condition_rows':24,
      'unique_inputs':corpus['unique_inputs'],'natural_generations':9,'new_patient_generation_calls':72,
      'groups':groups,'items':result_items,'parent_control_comparisons':comparisons,'paired_natural_comparisons':paired,'completion_by_cell':{k:dict(v) for k,v in completion_cells.items()},
      'limits':'3profiles;dependentpairs/sharedparents/aliases;authorhypothesesnotclinicalgold;CCFoutputdemanddiffers;nomeanscaleequivalence',
      'source_sha256':{'corpus.json':sha(HERE/'corpus.json'),'schedule.json':sha(HERE/'schedule.json')}}
    dump(HERE/'results.json',result)
    # Random-looking sort is deterministic and conceals criterion/provider keys in this view.
    dump(HERE/'author-extraction-input.json',{'status':'labels/scoreswithheldnotindependentorfullyblind','rows':sorted(audit,key=lambda x:x['audit_id'])})
    dump(HERE/'author-extraction-keys.json',audit_keys)
    print('Results and author extraction views saved; recorded',completion['recorded'],'of',completion['planned'],'calls; no aggregate scores printed')

if __name__=='__main__':main()
