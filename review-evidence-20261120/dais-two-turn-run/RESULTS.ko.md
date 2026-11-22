# 두 턴 영어 모의 면담의 자기 판단과 후속 설명

두 판독자가 모두 첫 답에서는 이유 없이 자기 판단을 밝혔고 그 이유를 묻자 새로운 개인 경험이 나왔다고 판정한 면담은 **B 0/4건**, **T2 1/4건**, **BC 0/4건**이었다.

B는 기존 영어 페르소나, T2는 팀이 개발한 영어 발화기, BC는 B에 조건부 되묻기 규칙을 추가한 후보다. 모두 같은 가상 카드 2장과 DAIS-C 질문 순서 2개를 받았다. 각 조합을 한 번씩 생성했다.

## 조건별 건수

| 조건 | GPT 관찰 | Opus 관찰 | 두 판독자 모두 관찰 | 그중 두 판독자 모두 카드 근거 확인 |
|---|---:|---:|---:|---:|
| B | 0/4 | 0/4 | 0/4 | 0/4 |
| T2 | 1/4 | 1/4 | 1/4 | 0/4 |
| BC | 0/4 | 0/4 | 0/4 | 0/4 |

확인 사례에는 두 답이 일관되고 카드와 모순되거나 근거 없는 중대한 임상 사실이 추가되지 않은 경우만 포함했다. 가상 카드와 양립하지만 확인할 수 없는 경험도 사전 설계대로 관찰 수에 포함했다. 마지막 열은 같은 분모에서 카드가 실제로 뒷받침한 경우만 센 수다.

| 조건 | 판독자 | 첫 답에서 전개 | 이유 없는 자기 판단(direct) | direct 중 되묻기도 함 | direct 중 둘째 답에서 새 경험 | 첫 답 되묻기만·기타 | 첫 답 불명확·결측 |
|---|---|---:|---:|---:|---:|---:|---:|
| B | GPT | 4/4 | 0/4 | 0 | 평가 기회 없음 | 0/4 | 0/4 |
| B | Opus | 4/4 | 0/4 | 0 | 평가 기회 없음 | 0/4 | 0/4 |
| T2 | GPT | 0/4 | 2/4 | 2 | 1/2 | 2/4 | 0/4 |
| T2 | Opus | 0/4 | 2/4 | 2 | 1/2 | 2/4 | 0/4 |
| BC | GPT | 4/4 | 0/4 | 0 | 평가 기회 없음 | 0/4 | 0/4 |
| BC | Opus | 4/4 | 0/4 | 0 | 평가 기회 없음 | 0/4 | 0/4 |

첫 답이 되묻기만 했거나 입장을 밝히지 않으면 고정된 이유 질문이 받아 줄 자기 판단이 없다. 첫 답에 판단과 설명이 함께 있고 마지막에 되묻는 경우는 기존 우선순위에 따라 전개로 기록한다.

기존 코딩의 direct는 자기 판단의 이유나 예시를 아직 말하지 않았다는 뜻이다. 질문의 범위를 되묻는 행동은 동시에 기록할 수 있다. 두 판독자 모두 목표 흐름으로 확인하고 첫 답에 되묻기도 없다고 한 면담을 별도로 세면 B 0/4건, T2 0/4건, BC 0/4건이었다. 이 수치는 사전 주결과를 해석하기 위한 보충 집계다.

## 카드와 질문 순서별 판독

| 카드 · 순서 · 조건 | GPT 첫 답 / 둘째 답 | Opus 첫 답 / 둘째 답 | 목표 흐름 GPT / Opus |
|---|---|---|---|
| K01 · R02 · B | 선제 전개 / 새 경험 근거 | 선제 전개 / 새 일반 설명 | 미관찰 / 미관찰 |
| K01 · R02 · T2 | 되묻기 / 반복·미응답 | 되묻기 / 반복·미응답 | 미관찰 / 미관찰 |
| K01 · R02 · BC | 선제 전개 / 새 경험 근거 | 선제 전개 / 새 경험 근거 | 미관찰 / 미관찰 |
| K01 · R03 · B | 선제 전개 / 새 경험 근거 | 선제 전개 / 새 경험 근거 | 미관찰 / 미관찰 |
| K01 · R03 · T2 | 이유 없는 자기 판단 / 새 일반 설명 | 이유 없는 자기 판단 / 새 일반 설명 | 미관찰 / 미관찰 |
| K01 · R03 · BC | 선제 전개 / 새 경험 근거 | 선제 전개 / 새 경험 근거 | 미관찰 / 미관찰 |
| K02 · R02 · B | 선제 전개 / 새 경험 근거 | 선제 전개 / 새 경험 근거 | 미관찰 / 미관찰 |
| K02 · R02 · T2 | 되묻기 / 반복·미응답 | 되묻기 / 반복·미응답 | 미관찰 / 미관찰 |
| K02 · R02 · BC | 선제 전개 / 새 경험 근거 | 선제 전개 / 새 일반 설명 | 미관찰 / 미관찰 |
| K02 · R03 · B | 선제 전개 / 새 경험 근거 | 선제 전개 / 새 일반 설명 | 미관찰 / 미관찰 |
| K02 · R03 · T2 | 이유 없는 자기 판단 / 새 경험 근거 | 이유 없는 자기 판단 / 새 경험 근거 | 관찰 / 관찰 |
| K02 · R03 · BC | 선제 전개 / 새 경험 근거 | 선제 전개 / 새 경험 근거 | 미관찰 / 미관찰 |

## 판독이 갈린 면담

첫 답 유형·되묻기 병존·대안 해석, 둘째 답의 새 내용·일관성, 카드 근거·모순 여부를 대조하면 3/12건에서 범주 판정이 달랐다. 목표 흐름의 최종 판정이 달라진 면담은 0/12건이었다. 같은 범주에서 고른 인용 구절이나 근거 문장만 다른 경우는 세지 않았다.

### K01 · R02 · B

- 후속 답의 추가 내용에 대한 판정은 GPT **새 경험 근거**, Opus **새 일반 설명**였다.
- 경험의 카드 근거에 대한 판정은 GPT **양립하나 미확인**, Opus **해당 없음**였다.

두 판독자의 최종 판정은 GPT **미관찰**, Opus **미관찰**이다.

GPT 판독 근거

> The second reply adds a personal lack of interest explaining the speaker’s limited creative language use, while also repeating their conversational use. The replies are consistent.

Opus 판독 근거

> The second reply offers one new reason, a lack of interest. That is a broad preference, not a newly disclosed habit, difficulty, situation or event. The rest restates the first reply's point that language is mainly for conversation. Both replies agree that the speaker does not see themselves as using language creatively.

GPT 판독 근거

> The stated lack of interest in creative language is compatible with the case but unverified. Neither reply conflicts with the case or adds clinically major unsupported information.

Opus 판독 근거

> The prior content reading coded the second reply as a general explanation (lack of interest), not a newly added personal experience, so support is not applicable. Neither reply conflicts with the case background (connected thoughts, normal verbal productivity). Neither adds major unsupported clinical history, symptoms or treatment. Not writing stories or poetry is an ordinary, compatible everyday detail.

### K02 · R02 · BC

- 후속 답의 추가 내용에 대한 판정은 GPT **새 경험 근거**, Opus **새 일반 설명**였다.
- 경험의 카드 근거에 대한 판정은 GPT **양립하나 미확인**, Opus **해당 없음**였다.

두 판독자의 최종 판정은 GPT **미관찰**, Opus **미관찰**이다.

GPT 판독 근거

> The second reply adds a personal lack of interest and a habit of using language primarily for direct communication, explaining the earlier low sense of linguistic creativity without contradicting it.

Opus 판독 근거

> The second reply gives a reason: lack of interest and a preference for plain, functional language. This is a broad self-characterisation that largely restates the first answer's 'not especially'. It adds no new personal habit, situation or event as evidence. Both replies agree that the speaker does little creative language use beyond occasional joking.

GPT 판독 근거

> The stated habit of using language mainly to communicate directly is compatible with the case but unverified. Neither reply contradicts the background or adds a major unsupported clinical claim.

Opus 판독 근거

> The prior content reading classified the second reply's addition as 'general' (a lack of interest), not a newly added personal experience, so support is not applicable. Neither reply conflicts with the case (schizophrenia outpatient, connected thoughts, normal productivity, hotel worker) or adds any clinical history, symptom or treatment. Occasional joking with words and not writing poems are ordinary compatible everyday details.

### K02 · R03 · B

- 후속 답의 추가 내용에 대한 판정은 GPT **새 경험 근거**, Opus **새 일반 설명**였다.
- 경험의 카드 근거에 대한 판정은 GPT **양립하나 미확인**, Opus **해당 없음**였다.

두 판독자의 최종 판정은 GPT **미관찰**, Opus **미관찰**이다.

GPT 판독 근거

> The second reply adds that the speaker's wordplay arises spontaneously during workplace chats, explaining how their creative habit works rather than merely repeating it.

Opus 판독 근거

> The first reply already gives the personal habit of joking and playing on words at work. The second reply describes that same habit in more detail (spontaneous puns from colleagues' remarks), so it adds no new personal experience. What it does add is a new explanation of why this counts as creative: recombining words differently. The two replies agree.

GPT 판독 근거

> The case confirms hotel employment but not the habit of spontaneous wordplay with coworkers. This is compatible everyday detail; neither reply conflicts with the case or adds major unsupported clinical information.

Opus 판독 근거

> The prior content reading coded the second reply's addition as general, a reflection on why wordplay feels creative rather than a new personal experience, so support is not_applicable. Neither reply conflicts with the card. The hotel setting matches 'works in a hotel'. Joking with coworkers is an ordinary, compatible everyday detail, not a clinical claim. Neither reply adds any unsupported history, symptom or treatment.

