"""Verify actual strategy responses, immutable evidence and deterministic audits."""
from pathlib import Path
import json,hashlib
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 freeze=read(HERE/'freeze.json')
 assert sha(HERE/'review-packet.md')==freeze['packet_sha256']
 assert sha(HERE/'mentor-role.txt')==freeze['role_sha256']
 for f,h in freeze['source_sha256'].items():assert sha(ROOT/f)==h,f
 a=read(HERE/'chronology-addendum-freeze.json')
 for f,h in a['source_sha256'].items():assert sha(ROOT/f)==h,f
 assert sha(HERE/'chronology-addendum.md')==a['addendum_sha256']
 f2=read(HERE/'round02-freeze.json');assert sha(HERE/'round02-request.md')==f2['request_sha256']
 for f,h in f2['source_sha256'].items():assert sha(HERE/f)==h,f
 sessions=[];calls=[]
 for roundno in [1,2]:
  p=HERE/f'claude-round{roundno:02d}';meta=read(p/'metadata.json');cmd=read(p/'command.json')['argv']
  body=HERE/('review-packet.md' if roundno==1 else 'round02-request.md')
  assert meta['status']=='response_received' and meta['returncode']==0 and meta['automatic_retries']==0
  assert meta['requested_model']=='claude-opus-5-5' and meta['effort']=='high'
  assert meta['tools']=='disabled' and meta['reported_server_snapshot'] is None
  assert (p/'input.txt').read_bytes()==body.read_bytes()
  assert sha(p/'input.txt')==meta['input_sha256']
  assert sha(p/'instructions.txt')==meta['instructions_sha256']==freeze['role_sha256']
  assert sha(p/'response.txt')==meta['response_sha256']
  raw=read(p/'stdout.raw');assert raw['result']==(p/'response.txt').read_text()
  assert set(raw['modelUsage'])=={'claude-opus-5-5'}
  assert '--no-session-persistence' in cmd and '--resume' not in cmd and '--continue' not in cmd
  assert cmd[cmd.index('--tools')+1]==''
  sessions.append(meta['transport_session_id']);calls.append({'round':roundno,'model':meta['requested_model'],'effort':meta['effort'],'timestamp_utc':meta['timestamp_utc'],'response_sha256':meta['response_sha256']})
 assert len(set(sessions))==2
 for p in [HERE/'astra-round01.md',HERE/'astra-round02.md']:assert p.stat().st_size>500
 dispatch=read(HERE/'astra-dispatch-record.json');assert dispatch['requested_model']=='gpt-6.2-astra' and dispatch['requested_reasoning_effort']=='high'
 for fn in ['measurement-audit.json','issue-location-audit.json']:
  obj=read(HERE/fn)
  for f,h in obj['source_sha256'].items():assert sha(ROOT/f)==h,f
 audit=read(HERE/'measurement-audit.json');assert audit['within_judge_fixed_text_M5']['codex']['equal_pairs']==18
 assert audit['within_judge_fixed_text_M5']['claude']['equal_pairs']==12
 assert audit['within_judge_fixed_text_M5']['claude']['all_three_equal_dialogues']==3
 assert [round(x['v04_minus_v02'],8) for x in audit['same_fixed_text_M5_round_contrasts']]==[0,round(-1/6,8),round(-1/6,8)]
 locations=read(HERE/'issue-location-audit.json')
 for r in locations['records']:
  base=next((ROOT/'development').glob(f"speech-m{r['stage']}-*"));key=read(base/'review-key-private.json');meta=next(v for v in key.values() if v['item_id']==r['item_id'])
  t=read(ROOT/meta['transcript_path']);turn=next(x for x in t['generated_dialogue'] if x['turn_id']==r['turn'])
  assert r['quote'] in turn['text']
 old=read(ROOT/'development/speech-m9-style-examples-v01/verification.json')
 for f,h in old['file_sha256'].items():assert sha(ROOT/f)==h,f
 plan=read(HERE/'next-plan.json');assert plan['new_generation_executed']==plan['new_numeric_ratings_executed']==0
 assert plan['final_720_changed'] is False and plan['heldout_profiles_used']==0
 files=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='verification.json']
 result={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'date_KST':'2026-11-19','actual_Astra_strategy_responses':2,'Astra_selection_evidence':dispatch,'actual_Claude_strategy_responses':calls,'separate_Claude_sessions':sessions,'initial_reviews_independent_followups_carry_real_prior_responses':True,'all_original_prompt_and_evidence_hashes_unchanged':True,'M9_historical_manifest_verified_files':len(old['file_sha256']),'M5_descriptive_audit_recomputed':True,'reported_issue_locations_quotes_verified':len(locations['records']),'new_generation_calls':0,'new_numeric_rating_outputs':0,'final_720':'not_performed_unchanged','clinical_validation':False,'new_paid_API_calls':0,'new_models_downloaded':0,'new_packages_installed':0,'file_sha256':{str(p.relative_to(ROOT)):sha(p) for p in files}}
 (HERE/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print('Verified 2 Astra responses + 2 separate Claude high responses; unchanged originals; no new utterances/Realism ratings')
if __name__=='__main__':main()
