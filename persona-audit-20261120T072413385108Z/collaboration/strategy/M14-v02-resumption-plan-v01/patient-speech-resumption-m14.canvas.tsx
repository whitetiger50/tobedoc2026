import { Stack, Grid, H1, H2, H3, Text, Table, Select, useState, useHostTheme } from "cursor/canvas";

const decisions = [
  ["질문·설정의 대상과 시간 정렬", "다음 작업", "진료 전 활동을 묻는 질문과 진료 때 대화를 다룬 goal의 불일치", "환자 프롬프트 유지"],
  ["선공개·반복 억제", "보류", "수면 기록 목표는 수면 질문과 관련됨. 뒤의 의사 질문이 재답변을 요청함", "정당한 자발성·재확인 보호"],
  ["일반 범위 금지문 추가", "보류", "‘둘이’는 경계 표현 한 곳이며 v0.5와 유사한 지시의 이득 미확인", "명확한 새 기전 없음"],
  ["예시 확대·말투 통일", "보류", "인위적 역할 이탈 탐지가 자연 원문의 상습 결함을 뜻하지 않음", "v0.6 예시 이득 미확인"]
];

const evidence = [
  { id: "A01", label: "사례1 · 수면 답변의 목표 설명", question: "요즘 잠은 어떠세요?", answer: "잠드는 데 시간이 좀 걸리는 날이 있어요. 그래도 밤중에 자주 깨지는 않아요. 다음 진료 전까지 잠드는 데 얼마나 걸리는지 적어 보고 싶어요.", fact: "다음 진료 전까지 잠드는 시간이 얼마나 걸리는지 적어 보고 싶다.", finding: "현재 수면 주제와 직접 관련되고, 설정은 관련 경험을 필요한 만큼 덧붙일 수 있게 한다. 미요청 설명이라는 이유만으로 생성 결함을 확정하지 않는다." },
  { id: "A02", label: "사례1 · 목표 재확인", question: "다음 진료 전까지 해 보고 싶은 일이 있나요?", answer: "잠드는 데 얼마나 걸리는지 적어 보고 싶어요.", fact: "같은 목표가 앞선 P07에서 이미 언급됐다.", finding: "의사가 다시 물었으므로 짧게 같은 사실을 답할 수 있다. 앞으로 나올 고정 질문의 순서를 환자가 미리 따라야 한다고 요구하지 않는다." },
  { id: "A03", label: "사례2 · 진료 전과 진료 때", question: "다음 진료 전까지 해 보고 싶은 일이 있나요?", answer: "다음 진료 때 안내 방송 때문에 신경 쓰이는 상황을 좀 더 이야기해 보고 싶어요.", fact: "다음 진료에서 안내 방송 때문에 신경 쓰이는 상황을 더 이야기하고 싶다.", finding: "질문이 의도한 시간과 제공한 목표 사실의 시간이 다르다. 다음 개발자료의 작성 단계에서 맞출 대상이다. 과거 문항·출력·평점은 수정하지 않는다." },
  { id: "A04", label: "사례2 · ‘둘이’의 의미 범위", question: "집에서는 누구와 함께 지내세요?", answer: "다 큰 딸하고 둘이 살고 있어요.", fact: "성인 딸과 함께 산다.", finding: "가구원 수를 단정한 것인지 관용적 동거 답변인지 경계가 남는다. 기존 원문 판독의 사실축은 두 모델 3회 모두 2점이었다. 지적 부재를 무오류나 탐지 실패의 증거로 쓰지 않는다." },
  { id: "A05", label: "사례3 · 필요한 시점 재진술", question: "말씀하신 경험은 주로 어떤 때에 생기나요?", answer: "사람이 많은 곳에 다녀온 날 오후에 가끔 들려요. 아침에는 잘 안 들리는 편이에요.", fact: "사람이 많은 곳에 다녀온 날 오후에 가끔 들리며 아침에는 들리지 않는 편이다.", finding: "앞선 답에 있던 시간 표현도 현재 질문이 다시 요구할 수 있다. 반복을 줄이려고 필요한 사실을 생략하지 않는다." }
];

export default function DevelopmentResumption() {
  const theme = useHostTheme();
  const [selected, setSelected] = useState("A03");
  const item = evidence.find(e => e.id === selected) ?? evidence[2];
  return <Stack gap={26} style={{ padding: 24, maxWidth: 1200, color: theme.text.primary }}>
    <Stack gap={10}>
      <H1>M14 · v0.2 개발 재개와 다음 우선순위</H1>
      <Text>2026-11-19 · Astra와 별도 Claude의 최초·후속 비평 각 2회 · 이번 단계는 기존 자료 검토와 계획만</Text>
      <H2>특정 결함을 근거로 다루는 개발은 재개 가능</H2>
      <Text>동일 평가자의 반복 일관성과 지정한 편집의 위치 지목은 작은 개발 가설을 시험하는 데 쓸 수 있습니다. 자연 발화의 미세 총점 순위나 임상 타당성이 확보됐다는 통과 선언은 아닙니다. 모델 간 점수 수준을 같게 맞추는 것도 목표가 아닙니다.</Text>
    </Stack>
    <Grid columns={2} gap={24}>
      <Stack gap={8}><H3>확인한 범위</H3><Text>M13 총점 반복쌍 일치: GPT 52/54(96.30%), Claude 50/54(92.59%). 표현 N1/N2는 총점 3/2, 사실 F1/F2는 사실근거 보조축 1/0으로 구별됐습니다.</Text><Text tone="secondary" size="small">출처: M12/M13 원평점·results.json. 큰 조작을 섞은 3프로필 자료에 조건부이며 임상 정확도나 일반 신뢰구간이 아닙니다.</Text></Stack>
      <Stack gap={8}><H3>바로 다음 개선</H3><Text>차기 개발 면담의 질문과 프로필 사실이 같은 대상·시점·지식 범위를 다루도록 작성 점검을 명확히 합니다. 환자 생성기 효과와 입력 과제의 문제를 구별하는 작업입니다.</Text><Text tone="secondary" size="small">이번에는 환자 프롬프트·모듈·평가 기준·기존 생성 입력을 변경하지 않았고 새 발화·수치 평정도 없습니다.</Text></Stack>
    </Grid>
    <Stack gap={10}>
      <H2>개입 후보별 결정</H2>
      <Table headers={["후보", "판단", "실제 근거", "유지할 원칙"]} rows={decisions}/>
      <Text tone="secondary" size="small">Astra·Claude의 실제 비평과 Codex의 수용·반박을 종합한 개발 판단입니다. 멘토 간 동의를 실험 근거나 임상 인증으로 합산하지 않습니다.</Text>
    </Stack>
    <Stack gap={12}>
      <H2>기존 지적 다섯 위치의 기원</H2>
      <Select value={selected} onChange={setSelected} options={evidence.map(e => ({ value: e.id, label: e.label }))}/>
      <Grid columns={2} gap={24}>
        <Stack gap={8}><Text weight="medium">원래 질문과 답</Text><Text>의사: {item.question}</Text><Text>환자: {item.answer}</Text></Stack>
        <Stack gap={8}><Text weight="medium">설정 근거와 판단</Text><Text>근거: {item.fact}</Text><Text>{item.finding}</Text></Stack>
      </Grid>
      <Text tone="secondary" size="small">M13 R의 3대화·24환자턴에서 이미 지적된 다섯 위치를 읽은 비맹검 Codex 노트입니다. 새로운 판독·전체 오류율·무결함 증명이 아니며 이번 검토는 종료했습니다.</Text>
    </Stack>
    <Stack gap={10}>
      <H2>다음 순서와 종료</H2>
      <Table headers={["단계", "산출물·행동", "종료·다음 결정"]} rows={[
        ["이번 완료", "기존 다섯 위치의 기원 정리, 질문 작성 점검 항목 정의", "추가 평정·같은 자료 재분류 없이 마침"],
        ["차기 자료 작성", "목적·대상·시간·근거 fact·알 수 있는 범위·이력·정답 노출을 한 번 대조", "의도한 범위가 맞으면 작성 점검 마침"],
        ["향후 행동 확인", "v0.2 고정. 입력 효과와 환자 프롬프트 효과의 실험을 구별", "지정한 개발 범위를 다 보면 결정"],
        ["분기", "명확한 생성자 결함 한 가지를 선택하거나 v0.2 유지", "모호한 사례만 남으면 그 주기를 닫음; 찾을 때까지 자료를 늘리지 않음"]
      ]}/>
      <Text>한 사례의 명백한 사실 반전은 그 사례에서 진단할 수 있습니다. 여러 프로필의 반복은 일반화 근거를 보태지만 임의 통과 역치가 아닙니다. 프롬프트 후보를 시험할 때는 v0.4~v0.6과 다른 작동 원리를 먼저 설명합니다.</Text>
    </Stack>
    <Text>관련 자발적 설명·정당한 짧은 재확인·한국어 생략을 보호합니다. 기존 Realism 주지표와 원점수는 유지하고, 보조축을 새 총점으로 합치지 않습니다. 최종 12사례와 720회 계획도 그대로 남아 있습니다.</Text>
    <Text tone="secondary" size="small">출처: collaboration/strategy/M14-v02-resumption-plan-v01/의 실제 비평·decision.md·next-development-plan.md·question-readiness-plan.md·기존 원문 발췌. 새 환자 발화·수치 평정·프롬프트 수정 없이 작성, 2026-11-19.</Text>
  </Stack>;
}
