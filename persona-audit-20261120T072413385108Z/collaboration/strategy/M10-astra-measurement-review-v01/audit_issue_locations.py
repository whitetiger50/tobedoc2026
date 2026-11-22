"""Location of already reported observations, not a new quality/error rating."""
from pathlib import Path
from collections import Counter
import json,re,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def read(p):return json.loads(p.read_text())
rows=[];sources={}
for stage in [8,9]:
 base=next((ROOT/'development').glob(f'speech-m{stage}-*'));key=read(base/'review-key-private.json');sources[str((base/'review-key-private.json').relative_to(ROOT))]=hashlib.sha256((base/'review-key-private.json').read_bytes()).hexdigest()
 for judge in ['codex','claude']:
  p=base/'reviews'/judge/'validated.json';sources[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
  for r in read(p)['reviews']:
   observed=[]
   for i in r['issues']:observed.append(('issues',i))
   for field in ['grounding_review','avoidance_review','style_review']:
    for i in r.get(field,{}).get('findings',[]):observed.append((field,i))
   for channel,i in observed:
    turn=i['patient_turn_id'];description=i.get('issue',i.get('explanation',''))
    rows.append({'stage':stage,'judge':judge,'item_id':key[r['blind_id']]['item_id'],'turn':turn,'location':'prompted_P05_P07' if turn in ['P05','P06','P07'] else 'neutral_P01_P04_P08','channel':channel,'quote':i['quote'],'description':description,'explicit_other_turn_references':sorted(set(re.findall(r'(?<![A-Za-z0-9])P0[1-8](?![A-Za-z0-9])',description))-{turn})})
summary=[]
for stage in [8,9]:
 for judge in ['codex','claude']:
  selected=[r for r in rows if r['stage']==stage and r['judge']==judge]
  # One review-turn can contain several distinct concerns; this is a location
  # grouping to avoid counting channel duplicates, not a deduplicated error rate.
  units={(r['item_id'],r['turn'],r['location']) for r in selected}
  summary.append({'stage':stage,'judge':judge,'rated_dialogues':18,'reported_records_all_channels':len(selected),'reported_records_by_channel':dict(Counter(r['channel'] for r in selected)),'review_turn_locations':dict(Counter(u[2] for u in units)),'review_turn_locations_total':len(units)})
out={'kind':'locations_of_existing_reported_observations_not_new_clinical_coding','summary':summary,'records':rows,'limits':'36dialogues×2judges; issues limited0-2perreview, grounding/style tasks differ bystage, missing reported issues do not imply no problem. Location is not causal attribution. Prefix/full or probe/nonprobe effects cannot be inferred. Channel records may describe same event. Review-turn grouping merges multiple concerns within one turn and is not an error rate. Explicit turn-reference regex misses implicit links. No most-issues threshold or new grading.','source_sha256':sources}
(HERE/'issue-location-audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
print('NONPROBE RECORDS')
for r in rows:
 if r['location']=='neutral_P01_P04_P08':print(json.dumps(r,ensure_ascii=False))
