# 같은 길이에서 사건 세부와 반복을 구별하는가

**두 판독자가 두 번 모두 구체적 전개 1점에 합의한 경우는 세부를 추가한 버전 4/4건, 같은 내용을 반복한 버전 0/4건이었다.** 네 사례 모두 세부 추가에서만 합의했다. 점수 변화는 Opus에서 관찰됐다. GPT는 두 조건 모두에서 1점을 유지했다.

| 사례 | 기존 Opus / GPT | 삽입한 단어 수 · 두 버전 동일 | 완성 답 단어 수 · 두 버전 동일 | 세부 추가 1차 → 2차 | 반복 1차 → 2차 |
|---|---:|---:|---:|---:|---:|
| GK02 두려움 | 2/1 | 8 | 31 | 1/1 → 1/1 | 2/1 → 2/1 |
| GK05 아침 일과 | 3/1 | 10 | 25 | 1/1 → 1/1 | 3/1 → 3/1 |
| GK07 당혹감 | 2/1 | 11 | 45 | 1/1 → 1/1 | 2/1 → 2/1 |
| GK12 자부심 | 2/1 | 11 | 46 | 1/1 → 1/1 | 2/1 → 2/1 |

삽입 위치는 모두 원문의 첫 문장 직후였다. 각 쌍의 질문·원문·추가 문장 수·영어 단어 수가 일치했다. 새 세부는 연구용 가상 문장이다. 기존 발화기 출력은 그대로 보존했다. [여덟 영어 문답 전문과 회차별 판독 근거](details.md)

| 사례 | 세부 추가 문장 | 같은 길이의 반복 문장 |
|---|---|---|
| GK02 | The dog stopped just before it reached me. | I remember the dog charging right toward me. |
| GK05 | I stop grinding when the grounds look like coarse sand. | Grinding coffee by hand is part of my morning routine. |
| GK07 | I realized my mistake when the instructor announced the class name. | I realized I was in the wrong class at that studio. |
| GK12 | I’d mixed the exact shade of blue I was aiming for. | I was pleased with how the mural I painted turned out. |

GK02에서 Opus는 개가 어디까지 다가와 멈췄는지가 사건을 완결한다고 설명했다. GK05에서는 갈기를 멈추는 기준, GK07에서는 수업을 잘못 찾았음을 깨달은 계기, GK12에서는 만족한 이유가 되는 구체적 성취를 근거로 들었다. GPT도 세부 추가 답의 근거에서 새 정보를 짚었다. 반복 답에서는 이미 있던 사건·방법·감정만으로 충분하다고 설명했다. GPT의 점수만으로는 두 조작을 구별할 수 없었다.

기존 불일치가 재현된 네 답을 선별하고, Opus의 기존 근거에서 부족하다고 본 부분에 맞춰 세부를 작성했다. 이 문장들에서는 같은 분량을 더해도 어떤 내용을 보탰느냐에 따라 1점 합의가 달라졌다. 이 결과로 모든 세부 추가의 효과, 실제 환자 발화 재현도, 전문의와의 일치를 추정할 수 없다.

Opus 5.5와 GPT-6.1 Sol(medium)은 서로 다른 무작위 순서로 두 회차씩 판독했다. 매 세션에는 한 문답과 기존 루브릭만 제공했다. 32개 독립 세션의 최초 응답 모두 채점 가능했고, 의미 명료도는 모두 1점이었다. 사건별 원점수와 집계, 실제 제시 순서, 기존 문답과 점수의 해시를 검증했다. Opus의 서비스 모델 ID와 GPT의 공식 CLI 모델 설정을 확인했다. [설계](DESIGN.ko.md) · [수치 검산](analysis.json) · [기존 36쌍 결과](../card-detail-pilot/RESULTS.ko.md)
