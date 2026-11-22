import { Stack, Grid, H1, H2, H3, Text, Table, Select, useState } from "cursor/canvas";

const reuse = [
  ["입력·대화 생성 기반", "사실/자기이해/의사소통/이력 분리, 원문·버전·해시, 공식 CLI", "새 언어 현상 실험의 실행 기반으로 유지", "질환 언어 재현을 검증한 결과는 아님"],
  ["환자 v0.2", "설정 준수와 대화 연속성을 다루는 기준 프롬프트", "조직적인 생성 기준 조건으로 보존", "최적 모형·실제 건강 대조군으로 부르지 않음"],
  ["v0.3~v0.6 비교", "제약·예시·모델 판독에 관한 개발 이력", "공학적 예비연구와 실패 분석에 활용", "임상적 사고 특성의 개선·최적화 결론으로 바꾸지 않음"],
  ["M12~M18 판독 연구", "반복성, 대조 반응, 상수·천장과 기준 경계", "평가 설계의 예비 근거로 보존", "새 언어 현상 지표의 타당성을 대신하지 못함"],
  ["인공 오류 대조", "무관한 답, 보고식 틀, 제삼자 역할 소개", "단순 인공 이상에 대한 분석기 반응 점검", "임상적 사고형식장애의 양성 표본이 아님"],
  ["Realism · CCF-R1", "전체 인상과 문맥별 적합성의 모델 판단", "부차적 품질·문맥 기록 후보", "조현병 언어 특성이나 인지 기제의 주지표로 쓰지 않음"]
];
const dimensions = {
  coherence: {
    label: "첫 제안: 국소 연결과 전체 목표 유지",
    question: "문장은 각각 이해되지만 전체 이야기·질문 목표에서 점차 벗어나는가?",
    observation: "인접 문장 사이 관계와 전체 주제에 대한 관계를 구별해, 실제 구절과 질문·선행 문맥을 근거로 기록한다.",
    contrasts: "일반적인 부연·주제 전환, 단순 무관 답변, 사실 모순, 길이 차이와 구별해야 한다. 의미 유사도 하나를 응집성의 정답으로 삼지 않는다.",
    proposal: "중립적 경험/정신증 관련 경험 × 조직적/목표 유지 변화의 4조건을 제안한다. 내용과 형식의 선택적 변화를 확인할 설계이며 아직 실행하지 않았다."
  },
  reference: {
    label: "후속 후보: 지시 대상·앞선 정보 연결",
    question: "누구·무엇을 말하는지, 앞서 소개한 대상과 지금 표현이 어떻게 연결되는가?",
    observation: "표현과 그 지시 대상·앞선 도입의 대응을 실제 원문에서 기록한다. LLM은 후보 추출을 돕고 참조 주석과 대조한다.",
    contrasts: "한국어의 자연스러운 주어 생략을 오류로 자동 취급하지 않는다. 영어 명사구 지표나 번역된 전사를 한국어 임상 준거로 곧바로 옮길 수 없다.",
    proposal: "검증 가능한 대상·사건 골격과 동일 서사 과제가 먼저 필요하다. 첫 실험에 모든 언어 현상을 합산하지 않는다."
  }
};
const steps = [
  ["1 · 현상 근거집", "문헌 정의, 관찰 예시, 비슷하지만 다른 현상, 자료 접근 조건을 좁힌다.", "지금 다음으로 만들 산출물"],
  ["2 · 통제 생성 설계", "내용·과제·기회를 맞춰 목표한 언어 양상을 선택적으로 유도할 조건을 정한다.", "구체 프로토콜과 별도 설계 비평 후"],
  ["3 · 독립 관찰·분석", "생성 반복과 판독 반복을 분리하고 표적 재현·부수 오류·기록 근거를 분석한다.", "전체 인상 평균의 상승을 성공 조건으로 삼지 않음"],
  ["4 · 환자 자료와 연결", "허가된 전사·독립 평정이 있으면 같은 과제의 특징·실패 양상을 비교한다.", "현재 자료·전문의 평정은 확보되지 않음"]
];

export default function ResearchReset() {
  const [feature, setFeature] = useState("coherence");
  const [scenario, setScenario] = useState("current");
  const selected = dimensions[feature as keyof typeof dimensions];
  return <Stack gap={28} style={{padding:26,maxWidth:1300,margin:"0 auto"}}>
    <Stack gap={10}>
      <Text tone="secondary" size="small">M19 · 2026-11-19 · 연구 방향 제안 / 새 실험 결과 아님</Text>
      <H1>조현병의 사고·의사소통을 텍스트로 탐구하기</H1>
      <Text>목표는 환자 역할의 인상 점수를 높이는 것에서, 정의한 언어 양상을 재현·분석하고 실제 환자 언어와의 연결 범위를 밝히는 것으로 다시 맞춥니다. 기존 작업은 실험 기반과 측정 예비연구로 활용할 수 있습니다.</Text>
      <Text tone="secondary">누적 합성 발화663개/108대화는 개발 자료입니다. 환자 원자료·전문의 검증은 없습니다. 이번 정리에서 새 생성·평정·프롬프트 수정은 하지 않았습니다.</Text>
    </Stack>
    <Grid columns={2} gap={26}>
      <Stack gap={9}><H2>우리가 관찰할 수 있는 것</H2><Text>경험·믿음이라는 내용, 문장과 담화의 조직, 질문·재진술·명료화의 상호작용을 구별합니다. 텍스트 관계는 사고 특성에 관한 간접 증거입니다.</Text></Stack>
      <Stack gap={9}><H2>아직 연결되지 않은 것</H2><Text>LLM의 비슷한 문장이 환자의 내적 사고나 인지·신경 기제까지 같다는 증거는 아닙니다. 문헌에 맞춘 조작, 사람의 임상 참조, 환자 집단의 분포는 다른 검증 단계입니다.</Text></Stack>
    </Grid>
    <Stack gap={10}>
      <H2>지금까지의 작업: 활용과 주장 범위</H2>
      <Table headers={["산출물","확보한 것","다시 활용할 곳","넘어서면 안 되는 해석"]} rows={reuse}/>
      <Text size="small" tone="secondary">출처: 환자v0.2 원문, M2 근거 감사, M17 개정안, M18 cases.json·results.json·README. M18 세 사례는 모두 대체로 조직적으로 답하도록 설정되어 사고형식 변화를 직접 시험한 자료가 아닙니다.</Text>
    </Stack>
    <Stack gap={10}>
      <H2>언어 현상을 먼저 좁히는 제안</H2>
      <Select value={feature} onChange={setFeature} options={Object.entries(dimensions).map(([value,d])=>({value,label:d.label}))}/>
      <H3>{selected.question}</H3>
      <Text>{selected.observation}</Text><Text tone="secondary">구별해야 할 것: {selected.contrasts}</Text><Text>{selected.proposal}</Text>
      <Text size="small" tone="secondary">임상 척도나 검증된 한국어 프롬프트가 아니라 저자 제안입니다. 진단명만으로 모든 생성물에 특징을 강제하지 않습니다.</Text>
    </Stack>
    <Stack gap={10}>
      <H2>자료 확보 여부에 따른 연구 범위</H2>
      <Select value={scenario} onChange={setScenario} options={[{value:"current",label:"현재: 환자 자료·독립 평정 미확보"},{value:"conditional",label:"가정: 허가된 환자 자료·독립 참조 확보"}]}/>
      {scenario === "current" ? <Stack gap={8}><Text>현재 가능한 연구는 문헌에 근거한 언어 양상의 LLM 행동 재현·실패와 분석 도구의 반응을 다루는 탐색 연구입니다. 임상적으로 검증된 조현병 생성기를 만들었다고 주장할 근거는 없습니다.</Text><Text tone="secondary">TOPSY는 우선 확인할 자료 후보입니다. 2026년 데이터 논문에는 승인 연구자의 접근 경로가 있지만 PsychosisBank 홈페이지에는 열람만 가능하고 분석은 아직 불가라는 안내가 있습니다. 현행 자료·버전에 적용되는 조건은 미확인이고, 즉시 사용 가능하거나 영구 불가하다고 단정하지 않습니다.</Text></Stack> : <Stack gap={8}><Text>이 조건이 실제 충족되면 같은 과제의 환자 언어와 생성물의 특징·관찰 일치·실패를 비교할 수 있습니다. 현재 확보됐다는 뜻은 아닙니다.</Text><Text tone="secondary">원자료 사용과 외부 LLM 처리 허용 여부를 확인해야 합니다. 임상의의 소규모 적합성 검토와 환자 집단 분포의 재현, 인지 기제의 검증을 구별합니다.</Text></Stack>}
      <Text size="small" tone="secondary">자료 경로의 현재 확인: PsychosisBank 홈페이지·TOPSY2026 데이터 논문; He2026·Çokal2026 Data availability. 회원 신청·자료 요청 연락·환자 원문 수집은 하지 않았습니다.</Text>
    </Stack>
    <Stack gap={10}><H2>다음 산출물과 개발 순서</H2><Table headers={["순서","할 일","범위·현재 상태"]} rows={steps}/><Text>첫 선택은 국소 연결과 전체 목표 유지에 관한 작은 근거집입니다. 문헌 기반 시뮬레이션만 가능한지, 실제 자료 비교까지 가능한지 먼저 정합니다. 평가기 정비가 연구의 주목적을 대신하지 않도록 제한합니다.</Text></Stack>
    <Stack gap={9}><H2>연구 방향을 받쳐 주는 원문</H2>
      <Text><a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC11932972/">Fradkin·Nour·Dolan 2023</a> — 생성 조작과 언어 지표의 반응을 연결하는 시뮬레이션 연구. 현재 프롬프트 실험이 그 기제를 복제한 것은 아닙니다.</Text>
      <Text><a href="https://www.sciencedirect.com/science/article/pii/S002839322600151X">Çokal 등 2026</a> — LLM의 구체 지시 표현 추출을 수작업 주석과 비교. 영어 자료의 결과입니다.</Text>
      <Text><a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC12948966/">He 등 2026</a> — 의미 유사도와 사람이 판단한 응집성의 관계를 직접 검토.</Text>
      <Text><a href="https://pubmed.ncbi.nlm.nih.gov/38600593/">Dalal 등 2024</a> — 언어 양상의 이질성. 하나의 조현병 말투를 가정하지 않는 근거.</Text>
      <Text><a href="https://aclanthology.org/2025.ranlp-1.92/">Nenchev 등 2025</a> — 실제 면담의 질문–답변 관계를 역추론 과제로 분석.</Text>
      <Text><a href="https://talkbank.org/psychosis/">PsychosisBank 공식 접근 안내</a> — 열람과 분석 가능 여부를 구별해야 하는 자료 경로.</Text>
      <Text><a href="https://www.sciencedirect.com/science/article/pii/S2352340926003410">TOPSY 데이터 논문 2026</a> — 그림 설명 전사·임상 관찰과 승인 연구자 접근 경로. 실제 사용 조건은 아직 확인되지 않았습니다.</Text>
    </Stack>
    <Text size="small" tone="secondary">최종12사례는 계속 미사용이고720판독 계획은 이번에 바꾸거나 실행하지 않았습니다. 새 모델 학습·다운로드·유료API·새 패키지는 사용하지 않았습니다. 이 방향 메모에 대한 새 Astra/Claude 비평도 아직 수행하지 않았습니다.</Text>
  </Stack>;
}
