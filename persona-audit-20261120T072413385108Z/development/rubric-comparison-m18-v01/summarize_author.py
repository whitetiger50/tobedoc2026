"""Post-extraction descriptive join; no scores are changed or model calls made."""
from collections import Counter
from common import HERE, read, dump, sha

def main():
    annotations=read(HERE/'author-reason-annotations.json')
    assert annotations['all_catalogue_texts_reviewed_before_aggregate_score_view']
    extracted={r['audit_id']:r for r in read(HERE/'author-claim-extraction.json')['rows']}
    results=read(HERE/'results.json'); groups=[]
    for group in results['groups']:
        selected=[i for i in results['items'] if i['item_id'] in group['item_ids']]
        eligible=[i for i in selected if i['prejudge_target_eligible'] and (i['condition']=='N' or i['manipulation_realized'])]
        counts=Counter(); details=[]
        for item in eligible:
            for record in item['cells'][group['criterion']][group['provider']]['readings']:
                if record is None: continue
                row=extracted[record['author_audit_id']]
                counts['returned']+=1
                for key in ['author_repeat_critique_at_quoted_target','other_adverse_target_claim','uncited_target_repeat_claim']:
                    counts[key]+=bool(row[key])
                counts['ambiguous_claim_record']+=bool(row['ambiguous_claims'])
                counts['general_allowance_record_not_target_specific']+=bool(row['general_allowance_not_automatically_target_specific'])
                counts['common_usable']+=record['common_output_usable']
                details.append({'item_id':item['item_id'],'repetition':record['repetition'],**row})
        groups.append({'criterion':group['criterion'],'provider':group['provider'],'stratum':group['stratum'],
          'eligible_texts':len(eligible),'counts':dict(counts),'details':details})
    dump(HERE/'author-extraction-summary.json',{'status':'author_claim_extraction_notclinical_gold_or_independent_rescoring',
      'source_sha256':sha(HERE/'author-claim-extraction.json'),'overlapping_categories_not_exclusive':True,'groups':groups})
    print('Saved author extraction descriptive join; no model calls or score changes')

if __name__=='__main__':main()
