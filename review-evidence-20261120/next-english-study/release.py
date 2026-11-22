"""Construct and validate the offline public bundle from completed study outputs."""
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

from reproduce import ARMS, CASES, READERS, digest, load, require, scopes

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
PATIENTHUB = PROJECT/'persona-audit-20261120T072413385108Z/evidence/snapshots/psyche-roleplay-v01/patienthub'
COMMIT = '54d5c8761a9055a1e86d153715607ef9fa26358a'
ARCHIVE = '연구_재현자료.zip'
GUIDE = """# 영문 정신과 외래 합성 면담 재현 자료

압축을 빈 폴더에 푼 뒤 그 폴더에서 `python3 -I -B reproduce.py`를 실행하세요. Python 3.8 이상의 표준 라이브러리만 사용합니다. 먼저 SHA-256 목록과 파일 구성을 검사한 다음 사례·판독자별 평점 대비, 일곱 행동 범주의 턴별 분모와 집계, 근거 인용, 두 판독자의 양성 일치를 대조합니다.

## 연구 대상과 파일

- `cases.json`에 독립적으로 작성한 가상 성인 외래 사례 8개의 프로필·면담 질문·평가 기회가 들어 있습니다. 표현 유형별 2사례입니다. `interviews.json`은 같은 사례에 세 조건을 적용한 24개 면담과 최초 답변 288개를 사례와 조건별로 보관합니다.
- `prompts/`에는 실제 사용한 시스템 지시문이 있습니다. B는 PatientHub의 PSYCHE식 영어 템플릿입니다. T1은 팀의 이전 후보, T2는 이번에 동결한 후보입니다. B는 역할별 대화 이력을 사용했고 T1과 T2는 동일한 JSON 입력 형식으로 각자의 이전 문답을 받았습니다. T2와 B의 차이에는 입력 표현 방식도 포함됩니다. 파일별 출처와 이용 조건은 `sources.json`에 있습니다.
- `first_scores.json`에서 판독자·가상 사례·조건마다 두 회차의 첫 제출 평점과 근거를 확인할 수 있습니다. GPT와 Opus가 면담과 프로필을 보고 각각 독립적으로 채점한 외래 적응 PATIENTSIM Realism_w_Profile(1–4점)입니다. 두 회차 모두 더 높거나 같거나 더 낮으면 각각 승·동률·패이며, 방향이 달라지면 불안정, 점수가 하나라도 결측이면 결측입니다. 독립 비교 단위는 사례 8개입니다.
- `semantic_turns.json`은 판독자별 평가 대상 턴과 양성·불확실·음성·결측 판정을 보존합니다. 양성·불확실 판정에는 가상 면담의 발췌와 판정 근거가 있습니다. 재설명 판정에는 앞선 답의 인용도 포함합니다. `semantic_guide.json`에 일곱 범주의 영어 정의가 있습니다. 면담 턴은 1부터 셉니다.
- `aggregate/`에는 전체 면담 평점, 행동 판독, 합성 오류 대조, 어휘 반복, 연구 후보 채택 판단 및 DAIS-C 집계가 있습니다. 어휘 반복은 동일한 단어열이 다시 나온 횟수를, 불필요한 재설명은 대화에서 이미 전달한 뜻을 새 목적 없이 반복한 횟수를 셉니다.
- `aggregate/dais_clinical.json`은 DAIS-C의 두 시작 질문 계열(Q2·Q3)에 해당하는 임상군의 집계입니다. `aggregate/dais_comparison.json`이 포함되어 있으면 임상군 전체와 비임상 비교군의 시작 질문 계열별 분모를 확인할 수 있습니다. 실제 참여자에 관한 데이터는 공개 가능한 집단 집계만 포함하므로 이 번들의 재계산 대상은 합성 자료의 평가입니다. 실제 임상 자료의 출처는 `sources.json`을 참조하세요.

## 별도 탐색 평가

`reconstruction/DESIGN.ko.md`은 주 연구 평점을 본 뒤 추가한 복원 평가의 사전 규칙입니다. `targets.json`은 가상 사례당 두 문항의 정답·대조 문장, 원문 근거 및 면담 기회를 제공합니다. `first_decisions.json`에서 질문만 읽은 대조와 전체 문답을 읽은 B·T1·T2 조건의 최초 판정을 확인할 수 있습니다. `results.json`의 각 판독자·조건 분모는 16문항(8사례 × 2영역)이며 영역별 분모는 8개입니다. 질문만 읽고 맞힌 문항을 제외한 결과의 분모는 판독자별로 달라질 수 있습니다. 재계산 시 문항별 선택을 정답·대조와 연결하고 조건별 건수와 분모를 검산합니다. `reader_concordance.json`에서 두 판독자가 함께 맞힌 문항, 한 명만 맞힌 문항, 둘 다 맞히지 못한 문항, 한쪽 이상 판정이 유효하지 않은 문항을 구분합니다.

## 외부 과제의 발화 길이 비교

`external-task/DESIGN.ko.md`와 `external-task/release.json`은 신데렐라 이야기와 세탁 절차 설명을 요청한 별도 탐색 실험입니다. 가상 사례 8개에 4개 발화 조건과 2개 과제를 적용해 받은 첫 답변 64개를 보관합니다. 임상군·비임상군의 참조값은 Pugh 등(2024) 표 2의 집단 요약값입니다. 검산기는 합성 답변에서 영어 철자 단어 수와 공백 기준 단어 수를 세고, 사례·조건·과제별 분모 및 평균을 확인합니다. 주 연구의 현실성 평점과 채택 기준은 주 연구 파일에 담겨 있습니다.

여기서 재현하는 것은 고정된 답변과 판독표를 사용한 분석입니다. 모델을 다시 호출하는 실험과 임상가의 타당도 평가는 별도의 검증이 필요합니다.
"""
URL = 'https://github.com/Sahandfer/PatientHub/blob/'+COMMIT+'/'

def convert(x):
    return (json.dumps(x,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n').encode('utf-8')

def checked(path, expected):
    raw = path.read_bytes()
    require(digest(raw)==expected, 'Frozen file changed: '+path.name)
    return raw

def project_prompts(files):
    freeze = load(HERE/'generation-freeze.json')
    hashes = freeze['condition_system_hashes']
    paths = {'B':PROJECT/'tobedoc2026/config/main-freeze-v01/system-template.txt',
             'T1':HERE.parent/'first-turn-revision-proposal/proposed-prompt.txt', 'T2':HERE/'T2.txt'}
    for arm, path in paths.items():
        files['prompts/'+arm+'.txt'] = checked(path,hashes[arm])
    lic = checked(PATIENTHUB/'LICENSE','59fd1743b93a5dd87269b7e1f8346c3a221a5743e19a039d95f2ac68debf76dd')
    files['prompts/LICENSE-PatientHub.txt'] = lic
    yaml = checked(PATIENTHUB/'data/prompts/client/psyche.yaml','cf83a3e5079f3e7b0db2b8bd084d16ce569d360b52c37140471e41996e3dc107')
    lines = yaml.decode().splitlines(keepends=True)
    require(lines[0].strip()=='en:' and lines[1].strip()=='system_prompt: |','Upstream YAML layout')
    body = []
    for line in lines[2:]:
        if line.strip() and not line.startswith('    '):
            break
        body.append(line[4:] if line.startswith('    ') else line)
    require((''.join(body).rstrip('\n')+'\n').encode()==files['prompts/B.txt'], 'Upstream B attribution mismatch')
    files['sources.json'] = convert({
        'B':{'name':'PatientHub PSYCHE-style client, English system_prompt', 'attribution':'Copyright (c) 2026 Sahand Sabour',
             'commit':COMMIT, 'source':URL+'data/prompts/client/psyche.yaml', 'implementation':URL+'patienthub/clients/psyche.py',
             'license':'MIT; upstream license reproduced at prompts/LICENSE-PatientHub.txt','sha256':hashes['B']},
        'T1':{'attribution':'TobeDoctor study team', 'origin':'Team v0.2 English-output variant with a turn-yielding revision',
              'license':'No separate open-source license specified by the study team.', 'sha256':hashes['T1']},
        'T2':{'attribution':'TobeDoctor study team','origin':'Frozen follow-up English system prompt',
              'license':'No separate open-source license specified by the study team.','sha256':hashes['T2']},
        'primary_scale':{'name':'PATIENTSIM Realism_w_Profile, psychiatric outpatient adaptation',
            'source':'https://proceedings.neurips.cc/paper_files/paper/2025/hash/24945e3bdc7b3f4b2e64b9979a16f38e-Abstract-Datasets_and_Benchmarks_Track.html',
            'source_scale_file_sha256':freeze['primary_scale_sha256']},
        'DAIS-C':{'citation':'Delgaram-Nejad, Archer, Chatzidamianos, Bartha and Robinson (2023). Discussing Abstract Ideas in Schizophrenia Corpus, 2017–2023.',
            'source':'https://reshare.ukdataservice.ac.uk/855021/', 'publication':'https://doi.org/10.1016/j.acorp.2023.100069',
            'source_data_license':'CC BY-SA 4.0','license_url':'https://creativecommons.org/licenses/by-sa/4.0/',
            'processing':'Participant-aggregate windows and recurrence statistics calculated by the study team.'},
        'study':{'generator':freeze['model'],'effort':freeze['effort'],'readers':['GPT-6.1 Sol (high)','Claude Opus 5.5 (medium)'],
                 'generation_case_sha256':freeze['cases_sha256'],'turns_per_interview':12}})
    return freeze

def primary_and_semantic(files, cases):
    keys = load(HERE/'private/key.json')
    by_cell = {(k['case'],k['arm']):k['id'] for k in keys}
    require(len(keys)==len(set(by_cell.values()))==24 and set(by_cell)=={(c,a) for c in CASES for a in ARMS},'Synthetic key coverage')
    frozen = load(HERE/'blind-freeze.json')['hashes']
    require(set(by_cell.values())==set(frozen), 'Frozen blind inventory')
    interviews = {c:{} for c in CASES}
    primary = {r:{c:{} for c in CASES} for r in READERS}
    semantic = {r:{c:{} for c in CASES} for r in READERS}
    for c in CASES:
        op = cases[c]['opportunities']
        for a in ARMS:
            uid = by_cell[c,a]
            require(re.fullmatch(r'I[0-9a-f]{20}',uid),'Blind label format')
            doc = json.loads(checked(HERE/'blind'/(uid+'.json'),frozen[uid]))
            require(doc['profile']==cases[c]['profile'],'Incorrect disclosed arm/case mapping')
            interviews[c][a] = [{k:t[k] for k in ('question','answer')} for t in doc['dialogue']]
            for r in READERS:
                records = primary[r][c][a] = []
                for n in (1,2):
                    p = load(HERE/'ratings'/r/('r%d'%n)/uid/'accepted.json')
                    require((p['round'],p['id'],p['reader'])==(n,uid,r),'Primary record mapping')
                    row = {'round':n,'status':p['status'],'score':p['score']}
                    if row['status']=='valid':
                        row['rationale']=p['rationale']
                        row['evidence']=[{k:e[k] for k in ('turn','quote')} for e in p['evidence']]
                    records.append(row)
                dest = semantic[r][c][a] = {}
                path = HERE/'semantic'/r/uid/'accepted.json'
                rec = load(path) if path.exists() else None
                if rec:
                    require((rec['id'],rec['reader'])==(uid,r),'Semantic record mapping')
                for metric, turns in scopes(op).items():
                    if not rec:
                        dest[metric] = {'labels':{str(t):'missing' for t in turns},'evidence':{}}
                        continue
                    block = rec['metrics'][metric]
                    evidence = {}
                    for t,e in block['events'].items():
                        require(block['labels'][t]==e['label'],'Semantic label mismatch')
                        ks = ('quote','reason','earlier_turn','earlier_quote') if metric=='avoidable_recap' else ('quote','reason')
                        evidence[t]={k:e['evidence'][k] for k in ks}
                    dest[metric] = {'labels':block['labels'],'evidence':evidence}
    for name, data in [('interviews',interviews),('first_scores',primary),('semantic_turns',semantic)]:
        files[name+'.json']=convert(data)

# Only group-level numeric summary fields may cross the clinical data boundary.
STAT_KEYS = ('target_turns','eligible_turns','repeat_turns','eligible_people','people_with_recurrence',
    'current_turn_with_invalid_bounds','person_opportunities_median_range','person_recurrence_counts_median_range',
    'median_usable_tokens_in_clean_target','person_recurrence_fraction_median_range_eligible',
    'participants_without_observable_window','participants_eligible_without_recurrence','anchored_without_observable_window')
STAT_GROUPS = {'exclusion_counts':('no_candidate_in_target','role_or_transcription','no_candidate_in_previous','elicitation_filter'),
    'pair_diagnostics':('prior_answer_pair_candidates','prior_answer_pairs_screened_as_reask','matching_pairs_fully_echoed_by_interviewer')}

def numeric(value):
    require(value is None or type(value) in (int,float) or
            (type(value) is list and len(value)==3 and all(type(x) in (int,float) for x in value)),'Unexpected clinical aggregate')
    return value

def window(stats):
    require(set(STAT_KEYS[:5])<=set(stats),'Required aggregate denominator')
    out = {k:numeric(stats[k]) for k in STAT_KEYS if k in stats}
    for key,fields in STAT_GROUPS.items():
        out[key]={f:numeric(stats[key][f]) for f in fields}
    return out

def cohort(block):
    out={k:numeric(block[k]) for k in ('participants','anchored_interviews','missing_opening')}
    out.update({k:window(block[k]) for k in ('turns_5_12','from_5_to_end')})
    return out

def clinical(files):
    folder = HERE/'patient-anchor'
    data = load(folder/'aggregate.json')
    files['aggregate/dais_clinical.json'] = convert({
        'source_archive_clinical_documents':numeric(data['source_archive_clinical_documents']),
        'opening_groups':{q:numeric(data['opening_groups'][q]) for q in ('Q2','Q3')},
        'primary':window(data['primary']),
        'primary_by_original_opening':{q:window(data['primary_by_original_opening'][q]) for q in ('Q2','Q3')},
        'sensitivities':{k:window(data['sensitivities'][k]) for k in ('four_tokens','six_tokens','without_prompt_filter','all_turns_after_four')}})
    comparison = folder/'comparison-aggregate.json'
    if comparison.is_file():
        d = load(comparison)
        out = {'groups':{},'inventory':{},'previous_clinical_Q2_Q3':cohort(d['previous_clinical_Q2_Q3'])}
        labels = ('Q1','Q2','Q3')
        matched = d['matched_opening_families']
        require(set(matched)<=set(labels), 'Unrecognized common opening')
        out['matched_opening_families']=matched
        for g in ('clinical','comparison'):
            out['groups'][g]={q:cohort(d['groups'][g][q]) for q in ('all',*labels,'other') if q in d['groups'][g]}
            fields = ('metadata_rows','archival_yes','archival_no','local_full_documents','matched_records_all_archival_yes',
                'no_usable_start','speaker_only_tagged_documents','timestamped_documents')
            out['inventory'][g]={k:numeric(d['inventory'][g][k]) for k in fields}
        files['aggregate/dais_comparison.json']=convert(out)

# These exact files are generated exclusively by the synthetic analytical pipelines.
# Each contract specifies top-level fields so future additions are not silently released.
AGGREGATES = {
    'primary':('results.json',('generation_turns','interviews','reader_sessions','readers','cross_reader_exact','unit')),
    'semantic':('semantic/results.json',('unit','readers','cross_reader','completed_first_forms','scheduled')),
    'calibration':('calibration/results.json',READERS),
    'lexical':('lexical.json',('method','current','previous','current_interview_words','previous_interview_words')),
    'decision':('decision.json',('qualified_readers','by_reader','adopt_as_research_candidate','observed_adoption_gates','conditional_competitive_signal','panel_superiority','adoption_robust_to_uncertainty','length_medians','note'))}

def reconstruction(files):
    path=HERE/'reconstruction'
    freeze=load(path/'freeze.json')['inputs']
    for name in ('targets.json','DESIGN.ko.md'):
        files['reconstruction/'+name]=checked(path/name,freeze[name])
    raw_results=load(path/'results.json')
    public_results={k:raw_results[k] for k in ('forms','planned_forms','planned_targets_per_arm_per_reader','independent_units','description','readers','cross_reader_by_arm')}
    files['reconstruction/results.json']=convert(public_results)
    plan=json.loads(checked(path/'private/schedule.json',freeze['private/schedule.json']))
    require(len(plan)==32 and len({(c['case'],c['arm']) for c in plan})==32,'Reconstruction schedule coverage')
    subset=sorted(plan,key=lambda c:(c['case'],c['arm']))
    decisions=[]
    for cell in subset:
        uid=cell['id']
        require(re.fullmatch(r'K[0-9a-f]{20}',uid),'Reconstruction record format')
        for reader in READERS:
            leaf=path/'ratings'/reader/uid/'first.json'
            rec=load(leaf) if leaf.exists() else None
            if rec:
                require((rec['reader'],rec['id'])==(reader,uid),'Reconstruction source mapping')
            for alias,v in sorted(cell['layouts'][reader].items(),key=lambda pair:pair[1]['domain']):
                item=rec['items'][alias] if rec else {}
                choice=item.get('choice')
                allowed=('A','B','insufficient','both_or_conflicting')
                efields=('turn','role','quote','supports')
                decisions.append({'case':cell['case'],'arm':cell['arm'],'reader':reader,'domain':v['domain'],
                    'condition':'questions_only' if cell['arm']=='Q' else 'full','gold_option':v['gold'],
                    'choice':choice if choice in allowed else None, 'outcome':item.get('status','missing_form'),
                    'reason':item.get('reason') if isinstance(item.get('reason'),str) else None,
                    'evidence':[{k:e[k] for k in efields} for e in item.get('evidence',[])]})
    files['reconstruction/first_decisions.json']=convert(decisions)
    # Neither includes decisive disagreements between foil/insufficient/conflict; unresolved includes invalid/missing.
    cells={(d['case'],d['arm'],d['domain'],d['reader']):d['outcome'] for d in decisions}
    joint={}
    for a in (*ARMS,'Q'):
        counts=dict.fromkeys(('both_correct','gpt_only_correct','opus_only_correct','neither_correct','unresolved'),0)
        for c in CASES:
            for domain in ('experience_or_function','appraisal_or_response'):
                g,o=(cells[c,a,domain,r] for r in READERS)
                if {g,o} & {'invalid','missing_form'}:
                    k='unresolved'
                elif g=='correct' and o=='correct':
                    k='both_correct'
                elif g=='correct' or o=='correct':
                    k='gpt_only_correct' if g=='correct' else 'opus_only_correct'
                else:
                    k='neither_correct'
                counts[k]+=1
        joint[a]={**counts,'scheduled_targets':16}
    files['reconstruction/reader_concordance.json']=convert(joint)


def external_length_benchmark(files):
    folder=HERE/'external-task'
    freeze=load(folder/'freeze.json')
    files['external-task/DESIGN.ko.md']=checked(folder/'DESIGN.ko.md',freeze['hashes']['DESIGN.ko.md'])
    raw=load(folder/'release.json')
    reference=raw['reference']
    def aggregate_group(key):
        return {g:{task:numeric(reference[key][g][task]) for task in ('story','laundry')} for g in ('patient','nonclinical')}
    fields=('case','source_model','task','condition','question','answer')
    rows=[]
    for row in raw['synthetic']:
        task=row['task']
        require(task in ('story','laundry') and row['question']==freeze['prefix']+'\n'+freeze['questions'][task],'External benchmark elicitation')
        require(row['source_model']==freeze['model'],'External benchmark source model')
        rows.append({**{k:row[k] for k in fields},'counts':{k:row['counts'][k] for k in ('english','whitespace')}})
    sources={k:reference[k] for k in ('citation','doi','clinical_population')}
    sources.update({k:aggregate_group(k) for k in ('means','n')})
    agg_keys=('arms','primary_patient_T2_vs_each','nonclinical_T2_vs_each','case_paired_differences',
              'leave_one_case_out','rank_lowest_first','rank_note')
    results={m:{k:raw['analysis'][m][k] for k in agg_keys} for m in ('english','whitespace')}
    integrity={k:raw['integrity'][k] for k in ('verified_first_outputs','frozen_fictional_profiles','tools_used','each_turn_history_empty','different_sessions')}
    files['external-task/release.json']=convert({'study':raw['study'],'reference':sources,'integrity':integrity,
        'caveats':raw['caveats'],'synthetic':rows,'analysis':results})


def payload():
    files={'README.ko.md':GUIDE.encode(), 'reproduce.py':(HERE/'reproduce.py').read_bytes()}
    frozen=project_prompts(files)
    files['cases.json']=checked(HERE/'cases.json',frozen['cases_sha256'])
    cases={c['id']:c for c in json.loads(files['cases.json'])}
    require(set(cases)==set(CASES),'Expected only synthetic cases N01–N08')
    for name,(path,fields) in AGGREGATES.items():
        d=load(HERE/path)
        files['aggregate/'+name+'.json']=convert({f:d[f] for f in fields})
    guide=load(HERE/'semantic/guide-freeze.json')
    files['semantic_guide.json']=convert({f:guide[f] for f in ('categories','scope','rounds','readers','missing','agreement')})
    clinical(files)
    primary_and_semantic(files,cases)
    reconstruction(files)
    external_length_benchmark(files)
    # The Korean final report remains a separate deliverable, so it can cite this frozen bundle.
    for name,raw in files.items():
        if name.endswith('.json'):
            txt=raw.decode()
            require(not re.search(r'"(?:session|session_id|provider|request_id|api_key|command|token|auth|account|account_id)"\s*:|\b[IK][0-9a-f]{20}\b|(?:/Users/|/private/var/|/home/)[^\s"]+',txt),
                    'Disallowed metadata in '+name)
    files['SHA256.json']=convert({k:digest(v) for k,v in files.items()})
    return files

def archive_bytes(files):
    stream=io.BytesIO()
    # Stored entries avoid compressor-version variance; fixed path order, owner bits and timestamps.
    with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_STORED) as z:
        for name in sorted(files):
            member=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
            member.create_system=3
            member.external_attr=0o100644<<16
            z.writestr(member,files[name])
    return stream.getvalue()

def main():
    files=payload()
    raw=archive_bytes(files)
    require(raw==archive_bytes(files),'Archive byte stability')
    with tempfile.TemporaryDirectory() as stage:
        folder=Path(stage)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            require(z.testzip() is None and set(z.namelist())==set(files),'ZIP integrity')
            z.extractall(folder)
        # Isolated standard-library interpreter; disallow all network and child-process operations.
        guard = """import runpy, sys
def offline(event, args):
    if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.posix_spawn'):
        raise PermissionError('Offline recalculation')
sys.addaudithook(offline)
runpy.run_path(sys.argv[1], run_name='__main__')
"""
        subprocess.run([sys.executable,'-I','-B','-c',guard,str(folder/'reproduce.py')],
                       cwd=folder,check=True,stdin=subprocess.DEVNULL)
    output=HERE/'release'
    output.mkdir(exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output,delete=False) as f:
        f.write(raw)
        tmp=Path(f.name)
    os.replace(tmp,output/ARCHIVE)
    print(ARCHIVE,digest(raw),len(raw),'bytes',len(files),'files')

if __name__=='__main__':
    main()
