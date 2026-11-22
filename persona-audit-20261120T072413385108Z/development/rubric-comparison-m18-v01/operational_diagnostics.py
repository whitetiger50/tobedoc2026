"""Post-run output diagnostics only; preserves frozen ratings and parser decisions."""
from collections import Counter
from common import HERE,read,dump

def main():
    schedule=read(HERE/'schedule.json')['slots'];out=[]
    for criterion in ['realism','ccf']:
        for provider in ['codex','claude']:
            counts=Counter();errors=Counter();details=[];lengths=[]
            for slot in schedule:
                if slot['criterion']!=criterion or slot['provider']!=provider:continue
                d=HERE/'reviews'/provider/slot['opaque_id'];v=read(d/'validated.json')
                counts['returned']+=1;counts['numeric_valid']+=bool(v.get('realism_numeric_valid'))
                counts['schema_valid']+=bool(v.get('fully_schema_valid'));counts['quote_error_records']+=bool(v.get('quote_errors'))
                es=v.get('schema_errors',[]);refs=[e for e in es if 'invalid_context_ref:' in e or 'unknown_ref:' in e]
                if es and len(es)==len(refs):counts['reference_vocabulary_only_schema_failure']+=1
                if refs:counts['any_reference_vocabulary_failure']+=1
                if es and len(es)>len(refs):counts['nonreference_schema_failure']+=1
                for e in es:
                    if 'invalid_context_ref:' in e:errors['invalid_context_ref:'+e.split('invalid_context_ref:',1)[1]]+=1
                    elif 'unknown_ref:' in e:errors['unknown_ref:'+e.split('unknown_ref:',1)[1]]+=1
                    else:errors[e]+=1
                extra=v.get('ccf_extra',{});boundary=extra.get('boundary_34',{}) or {}
                counts['boundary34_true']+=boundary.get('flag') is True
                lengths.append(len((d/'response.txt').read_text()))
                if es or v.get('quote_errors'):details.append({'item_id':slot['item_id'],'repetition':slot['repetition'],'source':str(d),
                  'schema_errors':es,'quote_errors':v.get('quote_errors',[]),'numeric_valid':v.get('realism_numeric_valid')})
            out.append({'criterion':criterion,'provider':provider,'counts':dict(counts),'schema_error_occurrences':dict(errors),
              'response_characters':{'min':min(lengths),'max':max(lengths),'mean':sum(lengths)/len(lengths)},'details':details})
    results=read(HERE/'results.json');goal=[];controls=[]
    for criterion in ['realism','ccf']:
        for provider in ['codex','claude']:
            c=Counter()
            for i in results['items']:
                if i['condition']!='N':continue
                for r in i['cells'][criterion][provider]['readings']:
                    f=r['natural_goal_turn_flags'];c['returned']+=1;c[f['record_state']]+=1
            goal.append({'criterion':criterion,'provider':provider,'states':dict(c)})
            for cond in ['G','U','F','X']:
                c=Counter()
                for i in results['items']:
                    if i['condition']!=cond:continue
                    for r in i['cells'][criterion][provider]['readings']:
                        if r['score']==4:
                            c['global4']+=1;c['global4_with_target_issue']+=bool(r['target_flags']['target_problem_explicit'])
                        c['returned']+=1
                controls.append({'criterion':criterion,'provider':provider,'condition':cond,'counts':dict(c)})
    dump(HERE/'operational-diagnostics.json',{'status':'postrun_diagnostics_notprimary_parser_repair',
      'cells':out,'natural_P08_common_field_states':goal,'control_global4_and_target_issue':controls,
      'interpretation':'CCFrole requests profile/communication grounding but reference vocabulary is open-ended (등); frozen parser only accepts fact IDs,turn IDs,authored_context. Treat unmatched real input paths as interface incompatibility,not fabricated patient facts. No alias normalization or malformed JSON repair applied.'})
    print('Saved post-run diagnostics without altering primary scores')

if __name__=='__main__':main()
