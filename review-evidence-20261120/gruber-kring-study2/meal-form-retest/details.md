# 식사 표현별 두 회차의 구체적 전개 점수

동일한 영어 문항별 1·2회 최초 점수와 실제 제시 위치를 표시한다. 전개 점수가 높을수록 전개가 부족하다고 읽은 것이다.

| 문항 | 영어 답 전문 | Opus 점수 | Opus 순번 | GPT 점수 | GPT 순번 |
| --- | --- | --- | --- | --- | --- |
| soup-compact-0 | I had lentil soup for lunch today. | 3 → 3 | 3 → 10 | 1 → 1 | 4 → 11 |
| soup-compact-1 | I had lentil soup for lunch today. That’s mostly what I remember about it. | 3 → 2 | 5 → 9 | 1 → 3 | 2 → 5 |
| soup-dash-0 | The last meal I ate was lunch today—I had lentil soup. | 1 → 1 | 2 → 12 | 1 → 1 | 6 → 4 |
| soup-dash-1 | The last meal I ate was lunch today—I had lentil soup. That’s mostly what I remember about it. | 1 → 1 | 9 → 3 | 1 → 1 | 7 → 12 |
| soup-split-0 | The last meal I ate was lunch today. I had lentil soup. | 1 → 1 | 11 → 7 | 1 → 1 | 11 → 10 |
| soup-split-1 | The last meal I ate was lunch today. I had lentil soup. That’s mostly what I remember about it. | 1 → 1 | 7 → 6 | 1 → 1 | 8 → 7 |
| tacos-compact-0 | I had beef tacos for lunch today. | 1 → 1 | 12 → 8 | 1 → 1 | 10 → 9 |
| tacos-compact-1 | I had beef tacos for lunch today. That’s mostly what I remember about it. | 3 → 3 | 4 → 11 | 1 → 1 | 3 → 2 |
| tacos-dash-0 | The last meal I ate was lunch today—I had beef tacos. | 1 → 1 | 8 → 2 | 1 → 1 | 12 → 6 |
| tacos-dash-1 | The last meal I ate was lunch today—I had beef tacos. That’s mostly what I remember about it. | 2 → 1 | 6 → 5 | 1 → 1 | 5 → 1 |
| tacos-split-0 | The last meal I ate was lunch today. I had beef tacos. | 1 → 1 | 1 → 4 | 1 → 1 | 1 → 8 |
| tacos-split-1 | The last meal I ate was lunch today. I had beef tacos. That’s mostly what I remember about it. | 1 → 1 | 10 → 1 | 1 → 1 | 9 → 3 |

## 일치도

- OPUS 재판독 정확 일치 10/12, 미채점 쌍 0/12.
- GPT 재판독 정확 일치 11/12, 미채점 쌍 0/12.
- 1회차 모델 간 정확 일치 8/12, 미채점 쌍 0/12.
- 2회차 모델 간 정확 일치 9/12, 미채점 쌍 0/12.

## 한 요소만 바꾼 비교

음식은 수프에서 타코, 문장 분할은 같은 단어의 대시 연결에서 두 문장, 기억 문구는 미포함에서 포함으로 바꾼 방향이다. 각 회차의 유지·상승·하락은 그 회차의 비교값이다. 두 회차 요약에서 혼합은 회차 간 방향이 달랐거나 한 회차에서만 변화한 경우다.

| 판독자 | 요인 | 1회 유지/상승/하락 · 유효/계획 | 2회 유지/상승/하락 · 유효/계획 | 양회 유지 | 양회 상승 | 양회 하락 | 혼합 | 양회 유효/계획 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OPUS | 음식명 | 4 / 1 / 1 · 6/6 | 4 / 1 / 1 · 6/6 | 3 | 0 | 1 | 2 | 6/6 |
| OPUS | 문장 분할 | 3 / 0 / 1 · 4/4 | 4 / 0 / 0 · 4/4 | 3 | 0 | 0 | 1 | 4/4 |
| OPUS | 기억 문구 | 4 / 2 / 0 · 6/6 | 4 / 1 / 1 · 6/6 | 3 | 1 | 0 | 2 | 6/6 |
| GPT | 음식명 | 6 / 0 / 0 · 6/6 | 5 / 0 / 1 · 6/6 | 5 | 0 | 0 | 1 | 6/6 |
| GPT | 문장 분할 | 4 / 0 / 0 · 4/4 | 4 / 0 / 0 · 4/4 | 4 | 0 | 0 | 0 | 4/4 |
| GPT | 기억 문구 | 6 / 0 / 0 · 6/6 | 5 / 1 / 0 · 6/6 | 5 | 0 | 0 | 1 | 6/6 |

## 개별 비교쌍

| 판독자 | 요인 | 변경 전 | 변경 후 | 1회 | 2회 |
| --- | --- | --- | --- | --- | --- |
| OPUS | 음식명 | soup-compact-0 | tacos-compact-0 | 3 → 1 | 3 → 1 |
| OPUS | 음식명 | soup-compact-1 | tacos-compact-1 | 3 → 3 | 2 → 3 |
| OPUS | 음식명 | soup-dash-0 | tacos-dash-0 | 1 → 1 | 1 → 1 |
| OPUS | 음식명 | soup-dash-1 | tacos-dash-1 | 1 → 2 | 1 → 1 |
| OPUS | 음식명 | soup-split-0 | tacos-split-0 | 1 → 1 | 1 → 1 |
| OPUS | 음식명 | soup-split-1 | tacos-split-1 | 1 → 1 | 1 → 1 |
| OPUS | 문장 분할 | soup-dash-0 | soup-split-0 | 1 → 1 | 1 → 1 |
| OPUS | 문장 분할 | soup-dash-1 | soup-split-1 | 1 → 1 | 1 → 1 |
| OPUS | 문장 분할 | tacos-dash-0 | tacos-split-0 | 1 → 1 | 1 → 1 |
| OPUS | 문장 분할 | tacos-dash-1 | tacos-split-1 | 2 → 1 | 1 → 1 |
| OPUS | 기억 문구 | soup-compact-0 | soup-compact-1 | 3 → 3 | 3 → 2 |
| OPUS | 기억 문구 | soup-dash-0 | soup-dash-1 | 1 → 1 | 1 → 1 |
| OPUS | 기억 문구 | soup-split-0 | soup-split-1 | 1 → 1 | 1 → 1 |
| OPUS | 기억 문구 | tacos-compact-0 | tacos-compact-1 | 1 → 3 | 1 → 3 |
| OPUS | 기억 문구 | tacos-dash-0 | tacos-dash-1 | 1 → 2 | 1 → 1 |
| OPUS | 기억 문구 | tacos-split-0 | tacos-split-1 | 1 → 1 | 1 → 1 |
| GPT | 음식명 | soup-compact-0 | tacos-compact-0 | 1 → 1 | 1 → 1 |
| GPT | 음식명 | soup-compact-1 | tacos-compact-1 | 1 → 1 | 3 → 1 |
| GPT | 음식명 | soup-dash-0 | tacos-dash-0 | 1 → 1 | 1 → 1 |
| GPT | 음식명 | soup-dash-1 | tacos-dash-1 | 1 → 1 | 1 → 1 |
| GPT | 음식명 | soup-split-0 | tacos-split-0 | 1 → 1 | 1 → 1 |
| GPT | 음식명 | soup-split-1 | tacos-split-1 | 1 → 1 | 1 → 1 |
| GPT | 문장 분할 | soup-dash-0 | soup-split-0 | 1 → 1 | 1 → 1 |
| GPT | 문장 분할 | soup-dash-1 | soup-split-1 | 1 → 1 | 1 → 1 |
| GPT | 문장 분할 | tacos-dash-0 | tacos-split-0 | 1 → 1 | 1 → 1 |
| GPT | 문장 분할 | tacos-dash-1 | tacos-split-1 | 1 → 1 | 1 → 1 |
| GPT | 기억 문구 | soup-compact-0 | soup-compact-1 | 1 → 1 | 1 → 3 |
| GPT | 기억 문구 | soup-dash-0 | soup-dash-1 | 1 → 1 | 1 → 1 |
| GPT | 기억 문구 | soup-split-0 | soup-split-1 | 1 → 1 | 1 → 1 |
| GPT | 기억 문구 | tacos-compact-0 | tacos-compact-1 | 1 → 1 | 1 → 1 |
| GPT | 기억 문구 | tacos-dash-0 | tacos-dash-1 | 1 → 1 | 1 → 1 |
| GPT | 기억 문구 | tacos-split-0 | tacos-split-1 | 1 → 1 | 1 → 1 |
