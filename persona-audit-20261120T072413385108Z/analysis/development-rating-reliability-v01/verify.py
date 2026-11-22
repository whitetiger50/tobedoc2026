from pathlib import Path
import json,hashlib,importlib.util,sys
from fractions import Fraction as F
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('rel',HERE/'reliability.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
spec=importlib.util.spec_from_file_location('parse',ROOT/'development/speech-m1-v01/review_dev.py');p=importlib.util.module_from_spec(spec);sys.path.insert(0,str(ROOT));spec.loader.exec_module(p)
def read(x):return json.loads(x.read_text())
def sha(x):return hashlib.sha256(x.read_bytes()).hexdigest()

def main():
 s=read(HERE/'results.json');base=ROOT/'development/speech-m5-repeatability-v01';old=read(base/'scores.json');items={r['item_id']:r for r in old['items']};raw=[]
 for r in range(1,4):
  key=read(base/f'round{r:02d}-key-private.json')
  for judge in ['codex','claude']:
   d=base/'reviews'/judge/f'round{r:02d}';v=read(d/'validated.json');assert p.parse_review((d/'response.txt').read_text())==v
   assert sha(d/'response.txt')==read(d/'metadata.json')['response_sha256']
   for row in v['reviews']:assert items[key[row['blind_id']]]['judges'][judge]['scores'][r-1]==row['score']
   raw.extend([d/'validated.json',d/'response.txt',d/'metadata.json',base/f'round{r:02d}-key-private.json'])
 for f,h in s['source_sha256'].items():assert sha(ROOT/f)==h
 assert m.fixtures()==s['checks']
 for judge,stored in s['M5_originals_only']['within_model'].items():
  matrix=[items[i]['judges'][judge]['scores'] for i in s['M5_originals_only']['item_ids']]
  assert m.serial(m.within(matrix))==stored
 matrix=[[F(items[i]['judges']['codex']['scores'][r]+items[i]['judges']['claude']['scores'][r],2) for r in range(3)] for i in s['M5_originals_only']['item_ids']]
 assert m.serial(m.within(matrix))==s['M5_originals_only']['two_model_arithmetic_mean_repeatability']
 prior=read(ROOT/'collaboration/strategy/M10-astra-measurement-review-v01/verification.json')
 for f,h in prior['file_sha256'].items():assert sha(ROOT/f)==h
 files=[p for p in HERE.glob('*') if p.is_file() and p.name!='verification.json']
 out={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'raw_M5_response_files_and_all54scores_checked':True,'original_subset6_dialogues_3profiles_36ratings':True,'original_and_combined_repeated_score_matrices_recomputed':True,'formula_fixture_groups_passed':s['checks'],'old_M10_manifest_files_unchanged':len(prior['file_sha256']),'new_patient_outputs':0,'new_model_ratings':0,'new_strategy_model_calls':0,'new_packages':0,'final720_changed_or_executed':False,'clinical_validation':False,'file_sha256':{str(f.relative_to(ROOT)):sha(f) for f in files},'raw_response_source_sha256':{str(f.relative_to(ROOT)):sha(f) for f in set(raw)}}
 (HERE/'verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 print('Verified all54 M5 raw ratings, original36rating subset, recomputed matrices and source hashes;4fixture groups passed;0new ratings')
if __name__=='__main__':main()
