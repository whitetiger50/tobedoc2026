"""Author text extraction helper. Does not grade quality or overwrite mechanical metrics."""
import argparse,hashlib,re
from datetime import datetime,timezone
from common import HERE,read,dump,sha,quote_location

def prepare():
    source=read(HERE/'author-extraction-input.json');catalogue={};rows=[]
    for row in source['rows']:
        claims=[]
        for c in row['common_claims']:
            text=c.get('reason')or''
            key=hashlib.sha256(text.encode()).hexdigest()[:12]
            catalogue.setdefault(key,{'reason_id':key,'text':text})
            claims.append(dict(c,reason_id=key))
        rows.append(dict(row,common_claims=claims))
    ordered=sorted(catalogue.values(),key=lambda x:x['reason_id'])
    dump(HERE/'author-reason-catalogue.json',{'created_utc':datetime.now(timezone.utc).isoformat(),
      'source_sha256':sha(HERE/'author-extraction-input.json'),'same_exact_reason_text_interned_without_semantic_filter':True,
      'criteria_provider_scores_withheld':True,'rows':ordered})
    dump(HERE/'author-claim-view.json',{'rows':rows})
    print('Prepared full common reason catalogue:',len(ordered),'unique exact reason texts from',len(rows),'masked records. No score aggregate printed.')

def show(start,count):
    rows=read(HERE/'author-reason-catalogue.json')['rows']
    for i,r in enumerate(rows[start:start+count],start):
        text=re.sub(r'(?<![\w])[1-4](?:\.0)?\s*점','[등급언급]',r['text'])
        text=re.sub(r'(?<!\d)[1-4]\s*/\s*4','[등급경계]',text)
        text=re.sub(r'CCF(?:-R1)?|Realism','[기준명]',text,flags=re.I)
        print(str(i)+' '+r['reason_id']+' '+text)
    print('Displayed',start,'through',min(start+count,len(rows))-1,'of',len(rows),'unique exact texts')

def merge():
    annotations=read(HERE/'author-reason-annotations.json')
    catalogue=read(HERE/'author-reason-catalogue.json')
    mapping={r['reason_id']:r for r in annotations['rows']}
    assert set(mapping)=={r['reason_id']for r in catalogue['rows']}
    assert annotations['all_catalogue_texts_reviewed_before_aggregate_score_view']
    out=[]
    for row in read(HERE/'author-claim-view.json')['rows']:
        turns={t['turn_id']:t['text']for t in row['dialogue_excerpt'] if t['speaker']=='patient'}
        criticized=[];other=[];uncited=[];general_allowances=[];ambiguous=[]
        for c in row['common_claims']:
            a=mapping[c['reason_id']];stance=a['repetition_stance']
            if stance in ['allow','mixed']:general_allowances.append({'field':c['field'],'reason_id':c['reason_id'],'reason':c['reason']})
            if not c['adverse']:continue
            ev=[]
            for e in c['evidence']:
                tid=e.get('patient_turn_id');q=e.get('quote')
                if e.get('valid_quote') and tid in row['target_ranges']:
                    location=quote_location(q,turns[tid],row['target_ranges'][tid])
                    if location['target']:ev.append(e)
                    elif location['ambiguous']:ambiguous.append({'field':c['field'],'reason_id':c['reason_id'],'evidence':e})
            if ev:
                record={'field':c['field'],'reason_id':c['reason_id'],'reason':c['reason'],'evidence':ev,
                        'issue_family':a['issue_family'],'link_caution':a.get('link_caution','')}
                if a.get('link_caution'):ambiguous.append(record)
                elif stance in ['critique','mixed']:criticized.append(record)
                else:other.append(record)
            elif stance in ['critique','mixed'] and any(tid in (c['reason']or'') for tid in row['target_ranges']):
                uncited.append({'field':c['field'],'reason_id':c['reason_id'],'reason':c['reason']})
        out.append({'audit_id':row['audit_id'],'author_repeat_critique_at_quoted_target':bool(criticized),
          'other_adverse_target_claim':bool(other),'uncited_target_repeat_claim':bool(uncited),
          'repeat_claims':criticized,'other_claims':other,'uncited_claims':uncited,'ambiguous_claims':ambiguous,
          'general_allowance_not_automatically_target_specific':general_allowances})
    dump(HERE/'author-claim-extraction.json',{'timestamp_utc':datetime.now(timezone.utc).isoformat(),
      'status':'Codexauthor_claim_extraction_notindependent_orclinical_rescoring',
      'catalogue_sha256':sha(HERE/'author-reason-catalogue.json'),'annotations_sha256':sha(HERE/'author-reason-annotations.json'),
      'mechanical_metrics_not_overwritten':True,'rows':out})
    print('Author claim extraction saved for',len(out),'masked records; no score aggregate printed')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','show','merge']);p.add_argument('--start',type=int,default=0);p.add_argument('--count',type=int,default=70);a=p.parse_args()
    if a.action=='prepare':prepare()
    elif a.action=='show':show(a.start,a.count)
    else:merge()
