# Gruber–Kring 경계 예제 판독 결과

2026-11-21 KST. Opus와 GPT는 비임상 영어 예제 세 쌍에서 사전에 정한 변화를 모두 포착했다. 같은 식사 정보를 반복한 답에서는 두 점수가 모두 유지됐고, 길이가 같은 경주 답에 맥락을 보태자 전개 점수만 개선됐다. 길 안내에서 지명을 불명확하게 바꾸자 명료도와 전개가 모두 나빠졌다. 두 척도는 구별해서 읽을 수 있지만 한 표현이 양쪽 점수에 영향을 줄 수 있다. [고정 설계 §3·5](../DESIGN.ko.md) · [판독 전 기대 관계](expectations.json)

## 예제별 최초 점수

괄호 안은 **(구체적 전개, 의미 명료도)** 순서다. 두 척도 모두 1이 가장 양호하고 3이 가장 어렵다. 팀 연구용으로 작성한 영어 예문이며 공개 환자 전사나 발화기 출력은 사용하지 않았다. 단어 수는 응답에서만 셌다. [독립 입력 6개](examples.json)

| 질문·조건 | 영어 답변 | 단어 수 | Opus | GPT |
|---|---|---:|---|---|
| 마지막 식사 · 짧은 답 | Tomato soup. | 2 | (3, 1) | (3, 1) |
| 마지막 식사 · 같은 사실 반복 | What I had for my last meal was tomato soup. Yes, tomato soup was what I ate. | 17 | (3, 1) | (3, 1) |
| 자부심 · 완주 사실 반복 | I finished the race and felt proud when it was over. Finishing it was the part I was proud of. | 20 | (3, 1) | (3, 1) |
| 자부심 · 맥락 추가 | I felt proud finishing my first race after weeks of practice. My little brother cheered for me at the finish. | 20 | (1, 1) | (1, 1) |
| 길 안내 · 식별 가능한 지명 | From my house, drive north and turn left at the bakery. When the road forks, take the branch toward the clock tower. The library entrance is on the right just beyond the tower, directly across from the pharmacy. | 38 | (1, 1) | (1, 1) |
| 길 안내 · 불명확한 지시어 | From my house, drive north and turn left at that place. When the road forks, take the branch toward that other thing. Its entrance is on the right just beyond that thing, directly across from the other one. | 38 | (2, 3) | (2, 3) |

## 사전 판정과 근거

| 사전 점검 | 기대 관계 | Opus | GPT |
|---|---|---|---|
| 사실을 유지하고 길이만 늘림 | 전개 동일, 명료도 동일 | 두 관계 충족 | 두 관계 충족 |
| 같은 길이에서 중요한 세부를 더함 | 전개 점수 감소 | 3 → 1 | 3 → 1 |
| 같은 경로에서 지시대상을 흐림 | 명료도 점수 증가 | 1 → 3 | 1 → 3 |

두 판독자는 식사 답에서 “tomato soup”의 반복을 추가 정보로 세지 않았다. 경주 답에서는 수 주의 연습과 결승선에서 동생이 응원한 일이 완주에 맥락을 더한다고 판단했다. 두 답 모두 무엇 때문에 자부심을 느꼈는지 알아볼 수 있어 명료도는 1점을 유지했다.

길 안내에서는 두 판독자 모두 방향·갈림길·입구의 위치가 남아 있다고 읽었다. 다만 “that place”와 “that other thing”이 어느 장소인지 알 수 없어 실제 경로를 따라가기 어려웠다. 두 판독자 모두 이 표현을 **의미를 복원하기 어렵게 하는 지시 불명확성**과 **경로를 완결하는 데 필요한 정보의 누락**으로 각각 설명했다. 전개 1 → 2의 동반 변화는 사전 통과 조건 밖의 관찰이다. 이 사례에서 두 점수를 독립적인 검증 결과 두 건으로 해석하면 근거를 중복 계산하게 된다. [Opus의 해당 답 판독](opus/forms/K94.json) · [GPT의 해당 답 판독](gpt/forms/K94.json)

## 일치도와 해석 범위

두 판독자 모두 여섯 답을 각각 하나의 활동으로 채점했다. 판독 가능 여부 불일치 0건, 항목별 정확 일치는 전개 6/6, 명료도 6/6이다. 아래 칸은 Opus 점수(행)와 GPT 점수(열)의 교차 빈도다. [검증된 집계](summary.json)

| Opus 점수 | 전개 GPT 1 | GPT 2 | GPT 3 | 명료도 GPT 1 | GPT 2 | GPT 3 |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 2 | 0 | 0 | 5 | 0 | 0 |
| 2 | 0 | 1 | 0 | 0 | 0 | 0 |
| 3 | 0 | 0 | 3 | 0 | 0 | 1 |

고정한 규칙상 두 판독자 모두 두 항목의 사전 점검을 통과했다. 명료도 2점은 한 번도 관찰되지 않았고 전개 2점도 한 예에 그쳤다. 여섯 문장은 의도적으로 대조를 크게 만든 예이고 판독자별로 한 번씩만 평가했다. 이 결과로 미묘한 1·2·3점 경계, 동일 판독자의 재검사 일관성, 자연 발화에서의 일치도, 사람 채점과의 일치도, 실제 환자군에 대한 발화기 재현도까지 추정할 수 없다. 이 점검은 본실험 전 판독 절차에 관한 근거다. 360개 발화기 본실험 실행 건수는 0건이다.

## 확인 기록

기존 설계, 운영 채점표, 예문, 기대 관계, 제출 순서, 호출 코드의 SHA-256을 첫 판독 전 기록했다. 각 판독자는 독립 세션 6개에서 같은 영어 채점표와 한 문답만 받았다. 짝, 기대값, 상대 판독, 목표 집단 평균은 입력에서 제외했다. 12개 첫 응답의 원본 해시, 전송 내용 해시, 서로 다른 판독 세션, 도구 호출 0건을 확인했다. Opus의 실제 응답 모델 표시는 6건 모두 `claude-opus-5-5`였다. GPT는 공식 CLI의 실행 모델 표시가 6건 모두 `gpt-6.1-sol`이었으며, 수집한 로그에 별도 서버 응답 모델 ID는 없었다. [동결 해시](freeze.json) · [판독 코드](calibrate.py) · [로컬 검증 및 집계 코드](summarize.py)
