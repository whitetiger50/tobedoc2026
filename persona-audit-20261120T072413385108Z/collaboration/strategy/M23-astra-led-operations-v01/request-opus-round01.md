# M23 Astra 주도 실제 운영·근거판정 검토 (별도 새 문맥, 최초 1회)

사용자(한국 의대생)는 1~2개월 연구 방향을 못 잡아 지쳤다. 원목적은 '조현병 환자의 사고·의사소통 특성이 텍스트에서 어떻게 드러나는지, 이를 기존 LLM으로 재현·분석할 수 있는가'이다. 지금 MacBook에서 같은 계정 Mac mini로 옮기며 '중간중간 나에게 묻지 말고 Astra를 주축으로 Sol·Opus와 내부 논의해 나아가는 시스템'을 명시 요청했다.

현재 실제 실행: Astra(gpt-6.2-astra high)에게 리더로 위임해 아래 운영규약과 근거감사 결정을 받았고 Sol(gpt-6.1-sol high)이 표준Python 이전도구를 구현했다. 당신은 이 주기의 별도 방법론 반론자다. 새로운 판독자/임상의가 아니다. 전체 저장소·대화·기존 판독세션은 전달하지 않는다.

현 상황: 실제 환자 전사·전문의 평정 없음. 기존 합성663턴/108대화, 수치732응답/731유효는 생성/측정 예비기록이며 임상타당성증거 아님. M21의 면담지원이력→새그림서사 E증가/V감소 96출력 설계는 임상준거 결손으로 미실행/보류다. 목표를 라벨반응/지시연기 연구로 조용히 바꾸지 않음. 최종12내용/720 미사용, 프롬프트수정·새발화·평정 이번주기 없음. 구매/API/새모델/외부연락 금지, 기존구독과공개출처만. 지금 할 일은 운영체계+기기이전+읽기전용 근거 한건이다.

이전 구현(코드 자체는 이번 방법론검토 범위밖): working-tree/untracked 연구파일 스냅샷 ZIP과 파일별SHA256, .git/환경/캐시/인증이름파일·외부symlink 제외, 원본보존, 검증추출은새목적지 전용. Finder압축해제 후 내장manifest 검증 지원. fixture12시험을 Sol이 통과했다고 보고했고 부모가 실제test/zip검증 예정. 아직 본archive미생성·Mac mini접근/설치/전송미검증. .codex/config.toml은 새 프로젝트 세션 Astra high 권장기본, .codex/agents별모델 지정과 AGENTS 위임규칙 존재. 현재열린대화모델변경 또는새Mac자동발견을확인한것아님. 역할파일만으로상시실행/실제협업이라고하지않음. 예약/백그라운드runner 생성없음.

질문:
1. Astra 운영방식이 일상선택을 사용자에게 돌리지 않고 실제증거를늘리면서 재검토/합의루프를막는가? 과도한사용자승인/목표우회/규칙문서만늘림 위험은 무엇인가? 현재지원이없는상시실행을약속하는가?
2. 아래새감사의 환자내 상관과 환자대조군 연령보정효과, p>.05 해석, 같은과제사용권/측정정의 미확인에 대한 판정이 타당한가? 저자 출력에서 읽은값이고 원자료 재분석아님. source URL/해시/모형위치 확인범위만 인용하고 도구없이 전문검증했다고하지말기.
3. 다음작업(기존임상근거+독립연구1편의1페이지요약)이 원목적의 임상절반을 실제로채우는 작은완료물인가, 또유예에불과한가? 다음한작업을더의미있게하는 최소수정/완료기준이있다면 제안하라. 새설계후보·생성배치를추가하는식은피하라.
4. 기존성과를 모두무의미하다고하거나 임상연구성과로포장하지않도록 사용자에게핵심을어떻게설명할지2~3문장. 연구자유사성과 모델협업합의를혼동하지않게하라.

치명적논점/필요수정/그대로진행가능판정 순. 한국어 약1000어절이내, 점수평정없음. 아래 실제 리더문서에 대한 최선의반론을주고 불필요한추가라운드를요구하지말라.


--- collaboration/OPERATING_MODEL.md ---
# Astra가 책임지는 연구 운영

연구 목적은 조현병 환자의 사고·의사소통 특성이 텍스트에서 어떻게 관찰되고, 기존 LLM이 어느 부분을 재현·분석할 수 있는지 밝히는 것이다. 연구자가 답해야 할 임상 질문과 생성기 개발의 성과를 기록에서 구분한다.

**Astra가 결정한다.** 현재 상태와 다음 작업을 읽고, 결론을 바꿀 수 있는 질문 하나, 이번에 남길 파일 하나, 완료·중단 기준을 먼저 정한다. Sol은 그 질문에 필요한 출처 확인·구현·검산을 맡는다. Opus에는 공개 또는 공유 가능한 최소 자료와 가장 강한 반례를 달라는 요청을 별도 문맥의 공식 구독 CLI로 보낸다. 단순 파일 점검이나 결정론적 계산에 매번 세 모델을 호출할 필요는 없다.

**사이클마다 증거가 하나 늘어야 한다.** 원문 위치와 수치, 검증된 실행 결과, 또는 특정 자료 경로의 닫힘이 산출물이다. 설계안 개수와 모델 합의 횟수는 성과가 아니다. 원문과 반대 근거가 충돌하면 Astra가 직접 확인한 뒤 채택·수정·기각, 이유, 불확실성을 기록한다. Opus 검토 기본 1회, 판정을 바꾸는 새로운 사실이나 중대 수정이 있을 때만 후속 1회. 의견 차이는 남겨도 된다. 같은 자료를 재논의할 때는 새로운 증거 또는 구체적인 오류를 먼저 제시한다. 한도에 도달하면 현재 증거로 결정하고 다음 독립적 작업으로 간다. 선호하는 결론이 나올 때까지 생성·심사하지 않는다.

**실제 역할을 호출한다.** 새 환경에서는 루트 AGENTS.md, 이 문서, AUTONOMY_STATE.json, NEXT_ACTION.md 순서로 읽는다. 사용자가 연구 진행을 맡긴 활성 작업에서, 런타임이 지원하는 실제 Astra(gpt-6.2-astra/high)를 선택 또는 위임해 리더 판단을 받고 Sol(gpt-6.1-sol/high)에 구현 범위를 준다. 부모가 Astra로 실제 확인된 경우 별도 Astra 호출은 생략할 수 있다. 세션이 보고하는 실제 모델, 요청 설정, 실행 여부와 증거 파일을 따로 기록한다. 권장 설정과 실제 응답의 검증이 다르고 모델 별칭이 불변 스냅샷을 보장하지 않는다. .cursor의 역할 프롬프트나 .codex 설정 파일만으로 실제 참여를 주장하지 않는다. Opus는 로컬 모델로 가장하지 않고 기존 공식 구독 CLI를 이용한다. 역할 하나가 없으면 기술복구·자료 정리 등 독립 작업은 계속하고 결손·결정 상태를 명시한다. Sol이나 Opus의 의견으로 실제 Astra 결정을 대신 표기하지 않는다.

**연구팀이 결정할 범위.** 이미 허용된 공개 원문 조회, 근거 대조, 제한된 공식 구독 검토, 로컬 파일 생성·정리와 결정론적 검산, 읽기 전용 기술 점검, 일상적인 구현 선택은 중간 승인을 구하지 않는다. 유료 API·구매, 외부 연락·제출·자료 신청, 제한 자료 접근/외부 전송의 권한, 원래 연구목표의 근본 변경은 사용자에게 올린다. 되돌릴 수 없는 작업이나 플랫폼의 필수 권한 절차는 그대로 따른다. 접근권·예산이 필요한 한 경로가 막혀도 허용된 독립 작업은 계속한다.

**보존과 범위.** 기존 원출력·v0.2·철회 기록을 보존한다. 최종12 내용과 720판독 계획은 작업 대상으로 삼지 않는다. 현재 M21 96개 본실험은 보류다. 이번 운영 전환에서는 새 환자 발화·평정·프롬프트 변경을 실행하지 않는다. 현재 허용 범위는 상태 파일에 적는다. 임상 전문가나 환자 데이터의 확보는 실제 증거가 있을 때만 갱신한다.

**기기 이동과 보고.** 상태 파일에 마지막으로 검증된 사실, 다음 파일, 소유자·상한·중단 규칙을 갱신한 뒤 멈출 수 있다. 경로는 프로젝트 루트 기준으로 적고 호스트별 인증 파일은 복사하지 않는다. 다음 기기에서 작업이 재개되면 기존 상태에 이어 진행한다. 동일 계정 로그인과 파일 규약만으로 채팅 종료 뒤 상시 백그라운드 실행이 보장되지는 않는다. 추가 채팅, 예약 자동화, 무한 CLI 루프는 만들지 않는다. 사용자에게는 새로운 연구 판단, 실제 결과 또는 권한상 필요한 결정만 간단히 전달한다.


--- collaboration/AUTONOMY_STATE.json ---
{
  "schema_version": 1,
  "updated_local": "2026-11-20",
  "root_relative_to": "persona-audit",
  "objective": "조현병 환자의 사고·의사소통 특성의 텍스트 표현과 기존 LLM의 재현·분석 가능성",
  "cycle": "M23",
  "workflow": "resume_on_active_turn",
  "background_scheduler_created": false,
  "decision_owner": "Astra",
  "runtime_roles": {
    "lead": {"requested": "gpt-6.2-astra/high", "current_evidence": "active follow-up to Astra research lead; model family/effort assigned via delegation, not immutable snapshot verification"},
    "implementation": {"requested": "gpt-6.1-sol/high", "task_this_cycle": "macOS handoff implementation coordinated by parent; requires its own runtime evidence"},
    "counterargument": {"requested": "Claude Opus 5.5 via official subscription CLI", "task_this_cycle": "independent review coordinated by parent; read final record before attributing response"}
  },
  "decisions": {
    "clinical_similarity_validated": false,
    "m21_generation": "hold",
    "m22_critique": "accepted; earlier synthetic cue lacks independent mapping to observed clinical disorganization",
    "m23_same_task_benchmark": "not established in checked documents; public model contrasts available, exact stimulus reuse rights, equivalent E/V coding and reference distributions unverified",
    "available_work": "clinical evidence extraction and existing engineering/measurement pilot",
    "current_authorized_outputs": "operating system, migration handoff and bounded public-evidence appraisal; no new patient-role outputs, ratings or patient prompt edits"
  },
  "protected": ["historical evidence and v0.2", "final 12 content stays unused", "720 final reads stay unused", "withdrawn TLC modification and BPRS realism metric stay retired"],
  "lead_report": "collaboration/strategy/M23-astra-led-operations-v01/astra-lead.md",
  "evidence": "collaboration/strategy/M23-astra-led-operations-v01/benchmark-evidence.json",
  "operating_model": "collaboration/OPERATING_MODEL.md",
  "next_action": "collaboration/NEXT_ACTION.md",
  "next_delivery": "collaboration/strategy/M23-astra-led-operations-v01/patient-language-evidence-brief.md",
  "handoff": "Read root AGENTS.md, operating_model, this state, then next_action. Restore actual roles when an active task runs. Use project-relative paths. Do not assume models or credentials from this host transfer to another host.",
  "escalate_to_user": ["new spend or paid API", "external contact, submission or permission request", "restricted data access/transfer authority", "fundamental objective change"],
  "review_budget": {"standard_opus": 1, "followup_only_if_material": 1},
  "review_and_migration_integration": "Parent integrates actual review and validation records. An assigned role is not evidence of completed work."
}


--- collaboration/NEXT_ACTION.md ---
# 다음 활성 연구 작업

**책임자 Astra · 실행 Sol · 필요 시 반론 Opus**

다음 결과물은 한 장의 **환자 발화 근거 요약**이다. 답할 질문은 “환자의 말에서 무엇이 관찰되며, 그 해석은 과제에 따라 어떻게 달라지는가?”다. M23에서 확인한 그림 이야기 연구와 별도 환자 표본의 구조화·비구조화 질문 실험 한 편만 사용한다. 다른 프롬프트를 제안하거나 M21의 같은 사용권 조사를 되풀이하지 않는다. [Barch·Berenbaum 원논문 정보](https://pubmed.ncbi.nlm.nih.gov/9255856/)

1. Sol은 M23의 benchmark-evidence.json과 Barch·Berenbaum(1997) 원문 또는 합법적으로 열리는 저자본을 대조한다. 39명 환자의 이야기/질문 생산 실험에서 무엇을 바꾸고 무엇을 측정했는지, 집단 간 차이인지 한 집단 내 과제 차이인지 확인한다. 원문 두 경로까지만 시도하고 초록에서만 확인된 항목에는 그 사실을 적는다. 환자 전사, 개인별 파일, 요청형 자료, 생성 CLI는 필요 없다.
2. 한 페이지에 과제·언어/장르·표본·측정 정의·주요 관찰·보존된 기능/확인할 수 없는 점을 출처 위치와 함께 쓴다. Zimmerer의 환자 내 상관과 연령 보정 집단 대비를 나눈다. 다른 과제·지표·연구의 효과를 합산하지 않는다. 마지막 두 문장에 임상 근거가 있는 범위와 LLM 출력에서 아직 시험되지 않은 범위를 명시한다.
3. Astra가 원문과 대조해 독립 연구의 근거가 보강됐는지 또는 비교가 어려운지 결정한다. 임상적 의미에 실질적 이견이 있을 때 Opus 1회 이내. 1개 문서, 2개 연구, 새 후보 탐색 0개, 새 생성·평정 0회, 모델 호출 총 3회 이내(Astra·Sol·Opus 각 1회), 활성 작업 1시간을 권장 상한으로 한다. 기존에 같은 요약이 완성됐다면 검증하고 닫는다.
4. 결과를 collaboration/strategy/M23-astra-led-operations-v01/patient-language-evidence-brief.md에 저장한다. 원문 제한이 있어도 확인된 내용으로 완료하고 불확실성만 표시한다. 다시 설계 토론을 시작하지 않는다. 임상 관련성이 있으며 같은 과제·정의로 시험할 조건이 생긴 경우에만 후속 소규모 측정 타당성 작업을 제안한다. 그렇지 않으면 검증된 임상 근거와 기존 합성 예비실험의 측정 한계를 갖춘 포스터 자료를 정리한다. 임상 재현 성공을 제목에 넣지 않는다.


--- collaboration/strategy/M23-astra-led-operations-v01/astra-lead.md ---
# 연구 책임자의 결정 · 2026-11-20

**지난 작업은 언어를 생성하고 기록하는 실험 기반과 평가법의 한계를 남겼다. “조현병 환자의 어떤 말하기 특성을 이 모델이 재현하는가?”에는 아직 실험적으로 답하지 못했다.** 생성·판독 횟수가 늘고 프롬프트 문구가 정밀해지면 진전처럼 보이지만, 비교할 실제 환자 쪽 관찰이 없으면 역할 연기의 품질만 정교해질 수 있다. 사용자가 지난 두 달의 의미를 의심한 이유는 타당하다. 그 간극을 또 다른 생성 조건으로 메우지 않겠다.

남길 것은 108대화·663개 합성 발화의 개발 기록, 사실·자기이해·대화이력 분리, 공식 구독 CLI의 새 세션과 원문·버전·해시 보존, 그리고 반복 판독이 잘못된 안도감을 줄 수 있음을 보여 준 사례다. M18에서 원래 현실성 평정은 GPT가 모두 4, Claude가 모두 3이었다. 반복값이 같아도 범위 내 차이를 구별한다는 증거는 없다. 이 기록은 향후 측정 방법의 설계를 돕는다. 환자의 언어를 잘 모사했다는 증거로는 쓰지 않는다.

내가 M21에서 제안한 96출력 설계에도 같은 한계가 있다. 연구자가 작성한 면담 지원 이력이 실제로 측정한 개념적 와해를 대변하는지 알 수 없다. M22의 Opus 반론을 수용한다. M21은 이 간극이 해소되지 않은 상태에서 본실험으로 진행할 가치가 낮다. 전체 연구의 목적과 기존 기반은 유지한다.

## 이번에 내린 과학적 결정

**환자들 사이에서 증상과 언어 특징이 함께 변한다는 관찰**과 **환자군이 대조군과 얼마나 다른가**를 구분했다. Zimmerer 등은 같은 여덟 컷 그림을 설명한 영국 조현병 환자 30명에서 개념적 와해와 서사 오기술의 양의 상관(ρ=.51), 평가·정서 언어 복합지표의 음의 상관(ρ=−.61)을 보고했다. 연구자들이 사후 탐색한 연관이다. [원논문](https://discovery.ucl.ac.uk/id/eprint/10219274/1/Zimmerer_1-s2.0-S0010945225003193-main.pdf)

저자의 공개 출력에서는 이 환자군과 해당 대조군 15명을 연령 보정해 비교한 값도 찾았다. 오기술은 d=+0.53, p=.101로 집단차 추정의 불확실성이 남는다. 질적 평가 표현은 d=−0.71, p=.032, 정서 표현은 d=−0.75, p=.023이었다. 오기술에 대한 환자 내 상관을 모든 환자에게 흔한 오류로 번역하면 안 되는 구체적인 사례다. 세 수치는 연구자들이 사용한 모형의 표준화 대비다. 원자료 참여자를 다시 분석하거나 집단별 절대 수준을 추정하지 않았다. [저자 결과·코드](https://osf.io/download/gde5x/)

원문에 측정 정의가 있고 일부 집단 효과크기도 있다는 점에서 출발점이 달라졌다. 그러나 출처가 별개인 원만화의 여덟 컷과 재사용 조건, 같은 기준을 적용할 참조자료는 확인하지 못했다. 저자 소프트웨어의 공개 색인과 설명서는 계산 절차와 더미 자료를 제공한다. 소프트웨어 라이선스가 원만화의 사용까지 허용한다는 근거는 찾지 못했다. 원 과제와 다른 만화에서 좁은 ‘명시적 모순’을 세면 원 연구의 ‘틀리거나 이상하거나 무관한 오기술’과 분모·분자가 달라진다. **현재 자료로는 M21을 동일 과제·동일 지표의 임상 벤치마크로 열지 않는다.** 그림이 영구적으로 입수 불가능하다는 뜻은 아니다. [저자 설명서](https://github.com/macronarr/macronarr/blob/0ee7e9f4322f465fce095205f5708e657ef92692/MacroNarr_Documentation.pdf)

다음 결과물은 실제 환자 발화 연구 두 편에서 관찰한 특성을 과제·집단·측정 정의·제약까지 포함해 한 장에 제시하는 것이다. 여기에 아직 측정하지 못한 LLM 쪽 항목을 표시한다. 이번 연구는 근거가 있는 임상 절반부터 완성할 수 있다. 추가 설계 경쟁이나 96개 생성 전에 그 한 장이 연구의 중심을 잡는다. 전체 파일·위치·숫자와 해시는 같은 폴더의 benchmark-evidence.json에 남겼다.

## 운영 인계

Astra가 연구 결정을 맡고 Sol은 근거 추출·구현과 검산, Opus는 핵심 주장의 반례 한 가지를 맡는다. 중재 요청 대신 근거와 채택/기각 이유를 기록한다. 실제 호출된 모델과 설정만 참여자로 표시한다. 사용자가 프로젝트를 열고 작업을 재개하면 루트 규칙과 collaboration의 운영기록을 읽어 역할을 복원한다. 채팅 종료나 기기 이동 이후 상시 실행을 약속하는 규약은 아니다. 이번 사이클에서는 환자 프롬프트, 새 생성·평정, 최종12·720을 사용하지 않았다.


--- collaboration/strategy/M23-astra-led-operations-v01/benchmark-evidence.json ---
{
  "cycle": "M23",
  "checked": "2026-11-20 Asia/Seoul",
  "question": "Does the checked Zimmerer package supply matching patient/control statistics, reproducible linguistic measures and the same usable original stimulus for a new synthetic comparison?",
  "decision": "Published clinical comparisons exist. A same-task, same-measure benchmark is not currently established. Keep M21 main generation on hold. Do not replace the original comic with a new comic and report the old group levels as a matching reference.",
  "sources": [
    {
      "source": "Zimmerer et al. Cortex 195 (2026), 81–95; DOI 10.1016/j.cortex.2025.12.006",
      "url": "https://discovery.ucl.ac.uk/id/eprint/10219274/1/Zimmerer_1-s2.0-S0010945225003193-main.pdf",
      "sha256_of_retrieved_pdf": "8337c64292940bbed9481f170fea0d9034038435d03a0accb6d3a4bdffd9e4c3",
      "locations": "Methods §§2.1–2.2; Table 3; Results §§3.1.2, 3.4",
      "scope": "30 English-speaking patients with schizophrenia and 15 corresponding Newcastle healthy controls in the cartoon task. Original study also includes aphasia and London comparison groups; those cohorts are not used for the listed SZ contrasts. The clinical measure is an observed PANSS conceptual-disorganization item, while M21's previous interview cue was investigator-authored.",
      "measurement": "The misdescriptions counted by the authors include wrong, odd and irrelevant descriptions per total propositions. Qualitative and emotional expression counts (including repetitions) are divided by words. The source within-patient evaluation composite uses standardized component measures. The M21 E and V differ in both operationalization and aggregation. Pauses require speech timing; ACS additionally requires the source controls’ sequences of coded propositions.",
      "public_article_copy": "collaboration/strategy/M23-astra-led-operations-v01/evidence/Zimmerer-et-al-Cortex-2026.pdf",
      "attribution": "Zimmerer et al., © 2025 The Author(s), published by Elsevier Ltd., Cortex 195 (2026) 81–95. Unmodified PDF from UCL Discovery. Article CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Original third-party cartoon excluded from any assumption of licensed reuse."
    },
    {
      "source": "Author-posted R analysis and rendered outputs. Read from the immutable bytes fetched during M21, without executing R code or computing individual-level statistics.",
      "project": "https://osf.io/6p5wu/",
      "inventory": "https://api.osf.io/v2/nodes/6p5wu/files/osfstorage/",
      "file": "https://osf.io/download/gde5x/",
      "sha256_of_zip": "62cbf0fbab0011045e8d5a8f50abb8172a91704422c8ba71afd6f5167869ebb8",
      "group_code": "R_analysis_code_and_output/R_analysis_code_and_output/R_analysis_markdown_scripts/Group_Differences_R_analysis.Rmd",
      "group_output": "R_analysis_code_and_output/R_analysis_code_and_output/R_analysis_output/Group_Differences_R_analysis.html",
      "how_to_locate": "Within the Newcastle regression section take the JointSZSZ predictor row under each listed outcome (not the earlier JointSZAphasia or later standardized cross-clinical comparison). Ref is NCNC. Rmd fits outcome ~ JointSZ + Age, uses emmeans and eff_size with fitted model residual sigma/df, and places the signed group effect in EffectSize. Ratio variables may be transformed; these are standardized model effects, not raw group means or per-person distributions.",
      "between_group_published_model_outputs": [
        {
          "outcome": "Misconceptions_ratio",
          "reported_measure": "misdescriptions",
          "group_effect_d": 0.5312325,
          "t": 1.678395,
          "p": 0.100697
        },
        {
          "outcome": "QLN_ratio",
          "reported_measure": "qualitative language",
          "group_effect_d": -0.7074804,
          "t": -2.2228593,
          "p": 0.031799
        },
        {
          "outcome": "ELN_ratio",
          "reported_measure": "emotional language",
          "group_effect_d": -0.7453092,
          "t": -2.354756,
          "p": 0.023284
        }
      ],
      "within_group_output": "R_analysis_code_and_output/R_analysis_code_and_output/R_analysis_output/Within_Group_Correlations_R_analysis.html; schizophrenia results rows 51 and 56",
      "within_sz_correlations_from_author_output": [
        {
          "outcome": "misdescriptions",
          "spearman_rho": 0.511393706,
          "p": 0.003873328,
          "fdr_p": 0.02582219
        },
        {
          "outcome": "evaluative devices composite",
          "spearman_rho": -0.608443559,
          "p": 0.00046189,
          "fdr_p": 0.0046189
        }
      ],
      "interpretation": "The positive within-patient correlation does not establish a patient-versus-control effect. The latter has a positive estimate and inconclusive conventional test for misdescriptions; p=.100697 does not establish zero or equivalence. Report all three author-posted model contrasts together; the group p values here are those printed, not new multiplicity-adjusted confirmatory tests.",
      "available_and_missing": "Code and HTML establish same-outcome contrasts that M22 did not have. We did not establish a ready-to-use bundle of the per-group raw mean, SD and individual distributions for all required measures in the inspected reports. Do not confuse age-regression intercepts with group means. A speaker-feature CSV is publicly indexed; M21 checked its header. OSF project license metadata had no license. No participant rows were extracted this cycle and permission for reuse or sending participant material to a provider is not assumed."
    },
    {
      "source": "Authors' MacroNarr software repository; complete recursive Git tree response: truncated=false, 23 paths. README, documentation, test CSVs, assets, and source files.",
      "url": "https://github.com/macronarr/macronarr/tree/0ee7e9f4322f465fce095205f5708e657ef92692",
      "documentation": "https://github.com/macronarr/macronarr/blob/0ee7e9f4322f465fce095205f5708e657ef92692/MacroNarr_Documentation.pdf",
      "attributions": "https://github.com/macronarr/macronarr/blob/0ee7e9f4322f465fce095205f5708e657ef92692/ATTRIBUTIONS.txt",
      "observed": "Public instructions describe building a control-derived list of narrative concepts, talk of a future database and label distributed examples dummy data. Root has software licensing/attributions. No separately named Dinner Party eight-panel stimulus, stimulus-specific reuse permission or certified original control proposition-sequence reference was identified in the inspected tree and documentation. Clinical paper identifies Fletcher & Birt (1983) as separate source. Access, copyright and external delivery are unconfirmed, not proven prohibited. No images or dummy/participant sequences were sent to a model."
    }
  ],
  "next_action": "Write one finite clinical-evidence brief addressing the original question. Contrast this anchor with Barch & Berenbaum (1997) in a separate patient speech-production task; record exactly which observable pattern each study supports. No new clinical claim from synthetic data."
}
