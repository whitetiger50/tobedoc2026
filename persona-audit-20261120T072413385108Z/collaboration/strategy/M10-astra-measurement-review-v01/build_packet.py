from pathlib import Path
import json,hashlib,statistics
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def read(p):return json.loads(p.read_text())
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
paths=[]
def take(rel):
 p=ROOT/rel;paths.append(p);return p.read_text()
m5=read(ROOT/'development/speech-m5-repeatability-v01/scores.json');paths.append(ROOT/'development/speech-m5-repeatability-v01/scores.json')
originals=[r for r in m5['items'] if r['kind']=='original'];rounds=[]
for n in range(3):
 means={v:statistics.mean(r['judges'][j]['scores'][n] for r in originals if r['condition']==v for j in ['codex','claude']) for v in ['v02','v04']}
 rounds.append({'round':n+1,'same_fixed_dialogues_condition_means':means,'v04_minus_v02':means['v04']-means['v02']})
repeat={'same_text_original_item_scores':originals,'original_only_repeatability':m5['repeatability_originals_only'],'round_condition_contrasts':rounds,'error_sensitivity':m5['error_sensitivity'],'limits':m5['limits'],'warning':'Pair counts share items/rounds, not 18 independent observations. Six originals from3reusedprofiles; all GPT originals4. No empirical noise floor/SEM/CI established. Controls test coarse family reference mismatches, not subtle realism validity. Round2 Claude references another packet ID.'}
dump(HERE/'existing-repeatability-audit.json',repeat)
ledger=[]
for n in range(3,10):
 for d in sorted((ROOT/'development').glob(f'speech-m{n}-*')):
  p=d/'scores.json'
  if not p.exists():continue
  x=read(p);paths.append(p)
  ledger.append({'stage':n,'source':str(p.relative_to(ROOT)),**{k:v for k,v in x.items() if k in ['condition_means','judge_specific_means','judge_condition_means','original_version_means','v04_minus_v02','v05_minus_v02','delta_v03_minus_v02','delta_v04_minus_v02','examples_minus_none','score_frequencies','dialogues','ratings','rating_outputs','style_summary','selection','independent_case_clusters','limits']}})
dump(HERE/'experiment-ledger.json',ledger)
parts=['''# M10 independent strategy/measurement review — 2026-11-19 KST
User explicitly requests Astra review of prompts, experiments and evaluation plus separate Claude direction discussion. Main question: tiny unstable differences raise rating consistency concerns. Do not generate/score patients, rewrite prompts, call APIs or browse entire repository. Review supplied primary evidence and propose a bounded next plan. Do not assume rawv02 optimal or recommend 720 ratings merely to make small differences significant.
Fixed: synthetic only, no realpatient/specialist validation; Dec2026 poster; no new model training; development GPT6.1SolHigh + Opus5.5 each1 per packet except user-authorized M5 each3. Arithmeticmean retained; final720 deferred, 12heldout profiles unused. Astra is developer strategy reviewer, not added numeric judge. Runtime historical defaultv04 differs from explicitly selected provisionalTv02. Claude directionHigh contexts separate from utterance judgingMedium. Existing source audit obtained actual E3authorcode, E4appendixtemplates, E6roleprompt; E1fullpatientprompt unavailable; none supplies validated full Korean schizophrenia template. Do not call all prompts unavailable. Prior T outputs already seen; only future B/T criteria can be prospectively frozen.
Review questions:
1. What do repeatability, interjudge disagreement, ceiling/floor, sensitivity and construct validity each show/not show? Avoid invented error margin, clinical significance threshold, independence or equivalence. Is selected prompt ranking stable enough to guide development?
2. Which changes accidentally confound prompt, question, case, sampling, review task/batch, author readiness or source availability? Judge pure iteration limitations and the v06 sharedscaffold comparison honestly.
3. Is v02 simplicity choice justified provisionally without implying winner? Critique categorical style-zero vs repeated score3 and merged factual/disclosure findings.
4. Propose ONE smallest next measurement diagnostic only if existing evidence insufficient, with fixed-text reuse, repeat/condition structure, sample unit, masked presentation, honest endpoint and stop/go rule. Separate proposed from authorized/executed. Do not claim pairwise preferences or more repeats fix validity. Do not change user fixed judges/aggregate without explaining why and keeping existing ratings.
5. Prioritize baselineB source/input audit vs newgeneration or rating. Protect final unused cases. Give concrete stop/go decisions and state what requires external clinical anchors.
Required output Korean: central diagnosis; supported evidence with file/IDs; criticism of Codex/Claude decisions; competing explanations; bounded next plan; unresolved disagreements. No new Realism scores. Distinguish model critique from validated scientific evidence.
''']
for name,content in [('EXPERIMENT LEDGER',ledger),('FIXED TEXT REPEATABILITY',repeat)]:parts+=['\n## '+name+'\n',json.dumps(content,ensure_ascii=False,separators=(',',':'))]
for v in ['01','02','03','04','05','06']:
 name='speech_module/patient_v01.txt' if v=='01' else f'speech_module/patient_v{v}.txt'
 if not (ROOT/name).exists() and v=='01':name='speech_module/patient.txt'
 if (ROOT/name).exists():parts+=['\n## PROMPT '+name+'\n',take(name)]
for name in ['development/speech-m9-style-examples-v01/reference-examples.json','development/speech-m9-style-examples-v01/methods.md','development/speech-m9-style-examples-v01/review-role.txt','development/speech-m9-style-examples-v01/interpretation.md','collaboration/strategy/M9-direction-review-v01/decision.md']:
 parts+=['\n## '+name+'\n',take(name)]
p=ROOT/'development/speech-m5-repeatability-v01/round01-packet.json';paths.append(p)
parts+=['\n## M5 ACTUAL FIXED ORIGINALS AND ERROR CONTROLS, PROFILES AND ANCHORS\n',json.dumps(read(p),ensure_ascii=False,separators=(',',':'))]
p9=ROOT/'development/speech-m9-style-examples-v01';key=read(p9/'review-key-private.json');paths.append(p9/'review-key-private.json')
chosen=['DEV-M0-01-rep03-examples','DEV-M0-02-rep01-examples','DEV-M0-02-rep03-none','DEV-M0-03-rep01-none','DEV-M0-03-rep01-examples']
for ident in chosen:
 k=next(k for k,v in key.items() if v['item_id']==ident);path=ROOT/key[k]['transcript_path'];paths.append(path)
 item={'item_id':ident,'generated_dialogue':read(path)['generated_dialogue'],'actual_reviews':{}}
 for judge in ['codex','claude']:
  p=p9/'reviews'/judge/'validated.json';paths.append(p)
  row=next(r for r in read(p)['reviews'] if r['blind_id']==k);item['actual_reviews'][judge]={field:row[field] for field in ['score','reason','uncertainty','issues','grounding_review','style_review']}
 parts+=['\n## PURPOSE-SELECTED ACTUAL M9 EXAMPLE (NOT REPRESENTATIVE SAMPLING)\n',json.dumps(item,ensure_ascii=False,separators=(',',':'))]
(HERE/'review-packet.md').write_text('\n'.join(parts))
role='당신은 조현병 환자 발화기 개발의 독립적인 연구 설계·측정 멘토다. 제공된 근거만 비판적으로 검토하고 한국어로 답하라. 환자 발화 평정이나 임상 검증을 수행하지 않는다. 전체 저장소나 전체 대화 기록을 읽지 말고 제공된 작은 근거 묶음의 범위를 지킨다. 수치 계산은 제공된 Python 집계를 대조하고 확인되지 않은 수치·출처·전문가 평가를 만들지 않는다. Codex의 제안과 기존 Claude의 판단을 무조건 동의하지 않는다.'
(HERE/'mentor-role.txt').write_text(role)
dump(HERE/'freeze.json',{'timestamp_utc':datetime.now(timezone.utc).isoformat(),'user_date':'2026-11-19 KST','purpose':'Astra independent review plus separate Claude measurement/direction exchange','requested_astra_model':'gpt-6.2-astra','requested_astra_effort':'high','claude_model':'claude-opus-5-5','claude_effort':'high','new_patient_generation':0,'new_numeric_ratings':0,'packet_bytes':(HERE/'review-packet.md').stat().st_size,'packet_sha256':sha(HERE/'review-packet.md'),'role_sha256':sha(HERE/'mentor-role.txt'),'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in set(paths)}})
print('Prepared bounded review packet bytes', (HERE/'review-packet.md').stat().st_size,'sources',len(set(paths)))
