# M22 독립 설계의 구성타당도·원목적 부합 검토 — 최초 요청

## 사용자의 목적과 질문 (이 내용만 이전 대화에서 전달)
사용자는 한국 의대생 연구자로 '조현병 환자의 사고·의사소통 특성이 텍스트에서 어떻게 드러나는지, 이를 LLM으로 재현하고 분석할 수 있는가'를 연구하고 싶다. 단순한 현실성 점수 경쟁이나 병명 라벨 반응 연구로 목표를 바꾸고 싶어 하지 않는다. 실제 환자 전사·전문의 판독은 확보되지 않았고 TOPSY 없이 3주 안에 포스터를 마칠 현실적 설계를 찾고 있다.
현재 사용자의 요청: '이 설계를 Claude에게 별도 문맥에서 검토받아줘. 특히 이전 면담 이력에 따른 반응을 보는 것이 실제 조현병의 사고·의사소통 특성 재현과 얼마나 연결되는지, 단순한 지시 수행을 넘어서는 연구적 의미가 있는지 논의해줘.'
이 대화는 새 전략 멘토 문맥이다. 이전 Claude 판독/멘토 응답이나 전체 실험 이력은 제공하지 않는다. 설계자의 모델 이름도 판단의 근거가 아니다. 이 계획은 미실행이며 이번은 설계 검토다.

## 제약과 확인 범위
- 기존 공식 GPT/Claude 구독 CLI만 사용. 새 유료 API/모델/패키지/원자료 접근 신청/외부 인력 연락 없음.
- 실제 환자나 전문의 타당도 없음. 새 실험 발화와 평정 아직 없음. 기존 12사례/720계획은 별도 보존·미사용.
- 환자 연구의 공개 요약통계·정의와 새로운 합성 자극만 필수 근거다. 이전 면담 재진술 도움을 PANSS 개념적 와해와 동등하게 본 실증은 제공되지 않았다.
- 현 설계의 E는 원논문보다 좁은 확정 장면 모순, V는 원논문 합성 표준점수와 다른 표현밀도다.
- 두 모델의 동일 이미지 CLI 전달은 미확인. 실행 의존성이지만 이번 검토의 우선은 기술 구현이 아닌 원목적·임상 연결이다.

## 답해야 할 핵심
1. 문헌의 '임상적으로 평정한 개념적 와해 ↔ 언어지표'와 실험의 '이전 면담 지원 이력 → 합성 담화' 사이 연결 고리를 단계별로 분해하라. 근거가 있는 고리, 임의의 대리변수/점프, 미검증 가정을 구분하라. 소음 조건이 해결하는 것/해결하지 못하는 것을 설명하라.
2. 결과 두 방향을 생성기에 직접 지시하지 않으면 단순 지시 수행을 넘었다고 할 수 있는가? 잠재적 재현, 의미적 프라이밍/페르소나 일반화, 고정관념 활성화, 과제 오류로 같은 결과를 설명할 수 있는가? 양성/음성/혼합 결과가 각각 원목적에 주는 정보와 식별 불가능성을 설명하라.
3. 질환 특이성이 반드시 필요한가, 기전 재현 없이도 표현형 재현 연구는 가능한가? 그렇다면 이번 설계가 최소한 확보해야 할 준거는 무엇인가? '실제 환자 기전까지 알아야만 연구가능'이라는 과도한 요구도 검토하라.
4. 이 연구가 사용자에게 설명 가능한 한 문장 목적을 갖는가? 원목적에 충분/부분/부족 중 판단을 이유와 함께 내리고, 현안 진행·실질 수정·중단 중 하나를 권고하라. 기술적 깔끔함이나 노력 투입을 연구 의미로 대체하지 말라.
5. 실질 수정이 필요하면 3주·환자 전사 미확보 조건 안에서 원목적과 더 직접 연결되는 한 가지 대안을 제시하라. 프롬프트에 특징을 명시하는 일이 모든 연구에서 순환논증인지, 개발용 조절변수와 독립 평가 준거를 나누면 무엇을 검증할 수 있는지도 따져라. 대안은 근거 확보 상태와 남은 검증 한계를 명시하고, 현실적으로 원목적을 달성 못 하면 솔직히 말하라. 새 미확인 문헌/데이터 확보를 이미 된 사실로 쓰지 말라.
6. 연구가 의미 있으려면 꼭 확인해야 할 1~2개 결정적 질문과 과도하게 약한 주장/과도하게 강한 주장의 예를 제시하라.

결론 먼저, 이어 주요 논증·제안. 설계를 칭찬하는 서론 없이 답하라. 수치 평정은 요청하지 않는다. 약 1800~2500 한국어 어절 이내로 핵심 중심으로 답하라.

--- 검토 대상 설계 전체 ---
# 조현병의 담화 특성을 LLM에서 어디까지 재현할 수 있을까

**검토 대상 독립 설계안 · 2026-11-19 · 설계만 완료**

**추천 제목** 〈이전 면담에서 주제 유지가 어려웠던 가상 화자는 새 그림 이야기를 어떻게 말하는가? 조현병 환자 연구에서 도출한 두 담화 특징의 LLM 전이 실험〉

환자 역을 맡은 모델에 틀린 이야기를 하라고 하면 그림과 다른 말이 늘 수 있다. 내가 알고 싶은 것은 그보다 어렵다. **이전 면담에서 대화의 목적을 유지하는 데 외부 도움이 필요했다는 사실만 주었을 때, 처음 보는 그림을 설명하는 방식에서도 환자 연구에 보고된 두 가지 변화가 함께 나타날까?** 첫째는 그림과 충돌하는 사건 기술의 증가, 둘째는 인물·사건에 대한 평가 및 정서 표현의 감소다. 둘째 특징은 “와해되면 말이 엉뚱하고 감정적일 것”이라는 손쉬운 연기와도 어긋날 수 있다. 각각 다른 방향으로 움직일 가능성 자체가 연구 질문이다.

이 설계에서 재현의 단위는 **한 임상 연구에서 관찰된 두 연관의 방향**이다. 실제 환자는 면담에서 개념적 와해를 평가받았고 합성 화자에는 연구자가 만든 과거 관찰이 주어진다. 이 둘은 같은 측정이 아니다. 두 방향이 모두 맞아도 제시된 이력에 조건부인 언어 생성의 증거다. 그 차이를 지키면 3주 안에도 원래 목적의 한 부분에 답할 수 있다.

## 환자 자료에서 출발한 이유

Zimmerer 등은 영어 모어 화자들이 거의 글자가 없는 여덟 컷 만화 한 편을 보고 들려준 이야기를 분석했다. 95명 중 이번 질문과 관련된 집단은 영국의 조현병 환자 30명과 해당 연령대 대조군 15명이다. 환자 내에서 PANSS 개념적 와해 문항이 높을수록 이야기를 잘못 기술하는 비율이 높았고(Spearman ρ = .51, p = .003), 평가·정서 표현 복합지표는 낮았다(ρ = −.61, p < .001). 저자가 공개한 분석 출력에도 같은 ρ가 기록됐고 FDR 보정 p는 각각 .0258, .00462였다. 오기술의 미보정 p는 본문(.003)과 저장소 출력(.00387)의 마지막 자릿수가 다르다. 저자들은 여러 사후 상관을 살폈으므로 탐색 분석이라고 명시했다. 두 상관은 각 지표와 임상 문항 사이의 연관이다. 두 언어 지표가 환자 개인에서 반드시 짝지어 나타난다는 결과가 아니다. 평균 유병기간은 약 18년이었고, 같은 그림만 사용했다. 실어증 집단에서도 잘못된 사건 기술이 관찰되었다. 이 현상의 질환 특이성, 대표성, 두 상관의 독립 재현은 확보하지 못했다. [Zimmerer 등, Cortex, 2026, §2–3 및 Table 3](https://discovery.ucl.ac.uk/id/eprint/10219274/1/Zimmerer_1-s2.0-S0010945225003193-main.pdf)

공개 OSF에서 참여자별 **파생지표** CSV의 헤더와 분석 코드의 변수 정의를 실제로 확인했다. 개념적 와해 문항, 발화량, 명제 수, 오기술 비율, 질적 평가와 정서표현 비율이 있다. 연구자가 재현 모델을 훈련할 환자 전사는 이 CSV에 없다. OSF 프로젝트에 별도 데이터 라이선스가 표시되지 않았고, 논문은 일부 자료가 제한된다고 밝힌다. 필수 임상 근거는 CC BY 4.0 원문에 이미 발표된 집단 규모, 수치, 지표 정의다. 이 경로는 개인별 파일의 재분석이나 환자 발화 외부 전송 없이 성립한다. [저자 저장소](https://osf.io/6p5wu/) · [공개 파일 색인](https://api.osf.io/v2/nodes/6p5wu/files/osfstorage/)

## 다른 질문들과 비교해 선택한 이유

- **청자 지식에 따른 설명 조절.** Achim 등의 실제 협동 식별과제에서는 청자가 모를 듯한 영화 인물을 설명할 때 대조군의 추가 정보량이 늘었고 발병 초기 스펙트럼군에서 변화 폭이 작았다. 청자가 가진 정보를 조작할 수 있어 의미 있는 후보였다. 그러나 환자군의 마음이론 검사와 정보량 조절의 연관은 입증되지 않았고, 다른 지시표현 지표에는 양군이 모두 반응했다. 모델에서 청자 지식을 지워서 적응이 줄어드는 결과만 얻으면 사회인지 과제의 정보가용성에 관한 설명이 남는다. [Achim 등, 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC9500190/) · [지시표현 후속 연구](https://libra.unine.ch/server/api/core/bitstreams/fd9e6c0c-a041-45fa-9c11-5aefa00061e1/content)
- **담화 목표 유지 또는 인물 역할 혼동.** 구조화 질문 대 자유 질문, 이야기 속 행위자 회상 오류에는 직접적인 환자 실험이 있다. 다만 문맥을 제거해 목표를 잃게 하거나 행위자 정보를 약화해 행위자를 틀리게 만드는 강제 조작과 환자 양상의 연결은 약하다. 기억 지연과 모델 입력 절단도 서로 다른 조작이다. 본 계획은 입력의 장면 정보를 온전히 유지한다. [Barch·Berenbaum, 1997](https://pubmed.ncbi.nlm.nih.gov/9255856/) · [Hoffman 등, 2011](https://pmc.ncbi.nlm.nih.gov/articles/PMC3105006/)
- **지시 명사구 분포.** Çokal 등의 수작업 주석과 LLM 추출 연구는 구체적인 영어 언어형식을 제공한다. 그러나 2026 논문은 앞선 환자 자료를 다시 사용했고, FTD가 높고 낮은 환자끼리의 차이가 모든 분석에서 확인된 것은 아니다. 한국어 적용 시에는 관사·생략 체계가 다르다. 단일 영어 명사구의 분류 정확도를 높이는 일보다 이번에는 수작업으로 원장면을 대조할 수 있는 사건 기술과 서술자의 평가를 선택했다. [2018 수작업 연구](https://www.nature.com/articles/s41537-018-0061-9.pdf) · [2026 재분석](https://doi.org/10.1016/j.neuropsychologia.2026.109505)
- **기존의 임상의 평정 합성 서사를 그대로 이용.** Fradkin 등의 연구는 GPT-2 조작과 합성 서사 249개에 대한 임상의 2인의 판독이 있는 좋은 방법론 선례다. 공개 색인에서 생성 코드와 결과 파일을 확인했지만 개별 원평정과 서사의 결합 자료·사용권까지 확인한 것은 아니다. 그 자료가 있어도 새 화자가 보이는 현상을 환자 연구와 잇는 문제는 남는다. [Fradkin 등, 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC11932972/) · [OSF 결과 목록](https://api.osf.io/v2/nodes/xhefa/files/osfstorage/637760404e8c3c08703b4b7f/)

## 실험 조건

모든 합성 화자에 **같은 조현병 외래 진료 배경**을 주며, 병명은 고정한다. 현재 기분, 협조 의사, 시각·청각, 교육·언어 배경, 자료량과 현재 과제 설명도 같게 한다. 조건 간 차이는 과거의 별도 대화에 대한 **관찰 기록 한 단락**이다. 이력은 표적 장면을 본 적이 없는 화자의 과거 행동으로 그려진다.

1. **주제 유지 지원 이력(D)**. 이전 일상 면담에서 두 차례 현재 의제를 다시 짚어 주어야 진행 중이던 사안으로 돌아왔다. 두 사안의 내용이나 당사자의 실제 발화는 제공하지 않는다. 청각·기분·말수·사실 판단에 관한 새로운 속성을 부여하지 않는다.
2. **상황성 중단 이력(I)**. 같은 과거 면담에서 두 번의 일시적 외부 소음으로 면담자가 현재 의제를 다시 짚고 당사자가 재개했다. D와 호명·개입 횟수와 과거 상황의 세부량을 맞춘다. 현재 그림과제는 세 조건 모두 조용한 환경이다.
3. **조직적 이력(O)**. 같은 의제 두 개를 외부의 되짚기 없이 마쳤다. 다른 두 조건과 관찰된 시간, 목표, 완료 결과를 맞춘다.

기록은 각 조건당 두 가지 평행 문안으로 만들고 같은 A/B 문안군에서 세 조건의 분량·인칭·말투·임상 정보량을 맞춘다. 출력 관련 지시, 그림 속 실수, 정확도, 감정·평가 어휘, 무미건조함, 말수, 모델에게 보일 환자 인용문, PANSS 점수, 연구명, 기대 방향은 넣지 않는다. 일반 실험 지시는 눈앞의 연속 장면을 다른 사람에게 자기 말로 이야기하라는 내용으로 통일한다. 이번 설계는 실제 프롬프트를 작성하지 않았다.

이력 D는 와해 시 나타날 수 있는 관찰 하나다. 주의 분산·피로·면담자 행동으로도 발생할 수 있고 와해 중증도를 확정하지 못한다. I는 개입 횟수가 결과를 만드는 설명을 줄이고 O는 기본 수행을 보여준다. 조건을 고른 연구자의 시각이나 모델의 정신질환 고정관념은 이 두 통제로 사라지지 않는다. D와 I에 비해 O만 다르면 가장 직접적인 해석은 이전 면담 중단 여부에 대한 반응이다.

## 과제, 단위, 실행 규모

**영어**로 생성한다. 환자 원연구와 같은 언어에서 평가적 표현을 읽기 위한 선택이다. 최종 포스터 본문은 한국어로 쓸 수 있다. 기존 한국어 환자 면담 v0.2는 한국어 단일 답변과 엄격한 사실 제약을 명시한다. 별도 실행 승인 후 **이 실험 전용 영어 과제 파일**을 만들며 원본을 고치거나 v0.2 성능으로 집계하지 않는다. 재사용할 부분은 자료 분리, CLI 기록, 새 세션, 해시, 원문 보존이다.

- 연구팀이 새로 그린 **무언 6컷 일상 서사 10편** 중 개발 2편, 최종 8편. 각각 서로 구분되는 인물 둘 이상, 확인 가능한 행위자·대상·결과, 평가나 감정 해석이 자연스러운 사건 둘 이상을 둔다. 관찰 사실 6개 및 관계가 배타적인 행위자·대상 쌍, 합리적인 복수 해석과 시각적으로 확정할 수 없는 추론을 그림마다 미리 목록화한다. 합성 자극에 환자 이야기·원 논문의 만화나 도안을 쓰지 않는다.
- 장면은 모두 한 번에 보이고 자유롭게 서술한다. 모델이 볼 이미지에 정답·감정 낱말·대사·임상 단서·사건 ID를 쓰지 않는다. 코드북은 별도 보관한다. 독립적으로 그린 사건군을 쓰고 동일한 장면의 배경색만 바꾼 버전으로 8편을 채우지 않는다. 원연구의 한 여덟 컷 만화, 사람과의 구술, 면담자 격려를 그대로 반복하는 연구는 아니다.
- 최종 **8편 × 3이력 × 2평행 문안 × 2생성기 = 96개**. GPT-6.1 Sol high 및 Claude Opus 5.5 공식 구독 CLI 각 48개, 모든 셀에서 최초 생성 1회. 문안 반복은 어휘 표현 견고성 점검이며 무작위 생성 반복 분산 추정은 범위 밖이다. 연구에서 제공한 정보의 누수는 막을 수 있으나 사전학습에서 공개 논문을 봤는지는 알 수 없다. 실행 폴더에는 생성에 사용할 해당 장면과 해당 이력만 두고 외부 검색, 다른 실험 결과, 코드북과 출처 문서에 접근시키지 않는다. 장면–모델 내 6실행을 사전 고정 시드로 섞고 모델 실행 순서를 장면별 교대한다. 동등한 새 세션·허용된 이미지 입력·도구 제한·출력상한, 정확한 버전·시각·호출옵션·해시를 기록한다. 불투명한 온도나 seed는 미제공으로 남긴다.
- 동일 과제를 받은 출력, 명제, 모델 호출을 환자 표본으로 세지 않는다. 설계에서 의미 있는 독립적 내용 변이는 **새 사건 8편**이다. 여덟 편은 정밀한 검정력이 산출된 수가 아니며 두 모델·두 문안·세 조건을 전부 교차하고 한 연구자가 전수 코딩할 수 있는 작업 상한이다.

## 두 결과를 어떻게 읽을 것인가

외부 증례나 진단평정 없이도 **여기서 그린 장면의 사실**과 **텍스트에 실제로 쓰인 표현**은 조사할 수 있다. 주판독자는 영어를 읽는 연구자 1명이다. 문안/조건/생성기를 벗겨 무작위 ID를 부여한 원출력과 원장면만 보고, 조건을 열기 전에 근거가 되는 최소 원문 범위와 장면 번호를 저장한다. 문체로 조건을 추측할 가능성은 남는다. 중복 평정과 자동 집계 규칙은 인계 문서에 있다.

**E · 그림과 명백히 충돌하는 사건 기술.** 이야기의 각 최소 술어–논항 단위를 하나의 명제로 나눈다. 연결된 독립 행위 둘은 둘로, 같은 행위의 수식어는 하나의 명제로 센다. 주지표는 ‘확정적 장면 모순 명제 수 / 모든 장면 서사 명제 수’다. 분자에는 누가 무엇을 옮겼는지, 어느 물건이 어디에 있었는지 등 그림이 명시적으로 반증하는 단언만 넣는다. 예컨대 빨강 옷 인물만 상자를 건네는 장면에서 파랑 옷 인물이 건넸다고 말하면 해당한다. 어느 쪽인지 알아보기 어렵거나 “도우려 했나 보다”처럼 가능한 동기를 덧붙이면 해당하지 않는다. 앞선 일상 면담을 말하는 메타 발언은 별도 이탈 건수로 기록하고 분모에서 제외한다. 장면 서사에 속하는 추론·반복도 분모에 포함하며 누락된 사건은 분자에 넣지 않는다. 원연구의 ‘틀리거나, 이상하거나, 관련 없는’ 오기술보다 좁은 조작이다. **환자에서 명백한 모순만 증가했다는 실증은 없다.**

**V · 평가·정서 표현의 밀도.** 주지표는 ‘인물·상황에 대한 정성적 판단 또는 감정상태를 표현한 최소 의미구 수 / 장면 서사 단어 수 × 100’이다. 같은 구가 둘 다에 속하면 총 지표에는 한 번, 하위 유형에는 중복 표시한다. 눈에 보이는 색이나 이동과 “난처해 보인다”를 구별하고, 단순한 추정 표시(“아마”), 인사말, 장면 밖 자기평가는 제외한다. 직접 인용 속 정서 서술은 장면 속 인물에 관한 것이면 포함하고 근거를 표시한다. 반복하면 새 위치별로 센다. 원연구는 질적·정서 표현을 각각 단어 수로 나눠 표준화한 다음 평균했다. 여기서는 100단어당 비중복 표현 수와 두 하위 밀도를 제시한다. 임상 원점수·상관 크기와 수치 동등성을 주장하지 않는다. 영어 토큰은 알파벳 연속 및 내부 아포스트로피를 한 단어로 세고, 숫자 표기는 1단어, 하이픈 양쪽은 따로 센다.

**판단이 헷갈릴 때.** 단순 누락, 합리적 보충, 그림이 정해주지 않는 해석, 확정 모순, 맥락 외 발언을 구별한다. 애매한 모순 후보는 따로 표시하여 분자에 포함/제외했을 때를 함께 제시한다. 평가 표현의 경계가 모호하면 주 분석에서 확실건만 세고 포함 민감도를 낸다. 무반응/거절/질문만 있는 출력은 원문과 발생률을 보존하며 지표를 0으로 채우지 않는다. 그림에 대해 내용 있는 단언을 하지 않은 응답은 “오류 없는 이야기”로 분류할 수 없다.

## 비교, 반증, 해석

두 주예측은 D에서 I 대비 E가 높고 V가 낮다는 것이다. O에 대해서도 같은 방향을 기대한다. I와 O 차이에 평등성 가정을 두지 않는다. ρ의 크기를 맞추거나 두 지표를 합친 새 임상 총점을 만들 근거는 없다.

1. 각 사건·모델·이력에 문안 둘의 출력별 비율을 동등 가중 평균한다. 각 사건·모델에서 D−I와 D−O의 E, V 차이를 구하고, I−O도 공개한다. 두 모델을 각각 보고한다. 두 문안을 먼저 섞어서 가린 반전 여부는 문안별 재계산으로 보여준다.
2. 모델별로 8개 사건의 차이를 전부 표시하고 평균·중앙값·범위, 각 방향의 사건 수(동률 별도)를 보고한다. 한 사건씩 뺐을 때의 평균 범위도 낸다. 8개는 임의추출한 모집단이 아니다. 조건 효과의 주된 보고는 이 8개 고정 자극 안에서의 관찰이며 환자 모집단 p값은 없다.
3. **두 특징 모두 방향 일치**는 두 생성기 각각에서 평균 E 및 V의 D−I와 D−O가 모두 예측 방향일 때만 사용하는 기술적 문구다. 모델·문안·사건별 반전과 한 사건 제거 시의 반전도 바로 옆에 표시한다. 미세한 평균 부호만 맞으면 “약하고 불안정한 방향 일치”로 기재한다. 효과의 크기 범위·임상적 의미나 등가성을 부여하지 않는다. 한 축만 맞으면 부분 일치, I도 D와 함께 이동하거나 모델 간 방향이 다르면 각각 그대로 보고한다. 두 축 모두 바닥이라면 이 과제로 현상을 검출하지 못했다.
4. 기계적으로 산출한 단어 수, 서사 명제 수, 예정된 사실 6개의 커버리지, 역할 이탈·문법 붕괴·정신증 상투어로 인한 극단치를 공개한다. E의 보조분석은 **원래 예정한 6사실 중 모순되게 기술된 사실 수/6**, V의 보조분석은 명제 10개당 평가구 수 및 질적/정서 하위 밀도다. 분모 축소·전반적 침묵·장황한 자기설명 하나에서 시작된 효과인지 점검한다. 길이는 조건의 결과일 수도 있으므로 단순 회귀로 제거한 값을 주결과로 바꾸지 않는다.
5. 기술 실패 셀은 미리 정한 한도 안에서만 재시도한다. 의미상 실패는 재생성하지 않는다. 기술 결측 또는 장면 서사 분모 0인 셀을 가진 사건은 해당 모델·비교의 완전쌍 분석에서 따로 표시한다. 주 방향은 양쪽 문안과 세 조건이 모두 코딩 가능한 사건으로만 요약하고 사건 수/원래 8을 병기한다. 누락 시 전체 설계의 ‘두 특징 모두 방향 일치’ 판정을 보류하고 관찰 가능한 완전 사례의 방향만 말한다.
6. 기존 663발화/108대화는 개발 이력, 기존 판독의 천장과 파서 문제는 개별 현상으로 옮긴 이유다. 새 연구의 효과나 판독 신뢰도에 합산하지 않는다. 임상의 평정이 있으면 이력이 와해의 어떤 부분을 대표하는지, 생성물이 과장됐는지 나중에 평가할 수 있다. 지금 확보된 전문의 평가, 같은 과제의 실제 환자 분포, 외부 타당도는 없다.

**내 판단.** 이 연구의 가치는 환자처럼 보이는 예문을 만들어 보여주는 데 있지 않다. 환자 자료에서 먼저 관찰한 두 가지 예측을 공개하고, 그 예측을 모르는 생성 과제에서 모델이 어디까지 따라가며 어디서 어긋나는지 관찰하는 데 있다. 3주 안에 그 정도의 포스터에는 투자할 만하다. 반면 대회가 실제 환자와 합성 언어의 교환 가능성이나 임상적으로 검증된 환자 모형을 요구한다면 이 설계로는 그 결론까지 갈 수 없다.


--- 실제 원논문 발췌 (로컬 보존 PDF에서 pdftotext 추출; 저자 기술과 제안을 혼동하지 말 것) ---
원문: https://discovery.ucl.ac.uk/id/eprint/10219274/1/Zimmerer_1-s2.0-S0010945225003193-main.pdf
DOI: 10.1016/j.cortex.2025.12.006
Methods와§3.4 주변 문맥 (단 편집절단 경계 표시):
                                                                          eight black-and-white pictures. The pictures include various
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
analysis concepts used in previous literature such as Main

Fig. 1 — Differences between PwA and PwS in microstructure variables; z-scores represent normalized values for each group
relative to the respective control group. The line at zero represents the respective control mean. * denotes p < .05; ** denotes
p < .01; *** denotes p < .001.




means of assessing non-verbal cognition in PwA and PwS.                  which were statistically moderate (exceeding .4 or − .4, i.e., |x| >
Because there are many discourse variables, we created com-              .4). Note that because of the post-hoc nature of this part of the
posite variables where we decided they worked conceptually.              investigation, as well as the large number of comparisons, this
    We standardized all variables. For microstructure analysis,          correlational analysis should be considered exploratory.
we then created composites by averaging (1) Word count, Ut-                  In PwA, there were few notable relationships between
terance count, and MLU to form a “Productivity” variable, (2)            micro- and macrostructural variables, and between macro-
Within utterance pause ratio and Between utterance pause                 structure and non-verbal test performance. The productivity
ratio to form a “Pauses” variable, (3) Mean number of embed-             composite correlated with number of unique propositions in
dings, Mean number of dependents, and the negative of Mor-               PwA, rho = .75, p < .001, showing that more language pro-
phosyntactic error ratio to form a “Grammatical complexity               duction resulted in more narrative content. Productivity
and accuracy” variable, (4) Definiteness score and the negative          negatively correlated with the evaluative devices composite,
of Referential error ratio for a “Reference” variable. For               rho = − .45, p = .05, suggesting a preservation of qualitative
macrostructure analysis, we averaged (5) Qualitative language            and emotional language in speakers who otherwise produced
ratio and Emotional language ratio to form a “Evaluative de-             little. PwA who produced more typical narrative structure had
vices” variable. We further selected (6) ACS, (7) Number of              better grammatical complexity and accuracy, rho = .42,
unique propositions and (8) Misdescriptions ratio to capture             p = .06, and better performance on WASI Matrices, rho = .41,
propositional structure, quantity, and errors. We calculated             p = .07. PwA with fewer misdescriptions scored high on the
correlations with Spearman's rho. Because the PwA group was              reference composite, rho = − 57, p = .008, and scored higher on
smaller than the PwS group, selecting a threshold for reporting          the PPT, rho = − .44, p = .05. There were no moderate or
based on statistical significance would be confounded by                 stronger correlations between microstructure variables and
sample size differences. We therefore report all correlations            non-verbal test performance in PwA.

                                                      c o r t e x 1 9 5 ( 2 0 2 6 ) 8 1 —9 5                                           89




Fig. 2 — Differences between PwA and PwS in macrostructure variables; z-scores represent normalized values for each group
relative to the respective control group. The line at zero represents the respective control mean. * denotes p < .05; ** denotes
p < .01; *** denotes p < .001.




    In PwS, there were more notable correlations. The produc-               notable correlations: PwA with higher TROG scored higher on
tivity composite correlated with the number of unique propo-                the reference composite, rho = .49, p = .03, the grammar
sitions, but to a substantially weaker degree as in PwA, rho = .45,         composite, rho = .44, p = .05, and the proportion of mis-
p = .01. PwS who produced more unique propositions also                     descriptions, rho = .44, p = .05. Naming (BNT) scores corre-
scored higher on the reference composite, rho = .53, p = .002. Use          lated with ACS, rho = .49, p = .03.
of evaluative devices correlated with the reference composite,                 In PwS, conceptual disorganization was most strongly
rho = .49, p = .006. PwS who produced more misdescriptions                  associated with discourse variables. PwS with greater disor-
displayed poorer grammatical complexity and accuracy                        ganization produced fewer evaluative devices, rho = − .61,
(grammar composite), rho = − .40, p = .03, scored lower on the              p < .001, and more misdescriptions, rho = .51, p = .003, and
reference composite, rho = − 45, p = .01, had lower PPT scores,             scored lower on the reference composite, rho = − .4, p = .03.
rho = − .68, p < .001, and lower WASI scores, rho = − .46, p = .01.
    In contrast to PwA, the data from PwS contained notable
correlations between microstructure and performance in non-                 4.         Discussion
verbal reasoning tests. Better reference was associated with
higher WASI scores, rho = .41, p = .02, and better grammatical              We compared spontaneous narrative language of PwA and