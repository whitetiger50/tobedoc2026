# M22 후속 논의 — 실제 최초 비평과 Codex 응답에 대한 재검토
이것은 같은 전략 논의의 두 번째이자 마지막 예정 응답이다. 새 transport이나 아래 실제 교환만 명시적으로 전달한다. 합의를 요구하지 않는다. 다른 평가/멘토 세션은 사용하지 않는다. 새 환자 생성/평정/설계 구현은 없다.

## 최초 요청의 원목적과 현재 설계
사용자의 원목적은 '조현병 환자의 사고·의사소통 특성이 텍스트에서 어떻게 드러나는지, 이를 LLM으로 재현하고 분석할 수 있는가'다. 병명 라벨/일반 지시 반응 연구로 목표를 대신하고 싶어 하지 않는다. 한국 의대생 연구자로 3주, 환자 전사/전문의 자료 없음, 기존 GPT/Claude 구독만 사용한다.
현 M21: 같은 조현병 배경과 동일 새 그림에서 면담 주제 유지 지원 이력D/같은 횟수 외부 소음중단I/조직적이력O. 표적특징 지시 없이 D의 확정적 장면 모순E 증가/평가·정서밀도V 감소 예상. 문헌은 환자30명 내 임상 와해와 두 담화 지표의 탐색 상관. E는 원지표보다 좁고 V는 표준화 복합점수와 다름. 미실행.

--- 실제 Claude 최초 답변 전체 ---
# M22 설계 검토: 구성타당도와 원목적 부합

## 결론

- **원목적 부합은 '부분'이다. 권고는 실질 수정이다(중단은 아님).**
- 이 설계가 답하는 질문은 하나다. 환자 연구에서 관찰된 두 연관의 방향을 LLM이 간접 단서만으로 따라가는가. 이것은 "LLM으로 재현할 수 있는가"의 좁은 한 단면으로 정당한 질문이다.
- 그러나 현재 대조 구조로는 양성 결과가 나와도 "와해와 연결된 특징을 재현했다"와 "'어딘가 손상된 조현병 화자'라는 일반 페르소나를 연기했다"를 구별할 수 없다.
- 설계는 V(평가·정서 감소)를 "손쉬운 연기와 어긋날 수 있는 예측"으로 제시한다. 그런데 만성 조현병에 대한 흔한 고정관념에는 둔마된 정서와 빈약한 말이 포함된다[임상적 추론]. 그렇다면 E 증가와 V 감소는 둘 다 고정관념으로도 예측된다. 따라서 두 방향이 반대라는 점이 판별력을 주지 않는다. 이것이 가장 큰 약점이다.
- 수정의 핵심은 두 가지다. (1) 조작 변수를 '면담 지원 이력'이라는 약한 대리변수에서 개념적 와해라는 구성개념 자체로 옮긴다. (2) 일반 손상 페르소나와 예측이 갈리는 판별 조건을 넣는다. 3주 안에 가능하지만, 결과가 말하는 것은 끝까지 모델의 조건부 생성에 관한 사실이다. 환자에 관한 새 지식은 아니다.

---

## 1. 연결 고리 분해

| 단계 | 내용 | 근거 상태 |
|---|---|---|
| L1 | 조현병 환자 내 PANSS 개념적 와해 ↔ 오기술 비율(ρ=.51), 평가 장치 복합지표(ρ=−.61) | **[발췌 확인]** 수치와 방향은 원문과 일치한다. 저자가 사후·다중비교 때문에 "exploratory"라고 명시했다. |
| L2 | "면담 중 두 번 의제 되짚기가 필요했음" ≈ 개념적 와해의 관찰 가능한 표지 | **미검증 가정.** 설계도 인정하듯 주의·피로·면담자 스타일로도 생긴다. 두 번의 되짚기는 경도 수준이다. |
| L3 | 이력 텍스트 → 모델 내부의 '와해 상태' → 출력 | **점프.** 모델에는 와해 상태가 없다. 실제로 일어나는 일은 "이런 이력을 가진 사람은 어떻게 말하는가"에 대한 모델의 추론이다. |
| L4 | 출력의 E(확정 모순)·V(100단어당 밀도) ≈ 원논문의 오기술 비율·평가 복합지표 | **임의의 좁힘.** 원논문의 오기술 정의(Table 3)는 발췌에 없어 설계의 요약을 대조하지 못했다. V는 원논문처럼 질적·정서 비율을 표준화해 평균한 값이 아니다. |
| L5 | 방향 일치 → "환자 연구 특징의 재현" | **해석 점프.** L2·L3의 대안 경로가 같은 방향을 예측한다. |

**L1 자체에 대한 추가 주의 [발췌 확인 + 추론]**

- 같은 발췌에서 환자군의 오기술은 PPT(ρ=−.68)·WASI(ρ=−.46)와도 상관했다. PPT와의 상관은 개념적 와해와의 상관(.51)보다 크다.
- 오기술은 문법 복합지표(−.40)·지시 복합지표(−.45)와도 상관했다.
- 그렇다면 환자 자료에서도 오기술은 와해에 특이한 표지라기보다 일반 의미·비언어 인지 저하와 얽힌 지표일 수 있다.
- 이 점이 중요한 이유: 모델이 '일반 인지 저하' 페르소나로 E를 올려도 환자 공분산 구조와 우연히 맞을 수 있다. 결국 L5의 식별 문제가 환자 쪽 데이터에도 이미 들어 있다.

**원연구의 절차 [발췌 확인]**

- 면담자는 끼어들지 않되, 참가자가 마지막 컷 전에 멈추면 격려하거나 계속하라고 말할 수 있었다.
- 그러나 프롬프트 필요 여부를 예측변수로 분석했다는 내용은 발췌에 없다.
- 따라서 "되짚기 필요 이력"을 환자 자료와 잇는 경험적 다리는 없다.

**소음 조건 I가 해결하는 것**

- "면담자가 두 번 개입했다"는 사실, 개입 횟수, 과거 서술의 분량이 결과를 만든다는 설명을 줄인다.

**소음 조건 I가 해결하지 못하는 것**

- D와 I의 진짜 차이는 원인 귀속이다. D는 원인이 사람 내부에 있고 I는 외부에 있다. 모델에게 D는 "이 환자는 지금 상태가 나쁘다"는 신호다.
  - 그래서 D−I 대조는 '와해'가 아니라 '내부 원인의 손상 vs 없음'을 조작한다.
  - 손상의 종류(와해 vs 둔마 vs 인지 저하 vs 피로)는 열려 있다.
- 병명을 고정했기 때문에 D는 사실상 "상태가 나쁜 조현병 환자"가 된다. 그 결과 고정관념 묶음 전체(혼란, 정서 둔마, 말수 감소)가 함께 활성화될 수 있다.
- 시각 인식 오류는 조건과 무관하게 E에 섞인다. 모델별 이미지 처리 차이는 미확인 실행 의존성이다.
- 모델이 D를 실제로 어떻게 읽었는지 확인하는 조작 점검이 없다.

---

## 2. "직접 지시하지 않음"은 지시 수행을 넘어선 것인가

**짧은 답: 그 자체로는 아니다.**

- 역할극 생성은 정의상 지시 수행이다. 차이는 지시가 명시적이냐 함축적이냐뿐이다.
- '넘어섰다'를 의미 있게 말하려면 기준을 다시 세워야 한다. 지정하지 않은 속성 중에서, 데이터와 일치하고 단순한 대안 페르소나와는 다르게 채워지는 부분이 있는가.

**같은 결과(D에서 E↑, V↓)를 낼 수 있는 경로**

1. **잠재적 재현:** 모델이 학습 자료에서 와해와 담화 특징의 공변을 내재화해 일반화했다.
2. **의미적 프라이밍·페르소나 일반화:** "도움이 필요했다"에서 "능력 낮은 화자"를 추론해 덜 정교하고(V↓) 덜 정확하게(E↑) 말한다. 조현병 특이적이지 않다.
3. **고정관념 활성화:** "조현병 + 상태 나쁨"이 혼란과 무미건조를 함께 불러온다. V↓도 여기서 자연스럽게 예측된다.
4. **과제 오류:** 페르소나 연기 중 그림을 덜 참조해 시각 대조가 느슨해지고, 그 결과 E가 오른다.
5. **(추가) 사전학습 노출:** 공개 논문이나 유사 문헌을 본 효과는 차단할 수 없다. 설계도 인정한다.

**결과별로 주는 정보**

- **양성(두 방향 모두 일치):** "모델의 함축적 조현병 화자 표상이 와해 관련 이력에 대해 환자 연구와 같은 방향으로 움직인다"는 사실은 얻는다.
  - 원목적의 '재현'에 대한 하한 증거로 의미가 있다.
  - 그러나 경로 1과 2·3은 식별되지 않는다. 현 설계에는 2·3이 다르게 예측하는 조건이 없기 때문이다.
- **음성(바닥 또는 무변화):** 정보가 가장 적다.
  - 정확성을 강하게 학습한 모델에서는 확정 모순 E가 바닥일 가능성이 높다[추론].
  - 조작이 경도라서, 측정이 원지표보다 좁아서, 모델이 손상 묘사를 회피해서일 수 있다.
  - 이 원인들을 구분할 수 없다. "재현 불가"로 읽으면 안 된다.
- **혼합:** 예를 들어 E만 움직이고 V는 그대로라면, 모델이 이력을 '혼란'으로는 읽고 '정서 변화'로는 일반화하지 않는다는 정보가 된다.
  - 원목적에는 양성보다 오히려 구체적일 수 있다.
  - 그러나 왜 그런지는 역시 식별되지 않는다.

---

## 3. 질환 특이성과 기전 요구

- **질환 특이성은 필수가 아니다.**
  - 원논문의 연관은 조현병 환자 내 차원적 연관(와해 심도 ↔ 담화 지표)이다.
  - 진단 간 감별이 아니므로 주장도 차원 수준으로 두면 된다.
  - 실어증 집단에서도 오기술이 관찰된다는 사실(설계 기술, 발췌의 PwA 상관과도 일관)은 특이성 주장을 막는다. 하지만 차원 주장은 막지 않는다.
- **"실제 환자 기전을 알아야만 연구 가능"은 과도한 요구다.**
  - 표현형 수준의 시뮬레이션, 즉 관찰 가능한 행동 패턴의 재현은 기전 모형 없이도 정당한 연구 단위다.
  - 기전 주장만 하지 않으면 된다.
- **기전을 요구하지 않는 대신 최소 준거는 필요하다 [제안]**
  1. **표적 표현형의 경험적 정박:** 확보됨. 단일 탐색적 연구, n=30, 그림 하나라는 약한 정박이다.
  2. **조작–구성개념 대응:** 조작이 임상 변수와 개념적으로 대응해야 한다. 현재 가장 약한 부분이다(L2).
  3. **측정 충실도:** 원지표와의 차이를 명시하고, 가능하면 원정의에 더 가까운 보조지표를 둔다. 부분적으로 충족된다.
  4. **판별 준거:** 결과가 일반 손상 페르소나와 다르게 예측되는 지점을 최소 하나 포함해야 한다. **현재 없다. 가장 결정적인 결핍이다.**
  5. **측정 신뢰도:** 주판독자 1명이다. 중복 평정 규칙은 인계 문서에 있다고 하나, 나는 보지 못했다.

---

## 4. 한 문장 목적과 판단

**현 설계를 정직하게 쓴 한 문장**

> "환자 연구에서 개념적 와해와 연관된 두 담화 특징의 방향을, 와해를 명시하지 않은 면담 이력만 주었을 때 LLM이 새 그림 서사에서 따라가는지 관찰한다."

- 설명은 가능하다. 그러나 이 문장의 "와해를 명시하지 않은"이 연구 의미의 대부분을 떠맡고 있다. 그런데 2절의 이유로 그 장치는 해석상 이득을 주지 못한다. 오히려 L2라는 추가 가정과 대안 설명(피로·주의)만 늘린다.

**판단: 부분**

- 원목적의 "LLM으로 재현할 수 있는가"에는 좁게 닿는다.
- "사고·의사소통 특성이 텍스트에서 어떻게 드러나는가"에는 새로 기여하는 바가 없다. 그 부분은 원논문에서 가져온다.
- "분석할 수 있는가"에는 측정 체계를 만든다는 점에서만 간접적으로 닿는다.

**권고: 실질 수정**

- 중단하지 않는 이유:
  - 경험적 정박이 있는 출발점, 고정 자극 설계, 맹검 코딩, 반전 공개 규칙은 그대로 쓸 수 있다.
  - 판별 조건 하나로 해석력이 크게 달라진다.
- 기술적 엄밀성(해시, 시드, 문안 평행화)은 잘 되어 있다. 그러나 그것이 식별 문제를 해결하지는 않는다.

---

## 5. 대안 하나: 구성개념 직접 조절 + 판별 대조 + 독립 결과 준거

### 명시적 특징 지정은 순환논증인가

- 주장이 "지정한 특징이 나타났다"이면 순환이다.
- 다음 경우에는 순환이 아니다.
  - **(a)** 지정하지 않은 공변 특징이 경험적 방향대로 나타나는지 볼 때
  - **(b)** 조절 수준에 따라 결과가 단조적으로 변하는지 볼 때
  - **(c)** 측정 도구가 심어 둔 특징을 회수하는지 볼 때
- 핵심은 개발용 조절변수(무엇을 연기하라고 하는가)와 평가 준거(무엇을 재는가)를 분리하는 것이다. 준거 어휘가 조절 문안에 새지 않게 막아야 한다.

### 대안 설계 [제안, 미실행·미검증]

**조절변수 X(구성개념 자체)**

- 개념적 와해를 사고 흐름의 목표 지향성과 연결의 느슨함으로 기술하고, 없음/경도/뚜렷함의 3수준으로 준다.
- 기술에는 사실 정확성, 정서, 평가, 말수, 실수 관련 어휘를 넣지 않는다.
- 이렇게 하면 L2 점프가 사라진다. 또한 원논문의 상관(심도에 따른 연속 변화)에 대응하는 용량–반응 구조가 생긴다.
- 주의: PANSS 문항의 정확한 앵커 문구는 이 패킷에 없다. 원 정의를 확인한 뒤 문안을 써야 한다.

**판별 조건 Y(일반 손상 대조)**

- 같은 병명과 같은 심도 표현을 쓰되, 와해가 아닌 손상을 준다. 예: 말이 느리고 단어를 찾는 데 시간이 걸림, 또는 전반적 피로·저활력.
- 예측의 갈림은 다음과 같다.
  - **경험적 경로:** V 감소는 와해와 묶여 있다.
  - **일반 손상·고정관념 경로:** Y에서도 V가 비슷하게 감소하고 E가 오른다.
- 참고 근거: 발췌의 실어증군에서는 산출량이 적은 화자일수록 평가 언어가 보존되는 방향(ρ=−.45)이 보고되었다. 단어 찾기형 대조가 V에서 다른 예측을 가질 개념적 근거는 있다.
- 다만 이 근거는 다른 진단군의 집단 내 상관이다. 조현병 환자에서 음성증상이나 인지 저하가 V와 어떻게 연관되는지는 발췌에 없다("conceptual disorganization was most strongly associated"라는 문장만 있음). 따라서 Y의 예측은 가설로 표기해야 한다.

**독립 결과 준거**

- 기존 E·V를 유지한다.
- 원정의에 더 가까운 보조지표를 추가한다: 확정 모순 외에 이상하거나 무관한 기술을 포함한 넓은 오기술, 질적·정서 비율의 개별 보고.
- 가능하면 원논문 환자군에서 공변으로 보고된 지시(reference) 문제도 지정하지 않은 공변 특징으로 본다. 그러면 (a)형 검증이 하나 더 생긴다.

**조작 점검**

- 별도 새 세션에서 문안만 보여 주고, 이 사람의 어려움을 자유 기술하게 한다.
- 목적: X와 Y가 의도대로 다르게 읽히는지 확인한다.
- 이 단계는 생성 출력과 분리한다.

**규모**

- 4조건(X 3수준 + Y) × 8편 × 2모델 = 64개.
- 평행 문안을 유지하면 128개다. 3주 안에 1인 전수 코딩이 빠듯하다. 문안 반복은 개발 2편에서만 점검하고 본실험은 1문안으로 줄이는 것이 현실적이다. I·O 조건은 없앤다.
- **선행 점검(1~2일):** 개발 그림에서 "없음" 수준의 E가 바닥이 아닌지, 시각 오인이 모델별로 얼마나 되는지 먼저 본다. E가 사실상 0이면 E는 보조로 내리고 넓은 오기술을 주지표로 삼는다.

**이 대안으로 검증할 수 있는 것**

- 모델이 와해를 연기할 때 지정하지 않은 두 특징이 환자 연구의 방향과 용량 의존적으로 같이 움직이는가.
- 그 움직임이 일반 손상 연기와 구별되는가.

**남는 한계**

- 표적 상관 자체가 단일 탐색 연구에서 나왔다.
- 실제 환자와의 분포 비교와 전문의 판독이 없다.
- 사전학습 노출을 배제할 수 없다.
- 판독자가 1명이다.
- Y의 예측은 직접 실증이 아니다.

**솔직한 경계**

- 이 대안도 "조현병 환자의 의사소통을 LLM이 재현한다"까지는 가지 못한다.
- 갈 수 있는 곳은 "LLM의 와해 연기가 환자 연구의 특징 공변 구조와 어디서 맞고 어디서 일반 고정관념으로 환원되는가"까지다. 3주·환자 자료 없음 조건에서는 그것이 원목적에 정직하게 닿는 최대치라고 본다.

---

## 6. 결정적 질문과 주장의 경계

### 결정적 질문

1. **판별 질문:** 와해가 아닌 손상 페르소나에서도 같은 E↑·V↓가 나오는가?
   - 나온다면 결과는 "손상 연기 일반"이다. 와해와의 연결 주장은 성립하지 않는다.
   - 현 설계는 이 질문에 답할 수 없다.
2. **측정 가능성 질문:** 장면 정보가 온전할 때 두 모델의 기저 E가 바닥에서 벗어나는가? 그리고 시각 오인이 조건 효과와 분리되는가?
   - 아니라면 E 쪽의 모든 결과(양성이든 음성이든)는 해석할 수 없다.

### 과도하게 약한 주장 (연구 가치를 스스로 지움)

- "LLM은 시키면 틀린 이야기를 한다는 것을 확인했다."
  - 지정하지 않은 V 방향과 판별 조건의 정보를 버리는 서술이다.
- "환자 자료가 없으므로 이 결과는 아무 의미가 없다."
  - 모델의 함축적 표상이 경험적 공변과 맞는지는 그 자체로 검증 가능한 사실이다.

### 과도하게 강한 주장 (금지)

- "LLM이 조현병의 사고장애를 재현했다." / "합성 화자는 PANSS 개념적 와해 중등도 환자와 유사하다."
- "와해를 지시하지 않았으므로 모델에 잠재적 와해가 생겼다." / "모델이 임상 지식을 내재화했다."
- "E·V 결과가 원논문의 상관을 재현(replicate)했다."
  - 측정 정의가 다르다. 단위도 개인 간 상관이 아니라 조건 간 대조다. 표적 상관도 탐색적이다.

### 패킷 확인 범위 메모

- 원논문 발췌로 확인한 것: ρ값, 미보정 p, 탐색적 성격, 평가 복합지표의 구성, 면담자 프롬프트 절차, 환자군 내 오기술–PPT·WASI 상관.
- 확인하지 못한 것: Table 3의 오기술 정의, FDR 보정값, OSF 내용, 조현병·젊은 대조군 인원. 인원은 95−20−30=45라는 산술과는 일관된다.

--- Codex의 지적별 처리와 실질 반론 ---
# 최초 비평에 대한 Codex 처리와 후속 논점

1. 수용 — L2(면담 지원 이력과 임상 와해 사이) 근거 부재, L4 지표 변경, L5 양성 결과의 임상 재현 해석 한계. 현 M21은 원목적을 충분히 달성한다고 설명할 수 없다. 직접 지시하지 않음 자체로 구성타당도가 생기지 않는다.
2. 수용 — E↑·V↓가 일반 손상/고정관념에도 가능한 경로. V 감소가 뜻밖의 예측이라서 판별력이 있다고 단정하지 않는다. 다만 고정관념이 실제로 두 방향을 일으킨다는 것은 이번 미실행 자료에서 검증된 사실이 아니라 대안 가설이다.
3. 부분 수용/정정 — '모델에는 와해 상태가 없다'는 내부 구조의 존재/부재를 확정한 주장이다. 확인된 것은 임상적 와해 상태를 측정하거나 대응시킬 근거가 없다는 점이다. 표현형 모사에 기전 일치가 필수는 아니지만, 모델 내부에 병적 상태가 생겼다고 말할 수 없다.
4. 보류 — 직접 개념적 와해 조절+일반 손상 대조. 임상 문항의 이름/표현을 썼다고 조작–구성개념 연결이 검증되는 것은 아니다. 환자 임상심도와 모델 텍스트 수준의 동등성은 여전히 없다. 임상 특징을 지시해 생성하는 공학 실험은 가능하나, 핵심 결과가 LLM의 임상개념 표상/페르소나 생성 능력이라면 사용자가 거부한 목표 우회가 반복될 수 있다.
5. 반박/수정 요청 — 단어찾기/피로 대조의 E·V 방향은 같은 조현병 표본에서 확인되지 않았다. 실어증의 '산출량-평가장치' 상관을 조현병의 단어찾기 페르소나에 옮겨 기대대조를 확정할 수 없다. 같은 방향이면 곧바로 '일반 손상 연기일 뿐'이라고 단정할 수도 없다(실제 공유되는 표현형/비특이 경로 가능). 다르면 곧 임상 특이성의 증거도 아니다.
6. 반박 — 기저 E=0이라는 이유만으로 E의 양성·음성 결과를 모두 해석 불가라고 한 것은 과도하다. 대조군 0이어도 조작 조건에서 양성 오류가 나올 수 있고 대비는 정의된다. 바닥이 미세한 감소/음성 해석을 제한한다는 것과 검증 불가를 구별해야 한다. 개발에서 원하는 차이 여부를 보고 주지표를 교체하지 않는다. 원 임상지표와의 내용타당도/부호화 가능성에 따라 생성 결과를 보기 전에 고정할 수 있다.
7. 수용 — 실제 환자 분포/전문의 자료 없이 환자 유사성이나 같은 기전을 입증하지 못한다. 그러나 '3주 안에 이 대안이 정직한 최대치'라는 최적성은 확인되지 않았다. 지금 필요한 것은 다시 대안 수를 늘리는 일이 아니라 원목적의 어느 부분을 실제로 답하고 무엇은 답하지 못하는지 명확히 하는 것이다.


--- 추가 원문 발췌: Methods/Table3 (최초에는 Table3가 없어 직접 확인 못한 점 보완) ---
2.      Methods                                                           details, but the central content is of a man inviting another
                                                                          man for dinner and the hosting couple getting everything
2.1.    Participants                                                      ready for the evening, including a fish as the main dish. They
                                                                          welcome the guests but then notice that the fish has dis-
Ethical approval was obtained from the National Research                  appeared. One of the hosts runs into a fish and chip shop, and
Ethics Service Committee Northeast―Newcastle and North                    finally, everyone is enjoying fish and chips while a cat is in the
Tyneside 2 and the UCL Ethics Committee. Discourse samples                foreground licking its paw. The strip suggests the cat has
from 95 participants were analysed. All participants spoke                stolen the fish, but this is not depicted and must be inferred.
English as a native language. Exclusion criteria were designed            The Dinner Party contains false beliefs and several depictions
in accordance with the research traditions relevant to each               of emotional states. The strip has only a few printed words:
population, and to exclude mixed cases (such as dementia in               the title, “The Dinner Party”, some words on the notepad of
combination with aphasia).                                                the man being invited, “8pm Friday, Dinner with Smiths”, and
   We recruited 21 PwA either via the University College                  a sign saying “Fish 'n Chips”.
London's communication clinic or other London stroke net-                     Participants were asked to look at the pictures first and then
works. Exclusion criteria for PwA included history of neuro-              tell the story. The interviewer did not interrupt but could provide
degenerative disease or significant head injury prior to                  prompts to encourage the participant or to ask them to continue
aphasia onset, other cognitive or behavioural conditions                  if they stopped before they reached the final panel in the strip.
which can affect language or communication, including                         Speech was audio recorded and orthographically tran-
schizophrenia; accordingly, data from one individual with                 scribed. Where participants produced a phonological error,
aphasia were excluded due to signs of dementia symptom-                   but the target word could be clearly inferred, we noted the
atology. The remaining 20 PwA (mean age = 63.6, SD = 10.7;                target word. However, we did not add missing morphological
mean years of formal education = 13.9, SD = 2.2; 80% male)                information (such as suffixes) or correct any other grammat-
were in the chronic phase (mean 76.2 months post-onset;                   ical errors. Raters were blind to participant group, but not to
SD = 63.3), and it was a mixed group with regards to aphasia              whether data were recorded in London or Newcastle.
features. We recruited 30 older healthy controls (oHC; mean               Disruption to language can be obvious in participants, so that
age = 70.2, SD = 7; mean years of formal education = 14.3,                participant group could be inferred by transcribers. Tran-
SD = 2.0; 30% male) from University of Third Age London                   scriptions included pauses, paralinguistic phenomena and
chapters. The oHC group was older, t(48) = − 2.64, p = .01, and           verbalization errors (e.g., <laughs>, <unintelligible>). Micro-
matched for education, t(43) = − .67, p = .51.                            linguistic variables were annotated manually.

                                                        c o r t e x 1 9 5 ( 2 0 2 6 ) 8 1 —9 5                                                  85


   For this multi-level approach to narrative discourse anal-                 concepts central to the story. Utterances that were adequately
ysis, both microlinguistic and macrolinguistic measures were                  informative and reported events or details of the story were
devised, as detailed in sections 2.2.1 and 2.2.2.                             abstracted into narrative propositions. Propositions were
                                                                              assigned unique codes if they were produced by at least two
2.2.1.    Microstructure measures                                             control participants. Codes were used for analysis of narrative
For microstructure variables, we used the following essential                 organization (see Table 3). To exemplify the coding procedure,
units: Words (regardless of their morphological complexity),                  an excerpt from a participant's sample is presented below and
utterances (grammatically independent units of discourse),                    dissected into two narrative propositions along with their
pauses (hesitations longer than 250 msec; Rapcan et al., 2010),               respective referents.
clauses (configurations with a subject and a predicate), and                     e.g., a) they've gone to greet their guests b) who have arrived at
dependents (arguments or adjuncts of a predicate, e.g.,                       the door
grammatical objects, prepositional or adverbial phrases; In the                  a)
evening, they dress up nicely has four dependents). For each                     Theme: Internal Response-Setting.
verb, we determined whether it was episodic (e.g., “run”,                        Referent: they/hosts/Smiths Proposition: greet
“steal”), stative (e.g., “like”, “own”), a copular (“be”), or a                  b)
modal, (e.g., “must”, “can”). We further determined whether a                    Theme: Internal Response-Setting.
noun phrase was definite or indefinite, and whether a struc-                     Referent: they/guests/friends Proposition: arrive.
ture with an embedded clause was factive or non-factive. See                     Two raters within the research team independently
Table 2 for an overview of all microstructure variables.                      analyzed a small subset of the discourse samples. Inter-rater
                                                                              agreement was high (91%) and discrepancies were resolved
2.2.2.    Macrostructure measures                                             through mutual agreement.
At a macrolinguistic level, the story grammar model that best                    We computed seven measures which address various as-
fitted the event-based structure of the Dinner Party cartoon                  pects of macrostructure, such as narrative organization,
strip was a combination of Labov and Waletsky’s (1967; 1997)                  informativeness,       evaluative      devices,    narrative    mis-
and Stein and Glenn's (1979) narrative event classification (see              descriptions (see Table 3).
Zhang & Soergel, 2006, for mapping between them). We
focused on constitutive narrative propositions (similar to                    2.3.       Data analyses



Table 2 — Calculations underlying microstructure variables.

 Microstructure aspect                           Measure                                                      Description
 Productivity                      Word count                                           Number of words produced by the participant
                                   Utterance count                                      Number of utterances produced by the participant
                                   Mean length of utterance (MLU)                       Word count/utterance count
 Pauses                            Within utterance pause ratio                         n of pauses/(word count — n of clauses)
                                   Between utterance pause ratio                        n of pauses/n of clauses
 Grammar                           Mean number of dependents                            n of dependents/n of VPs
                                   Mean number of clausal embeddings                    n of clausal embeddings/utterance count
                                   Syntactic error ratio                                n of morphosyntactic errors/word count
 Reference                         Definiteness score                                   n of definite NPs/n of indefinite NPs
                                   Referential error ratio                              n of referential errors/word count
 Verb type                         Ratio of episodic verbs                              n of episodic verbs/n of verbs
                                   Ratio of stative verbs                               n of stative verbs/n of verbs
                                   Ratio of copular verbs                               n of copular verbs/n of verbs
                                   Ratio of modal verbs                                 n of modal verbs/n of verbs
 (Non)factive embedding            Factive embedding ratio                              n of factive embedded clauses/n of clausal embeddings
                                   Nonfactive embedding ratio                           n of nonfactive embedded clauses/n of clausal embeddings

86                                                      c o r t e x 1 9 5 ( 2 0 2 6 ) 8 1 —9 5




Table 3 — Description of macrostructure variables.

 Macrostructure aspect                  Measure                                                        Description
 Narrative organization      Associative chunk strength (ACS)         ACS was computed by sequencing all propositions to the order in which
                                                                      they were produced in each transcript. Repetitions of propositions were
                                                                      included at this step. We then determined the number of times a specific
                                                                      combination of two successive propositions (bigram) and three
                                                                      propositions (trigram) occurred across the reference control group samples.
                                                                      We then averaged bigram and trigram values for each participant's ACS.
                                                                      To allow compatibility with controls we subtracted 1 from the ACS of each
                                                                      control participant. This corrects for the fact that since HC formed the
                                                                      reference sample, their values end up naturally higher because whatever
                                                                      combination a control produces, that combination occurs at least once,
                                                                      namely in their own sample.
 Informativeness             Total propositions count                 Number of all propositions produced, including repetitions
                             Unique propositions count                Number of unique propositions produced, excluding repetitions
                             Repeated propositions ratio              ((n of total/n of unique propositions) - 1), i.e., a participant with 16 total and
                                                                      unique propositions has a ratio of 0.
 Evaluative devices          Qualitative language ratio               Words or phrases that express evaluation or judgement of the story
                                                                      characters or the setting (e.g., the culprit is hiding under the table, they are
                                                                      dressed in their best clothes, something terrible has happened). These were
                                                                      recorded in the form of a count per instance, including repetitions which
                                                                      have been argued to be a type of evaluative device in and of themselves
                                                                      (Armstrong & Ulatowska, 2007; Olness & Ulatowska, 2017). The ratio was
                                                                      computed as: n of qualitative words and phrases/word count
                             Emotional language ratio                 Words and phrases which refer to emotions (e.g., the hostess looks horrified,

## 이번에 답해야 할 사항
A. Codex의 수용·보류·반박 중 틀린 것이 있으면 반박하라. 특히 내부 상태 단정, 기저E=0의 해석, 일반 손상 대조의 임상근거, 직접 구성개념 지시의 남은 대리변수 문제를 정리하라.
B. 사용자의 근본 질문에 결론을 직접 내려라: 현 설계는 환자 담화 재현을 검증하는가, 아니면 LLM의 인물상/임상개념 반응을 보는 연구인가? 표현형 재현을 '지시한 텍스트가 나옴'보다 강하게 확인하려면 이 제약에서 실제 확보 가능한 무엇이 더 필요한가? 직접 개념적 와해 지시로 바꾸면 이 질문이 실질적으로 해결되는가, 아니면 더 정직해질 뿐인가?
C. 두 층을 분리해 최소한의 다음 조치를 제시하라. (i) 현재 자료/3주로 가능한 문헌 기반 합성 담화 공학·벤치마크, (ii) 실제 환자 특성과 닮았다는 검증에 추가로 필요한 외부 준거. 환자 전사 없이도 출판 문헌의 동일 측정/동일 과제 집단 요약값·검증된 코딩 정의로 어디까지 갈 수 있는지, 공변 두 방향만과 무엇이 다른지 따져라. 새 자료의 존재/허가는 확인하지 않았음을 유지하라. 직접 특징지시가 모두 순환이라는 표현도 교정하라(지시충실도 확인은 유효한 공학 평가이나 그것만으로 임상충실성이 되지 않음).
D. 판단을 위해 무엇을 더 확인해야 하는지를 최대 두 항목으로 좁혀라. 다시 96/128개 생성을 먼저 권하기보다, 생성을 하더라도 무엇이 해결되고 무엇은 안 되는지 설명하라. 사용자에게 새 본실험을 이미 승인된 것으로 말하지 마라. 새 설계/프롬프트 확정 없이 현안의 진행·보류·폐기 권고와 근거를 명확히 하라.

최종 답은 한국어 약1200~1800어절 이내. 새 참고문헌을 지어내지 말고 발췌 확인/추론/제안을 구분하라. 확정 가능한 범위와 남은 의견차이를 남겨라.
