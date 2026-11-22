# 활동 자체와 추가 세부의 경계 · 불일치 6개 원문 대조

기존 72개 합성 답 중 전개 점수가 갈린 6개를 전부 수록했다. 모두 중심 사실 카드에서 생성됐다. 점수는 Opus / GPT 순서다. 의미 명료도는 여섯 답 모두 1 / 1이었다. 아래 영문 근거는 최초 판독에서 그대로 가져왔다. 연구팀의 사후 설명은 점수에 반영하지 않았다.

## 원저의 기준

Gruber와 Kring은 사건을 말한 것 외에 추가 정보가 있는지, 그 정보로 사건 설명이 스스로 완결되는지를 보았다. 3점은 짤막하게 사건을 지칭하는 데 그치고 추가 정보가 없는 경우다. 2점은 추가 정보가 있으나 사건 전체를 이해할 중요한 세부가 빠진 경우다. 1점은 관련 정보가 하나 이상 더해지고 설명이 그 자체로 완결된 경우다. Study 2는 이 전개 코드를 가져와 정서 사건과 일상 활동을 다뤘다. 공개된 논문은 시간·장소·결과를 반드시 모두 말해야 한다는 규칙이나 손 분쇄와 식사 같은 표현의 정답을 제시하지 않는다. [원저 p. 523](https://esilab.berkeley.edu/wp-content/uploads/2017/12/Gruber-Kring-2008.pdf#page=4) · [Study 2 p. 526](https://esilab.berkeley.edu/wp-content/uploads/2017/12/Gruber-Kring-2008.pdf#page=7)

## 6개 불일치와 같은 조건에서 나온 1점 답

모든 행의 첫 번째 대조는 같은 인물·질문·생성 조건에서 나온 원래 카드 답이다. 이 여섯 대조는 모두 1 / 1이었다. 식사 두 사례에는 실제로 3 / 3을 받은 비슷한 중심 사실 답도 붙였다. 이번 72개에서 3 / 3 합의 답은 이 두 식사 응답뿐이었다.

### 1. GK05 개발판 · 아침의 손 분쇄

Can you describe what you usually do in the morning?

| 불일치 답 전문 · 중심 사실 카드 | 두 모델 모두 1점인 짝 전문 · 원래 카드 |
|---|---|
| **3 / 1** · I grind coffee by hand every morning. That’s a regular part of my morning routine. | **1 / 1** · “I grind coffee by hand each morning. I keep the beans in a blue tin, and the grinder is clamped to the kitchen counter. So when I think of my morning, that’s what comes to mind first—the blue tin, then standing at the counter turning the grinder by hand.” |

- **OPUS의 최초 근거** · The speaker names the activity of grinding coffee by hand. 'By hand' only specifies which activity it is, and the second sentence restates that it is routine. No steps, context, or other details about the activity are added.
- **GPT의 최초 근거** · The speaker specifies grinding coffee by hand, adding a method detail to a self-contained everyday activity.

‘손으로 커피를 갈기’ 전체를 활동으로 읽으면 두 번째 문장은 이미 말한 일과를 반복한다. ‘커피 갈기’를 활동으로 읽으면 ‘손으로’가 방법 하나를 보탠다. 원래 카드 답에서 원두를 보관하는 곳과 분쇄기를 고정한 곳은 어느 쪽으로 읽어도 구분되는 정보다.

### 2. GK08 개발판 · 마지막 식사와 질문의 반복

Can you tell me about the last meal you ate?

| 불일치 답 전문 · 중심 사실 카드 | 두 모델 모두 1점인 짝 전문 · 원래 카드 |
|---|---|
| **3 / 1** · I had beef tacos for lunch today. That’s the last meal I ate. | **1 / 1** · I had beef tacos for lunch today. They came in a paper tray from the food truck, with thin slices of radish over the beef. |

**3 / 3 대조 전문 · GK08 기본 모델, 같은 식사 질문·중심 사실 카드**

I had beef tacos for lunch today. That’s the main thing I remember—I don’t have much detail to add about what I was doing or thinking at the time.

- **OPUS의 최초 근거** · The speaker only identifies the meal as 'beef tacos for lunch today.' The second sentence repeats this. There are no further details, such as where they ate, who they were with, how the meal was prepared or what it was like.
- **GPT의 최초 근거** · The speaker specifies what they ate—beef tacos—and when, at lunch today.

‘오늘 점심에 먹은 소고기 타코’를 한 끼의 지칭으로 잡으면 마지막 문장은 질문을 확인한다. ‘점심’을 사건으로 잡으면 음식명과 시점이 세부로 보인다. 같은 카드·문항의 기본 모델은 음식과 시점을 똑같이 말한 뒤 더 덧붙일 내용이 없다고 했고 두 모델 모두 3점을 줬다.

### 3. GK08 단답 대조 · 마지막 식사와 기억에 관한 말

Can you tell me about the last meal you ate?

| 불일치 답 전문 · 중심 사실 카드 | 두 모델 모두 1점인 짝 전문 · 원래 카드 |
|---|---|
| **3 / 1** · I had beef tacos for lunch today. That’s mostly what I remember about it. | **1 / 1** · I had beef tacos for lunch today, in a paper tray from a food truck. There were thin slices of radish over the beef. That’s mostly what I remember. |

**3 / 3 대조 전문 · GK06 단답 대조, 같은 식사 질문·중심 사실 카드**

I had lentil soup for lunch today. That’s mostly what I remember about it.

- **OPUS의 최초 근거** · The speaker says only what the meal was and when it was eaten ('beef tacos for lunch today'). They add nothing about where, who with, how it was prepared or what it was like, and they confirm 'that's mostly what I remember about it.'
- **GPT의 최초 근거** · The meal account is self-contained, specifying beef tacos and lunch today.

추가된 마지막 문장은 어디까지 기억하는지를 설명한다. 식사 자체에 관한 서술은 첫 문장의 음식명과 시점이다. GK06 단답과는 음식명만 다르고 나머지 표현은 같은데, GPT의 기존 점수가 달랐다. 원래 카드 답에는 용기·구입처·곁들인 재료가 따로 등장한다.

### 4. GK02 단답 대조 · 개가 달려온 사건의 완결성

Can you tell me about a time when you felt afraid?

| 불일치 답 전문 · 중심 사실 카드 | 두 모델 모두 1점인 짝 전문 · 원래 카드 |
|---|---|
| **2 / 1** · I remember a dog charging toward me across a driveway. It frightened me—it all happened so quickly. That’s mostly what I remember. | **1 / 1** · I remember a dog charging toward me across a driveway. There was a low gate between us, and its broken tether was dragging behind it. It all happened so quickly—I felt really scared. |

- **OPUS의 최초 근거** · The speaker gives some detail beyond naming the event: a dog charged toward them across a driveway, and it happened quickly. Important information is missing, including the setting, when it happened, and the outcome. The speaker acknowledges this with 'That's mostly what I remember.'
- **GPT의 최초 근거** · The account describes a dog charging toward the speaker across a driveway and how quickly it happened, providing a self-contained frightening event.

‘개가 진입로를 가로질러 내게 달려왔다’로 사건을 특정한다. 순식간이었다는 말은 속도에 관한 정보다. Opus도 이 정보를 인정했지만 배경·시점·결과가 더 필요하다고 봤고, GPT는 무엇이 왜 무서웠는지가 이해된다고 봤다. 원래 카드 답은 낮은 문이 사이에 있었고 끊어진 줄이 끌렸다고 덧붙였다. 두 코더 모두 1점인 그 답조차 마지막에 무슨 일이 일어났는지는 밝히지 않는다.

### 5. GK07 단답 대조 · 잘못 들어간 수업과 직업 배경

Can you tell me about a time when you felt embarrassed?

| 불일치 답 전문 · 중심 사실 카드 | 두 모델 모두 1점인 짝 전문 · 원래 카드 |
|---|---|
| **2 / 1** · I once joined the wrong class at a dance studio. It was embarrassing when I realized. I work as a swimming pool caretaker, so being at the studio was quite a change of scene. | **1 / 1** · I once walked into the wrong class at a dance studio. There were couples practicing a waltz around me, and I was standing there with my tap shoes in a drawstring bag. I felt pretty awkward, realizing I wasn’t meant to be there. |

- **OPUS의 최초 근거** · The speaker gives the setting (a dance studio) and says the embarrassment came when they realized it was the wrong class. The remark about working as a swimming pool caretaker is background and adds little to the event itself. Important details are missing, such as how they realized the mistake and what happened next.
- **GPT의 최초 근거** · The account explains that the speaker joined the wrong class at a dance studio and felt embarrassed upon realizing the mistake.

잘못된 수업에 들어갔다는 말이 사건을 특정하고, 실수를 알았을 때 당혹스러웠다는 말이 사건과 감정을 연결한다. 수영장 관리인이라는 직업은 새 정보다. Opus는 그 정보가 실수를 어떻게 알아차렸는지 거의 설명하지 않는다고 봤고, GPT의 1점 근거는 수업·깨달음·감정의 연결이었다. 두 모델이 모두 1점을 준 짝에서는 남들은 왈츠를 추고 자신은 탭댄스 신발을 들고 있어 상황의 어긋남이 보인다.

### 6. GK12 단답 대조 · 놀이터 벽화와 자부심의 이유

Can you tell me about a time when you felt proud?

| 불일치 답 전문 · 중심 사실 카드 | 두 모델 모두 1점인 짝 전문 · 원래 카드 |
|---|---|
| **2 / 1** · I felt proud of a mural I painted for a playground. It was nice to make something for that space. I don’t remember all the details, mostly just feeling pleased with how it turned out. | **1 / 1** · I felt proud when I painted a mural for a playground—three blue whales along the wall. A kindergarten class was there for the unveiling. It felt good to have made something for them. |

- **OPUS의 최초 근거** · The speaker names the event (painting a mural for a playground) and adds some evaluative detail ('nice to make something for that space', 'pleased with how it turned out'). Important information is missing, though: what the mural showed, when or how it was made, and what made it a source of pride. The speaker also says 'I don't remember all the details.'
- **GPT의 최초 근거** · The account identifies painting a mural for a playground and explains feeling pleased with the result, providing self-contained detail beyond naming the activity.

놀이터에 벽화를 그렸다는 말이 사건을 특정한다. 그 공간을 위해 만들어 좋았고 결과가 마음에 들었다는 평가는 추가 정보다. Opus도 평가가 더해졌음을 인정했으나 자부심의 구체적 이유가 충분히 전개되지 않았다고 봤다. GPT는 결과에 만족했다는 설명으로 사건이 완결된다고 봤다. 두 판독자가 모두 1점을 준 짝은 벽화의 고래 세 마리와 공개식에 온 유치원 학급을 특정한다.

## 같은 사실을 말했는데 점수가 달라진 식사 답

아래 세 응답은 같은 식사 질문과 중심 사실 카드를 썼다. GK06에서 음식과 시점을 두 문장으로 제시한 답은 개발판과 기본 모델의 별도 세션에서 글자까지 같았고, 두 판독자는 두 답 모두 1점으로 읽었다. 같은 인물의 단답은 음식·시점을 한 문장에 담고 기억에 관한 말을 붙여 둘 다 3점이었다. GK08 단답에서는 음식명만 달라졌는데 GPT의 점수가 달랐다. 표현 분할이나 기억에 관한 말이 점수를 바꾼 원인인지는 이 비교로 결정할 수 없다.

| 인물·조건 | 답 전문 | 기존 점수 |
|---|---|---|
| GK06 개발판 | The last meal I ate was lunch today. I had lentil soup. | 1 / 1 |
| GK06 단답 대조 | I had lentil soup for lunch today. That’s mostly what I remember about it. | 3 / 3 |
| GK08 단답 대조 | I had beef tacos for lunch today. That’s mostly what I remember about it. | 3 / 1 |

1점과 3점 사이의 세 불일치는 활동의 이름을 어디까지로 정하느냐에 걸려 있다. 1점과 2점 사이의 세 불일치는 이미 확인되는 추가 정보가 설명을 완결할 만큼 관련 있고 충분한지에 걸려 있다. 원저 코더가 이 합성문을 채점한 기록은 없어 어느 모델이 원저의 사람 점수를 맞혔는지 결정할 수 없다. [36쌍의 전체 답과 근거](pairs.md) · [기존 결과](RESULTS.ko.md)
