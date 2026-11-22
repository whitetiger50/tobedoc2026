# M1: 실제 개발 발화 생성과 두 모델 단회 검토

2026-11-18. 기존 개발 사례 3개에서 GPT-6.1 Sol High를 사용해 4턴씩 **실제 합성 환자 발화 12개**를 생성했다. `runs-v01/*/transcript.json`의 `authored_context`는 이전에 Codex가 작성한 문맥이고 `generated_dialogue`만 이번 모델 출력이다. 모든 입력·전체 이력·원출력·공식 CLI 실행 설정을 보존했다. 별도 유료 API, 모델 다운로드, 패키지 설치는 없었다.

## 평정과 반영

GPT-6.1 Sol High와 Claude Opus 5.5에 `review-packet.json`과 `review-role.txt`를 똑같이 각 1회 전달했다. 한 호출에서 세 대화를 각각 한 번 평정했다. 생성 모델·조건명·다른 검토자의 답변은 제공하지 않았다. GPT는 같은 모델의 생성물을 평가하므로 자기 평가의 한계가 있다. PATIENTSIM의 Realism_w_Profile 원 앵커에서 ED patient를 psychiatric patient로 바꿨고, 새 임상 척도를 만들지 않았다.

- 사례 1 / M1-C: GPT 4, Claude 3 → **3.5/4**.
- 사례 2 / M1-A: GPT 4, Claude 3 → **3.5/4**.
- 사례 3 / M1-B: GPT 3, Claude 2 → **2.5/4**.
- 세 사례의 평균: **3.17/4**. GPT 원평점 평균 3.67, Claude 원평점 평균 2.67.

원평점과 산술평균은 `scores.json`, 원 비평은 `reviews/*/response.txt`, 지적별 수용·보류·반박은 `disposition.md`다. 모든 근거 인용이 해당 환자 원문에 존재하는지 Python으로 확인했다. 평균은 개발 참고값이다. 최종 성능, 평가자 반복성, 임상 타당성, 실제 환자와의 동등성을 나타내지 않는다.

두 검토자가 공통 지적한 것은 사례 3의 미기록 당일 활동을 회피로 답한 문제다. v0.2는 예정 질문에 필요한 사실 ID를 명시해 누락 시 생성 전에 중단하는 기능을 추가했다. 인과의 임의 연결, 설정 항목 나열, 이전 답변 전체 복사를 줄이는 지시도 보완했다. 짧은 사실 답을 억지로 변주하거나 경계심을 항상 단계적으로 표현하게 하지는 않았다.

## v0.2 사용과 범위

```bash
python3 -m speech_module prepare --input /absolute/path/to/case.json --out /tmp/new-speech-run --require-fact today_activity
```

`required_fact_ids=("today_activity",)`를 `build_packet`, `prepare`, `generate`에 전달해도 된다. 이 ID가 없거나 `patient_knows=false`이면 `MissingCaseDetail`이 발생하고 모델을 호출하지 않는다. 주석은 작성자가 질문을 보고 제공한다. **필요한 사실의 의미적 충족이나 임의의 새 질문에서의 누락을 자동 판단하는 기능은 아니다.** 예를 들어 `treatment`라는 ID만 있다고 약 이름·용량이 모두 있다는 뜻이 되지 않는다. 중요한 세부는 별도 ID와 구체적인 값으로 작성해야 한다.

누락을 발견하면 작성자가 새 가상 사실을 정해 별도 입력 버전으로 보완하거나 그 질문을 실행에서 보류한다. 자료에 없다는 이유로 환자가 모른다거나 말하기 싫어한다고 자동 설정하지 않는다. 기존 v0.1 패킷은 원 프롬프트로 계속 검증할 수 있다.

수정 후에는 사례마다 문제 관련 질문 하나씩 **3발화만 기능 확인**했다. 평정은 다시 받지 않았다. 사례 2의 인과 지식과 사례 3의 당일 활동은 명시적으로 추가한 합성 사실이다. `followup-plan-v02.json`에 생성 전 변경과 누락 차단을 남겼다. 입력 보완과 프롬프트 변경이 함께 있으므로 v0.1 대비 효과 크기나 점수 개선을 계산하지 않는다. v0.1 평균 3.17점을 v0.2의 점수로 표시하지 않는다.

관찰한 원문: 사례 1은 “환청일 수 있다고 생각해요.”라고 답하며 아침 상태를 덧붙이지 않았다. 사례 2는 “왜 자꾸 깨는지는 저도 잘 모르겠어요.”라고 답해 미확정 인과를 단정하지 않고 이웃에게 전달될지 다시 물었다. 사례 3은 새로 정한 합성 사실에 따라 “오늘 오후에는 집 근처를 좀 걸었어요.”라고 직접 답했다. 각각 한 출력의 관찰이며 안정적 개선이나 현실성 재평정의 결과는 아니다.

## 파일과 실행 기록

- `generation-plan.json`: 출력 전 고정한 질문과 설정. 생성 모델 `gpt-6.1-sol`, 추론 `high`.
- `runs-v01/`: 3대화·12발화, 턴별 패킷·원문·공식 CLI 출력.
- `review-freeze.json`: 검토 전 고정한 동일 자료·역할의 해시와 집계 규칙.
- `reviews/codex/`, `reviews/claude/`: 각 1회 응답, 원평점, 지적, 실행 메타데이터.
- `followup-plan-v02.json`, `runs-v02-functional/`, `followup-outputs-v02.json`: 수정 후 평점 없는 3발화와 입력 변경.
- `verification.json`: 구조 테스트 및 실제 기록 무결성 확인.

공식 CLI의 명시적 모델 선택과 로그를 기록했다. 구독 CLI는 불변 서버 snapshot과 temperature를 노출하지 않아 이를 고정된 릴리스·설정으로 추정하지 않았다. 생성 12회 + 기능 확인 3회, 개발 검토는 GPT 1회 + Claude 1회다. 과거 M0 Claude 설계 비평 1회는 별도다. 자동 재시도와 좋은 답변 고르기는 하지 않았다.

원 척도 출처: [고정 PATIENTSIM JSON](https://github.com/dek924/PatientSim/blob/9c262e692bd94305d922654d05bd1741c4d97433/src/prompts/eval/llm_eval_metrics_persona.json). `sources/llm_eval_metrics_persona.json`의 SHA-256은 기존 lock의 `ef29b12666d8241b6559db144e8004b91dab21d1ede6d5c306e27a7a5086e995`와 일치한다. 실행 설정 근거는 [공식 Codex 설정 문서](https://learn.chatgpt.com/docs/config-file/config-reference)와 설치된 CLI의 `--help`다.

다음은 v0.2의 완전한 새 개발 면담에서 사실 의존성 주석과 자발적 표현이 함께 작동하는지 확인하는 단계다. 기존 자료는 개발에 노출됐으므로 미사용 확인 자료로 다시 분류하지 않는다. 720회 판독은 최종 결과 단계에 남겨 둔다.
