import { Stack, Row, H1, H2, Text, Table, Select, Divider, useState, useHostTheme } from "cursor/canvas";
type Item = "DER" | "INC" | "POS";
const specification = {"id": "tlc-independent-evaluation-v2", "status": "withdrawn_as_primary_outcome_unvalidated_custom_rubric", "date": "2026-11-17", "original_tlc_replication": false, "new_model_outputs": false, "blocks": [{"block_id": "B1", "topic": "일상 서술", "questions": ["평소 하루를 어떻게 보내는지 아침부터 저녁까지 이야기해 주세요.", "그중 하루를 예로 들어 조금 더 구체적으로 말씀해 주세요."]}, {"block_id": "B2", "topic": "최근 사건의 순서", "questions": ["최근 있었던 일 중 기억에 남는 일 하나를 처음부터 이야기해 주세요.", "그 일이 있기 전과 후에 어떤 일이 있었는지 차례로 말씀해 주세요."]}, {"block_id": "B3", "topic": "걱정이나 불편한 경험", "questions": ["요즘 마음에 걸리거나 불편한 일이 있다면 어떤 일인지 이야기해 주세요.", "어떤 경험 때문에 그렇게 생각하거나 느끼게 되었는지 말씀해 주세요."]}, {"block_id": "B4", "topic": "생활 기능", "questions": ["최근 평소에 하던 일을 어떻게 하고 지내는지 이야기해 주세요.", "최근에 실제로 하셨던 일 하나를 구체적으로 말씀해 주세요."]}, {"block_id": "B5", "topic": "대인 상황", "questions": ["최근 다른 사람과 함께 있었던 상황 하나를 이야기해 주세요.", "그때 상대방은 무엇을 했고 본인은 어떻게 반응했는지 말씀해 주세요."]}, {"block_id": "B6", "topic": "앞으로의 계획", "questions": ["앞으로 며칠 동안 무엇을 하려고 하는지, 그 이유와 함께 말씀해 주세요.", "그 계획을 위해 어떻게 준비하거나 행동할 생각인지 더 말씀해 주세요."]}], "items": {"DER": {"name": "발화 내 생각의 연결", "anchors": {"0": "관찰 가능한 생각들이 맥락상 연결된다. 질문자가 요구한 주제 전환은 포함하지 않는다.", "1": "설명되지 않은 국소적인 연결 약화가 있으나, 통상적인 맥락만으로 주요 흐름을 따라갈 수 있다. 단순한 비유·생략은 배제한다.", "2": "분명한 연결 이탈 때문에 설명을 더 들어야 하지만, 두 응답을 함께 보면 주요 사건이나 의도를 복원할 수 있다.", "3": "서로 이해 가능한 생각 사이의 연결이 반복적으로 무너져, 추가 질문 후에도 핵심 전개의 일부를 복원하지 못한다.", "4": "개별 생각은 일부 이해되지만 블록 전반에 유지되는 흐름을 거의 찾지 못한다. 문장 자체를 이해할 수 없는 것만으로 DER 4를 주지 않는다."}}, "INC": {"name": "문장·절 내부의 의미 구성", "anchors": {"0": "의미를 해석할 수 있다. 내용이 비현실적이거나 믿기 어렵다는 사실은 근거가 아니다.", "1": "표현 일부의 의미 구성이 분명히 어긋나지만, 추측을 새로 보태지 않고 해당 메시지를 해석할 수 있다. 흔한 말 더듬기·구어적 문법 생략은 제외한다.", "2": "일부 절의 의미를 해석할 수 없지만, 나머지 발화와 추가 응답으로 주요 메시지를 이해할 수 있다.", "3": "핵심 절의 의미가 무너져 추가 응답 후에도 주요 메시지의 상당 부분을 이해할 수 없다.", "4": "블록의 언어 대부분에서 해석 가능한 명제를 얻기 어렵다. 출력 잘림이나 손상된 문자 때문에 읽을 수 없는 경우는 제외한다."}}, "POS": {"name": "열린 질문에 대한 자발적 확장", "anchors": {"0": "주제에 필요한 구체적인 내용을 자발적으로 확장한다. 정해진 최소 글자 수는 없다.", "1": "첫 답변의 확장이 부족하지만 중립적 추가 질문 후에는 적절한 설명을 제공한다.", "2": "두 차례의 기회에도 설명이 제한적이며, 질문자가 정보를 얻기 위해 더 유도해야 할 상태다. 일부 구체적 정보는 얻는다.", "3": "두 기회 모두 짧고 확장되지 않은 답변에 머물러, 필요한 서술을 거의 얻지 못한다. 명시적 거부나 질문을 이해하지 못한 경우는 따로 구분한다.", "4": "연구용 예약 범주. 기술적으로 정상 완료된 두 반응에서 명시적인 의도된 침묵을 관찰하고, 거부·출력 실패와 구분할 자료가 있을 때만 사용한다. 일반 텍스트 응답만으로는 대개 판정 불가다. **주 평가 사례의 POS 목표는 0~3으로 제한한다.**"}}}, "scoring": {"block_grades": "integer 0..4 or null; POS=4 reserved and not a primary target", "aggregation": "fixed six-block equal-weight mean; grade counts and unknown identification bounds required", "primary_outputs": "per-item score and target-interval distance; no clinical total", "equal_item_error": "secondary engineering summary, not clinical severity", "missing": "retain six planned slots; null is not zero", "target_distance": "max(lower-score,0,score-upper)", "scale_assumption": "Equal cost per ordinal step, declared study loss; not clinically equal intervals", "judging_unit": "One complete interview per blinded evaluation context", "hidden": ["method", "generation prompt", "target", "diagnosis label", "other outputs"]}, "sources": [{"name": "TLC 1986", "url": "https://pubmed.ncbi.nlm.nih.gov/3764363/", "reviewed": "Full 10-page author paper via university-hosted PDF; printed 474–477 relevant"}, {"name": "TLI 2002", "url": "https://doi.org/10.1192/bjp.181.4.326", "reviewed": "Primary article Method and Appendix; full rating manual not obtained"}, {"name": "TALD 2014", "url": "https://pubmed.ncbi.nlm.nih.gov/25458572/", "reviewed": "Primary abstract only; full anchor manual not obtained"}]};
const fixtures = {"A": {"kind": "arithmetic_example", "interview_id": "EXAMPLE_A_NOT_A_MODEL_OUTPUT", "scores": {"DER": [0, 1, 0, 1, 0, 1], "INC": [1, 2, 1, 2, 1, 2], "POS": [0, 0, 0, 0, 0, 0]}, "targets": {"DER": [2, 2], "INC": [0, 0], "POS": [1, 1]}}, "B": {"kind": "arithmetic_example", "interview_id": "EXAMPLE_B_NOT_A_MODEL_OUTPUT", "scores": {"DER": [2, 2, 2, 2, 2, 1], "INC": [0, 0, 0, 0, 0, 1], "POS": [1, 1, 1, 1, 1, 1]}, "targets": {"DER": [2, 2], "INC": [0, 0], "POS": [1, 1]}}};
const itemKeys: Item[] = ["DER", "INC", "POS"];
function calc(grades: Array<number | null>, target: number) {
  const known = grades.filter((v): v is number => v !== null);
  const total = known.reduce((a,b) => a+b,0);
  const lo = total / 6, hi = (total + 4 * (6-known.length)) / 6;
  const d = (v:number) => Math.abs(v-target);
  return {lo,hi,missing:6-known.length,errLo:Math.max(lo-target,0,target-hi),errHi:Math.max(d(lo),d(hi))};
}
export default function TLCIndependentEvaluation() {
  const theme = useHostTheme();
  const [example,setExample] = useState("A");
  const [item,setItem] = useState<Item>("DER");
  const [scores,setScores] = useState<Record<Item,Array<number|null>>>(fixtures.A.scores);
  const [targets,setTargets] = useState<Record<Item,number>>({DER:2,INC:0,POS:1});
  const calculated = itemKeys.map(k => ({key:k,...calc(scores[k],targets[k])}));
  const summaryLo = calculated.reduce((a,b) => a+b.errLo,0)/3;
  const summaryHi = calculated.reduce((a,b) => a+b.errHi,0)/3;
  const display = (lo:number,hi:number) => Math.abs(lo-hi)<1e-10 ? lo.toFixed(3) : `${lo.toFixed(3)} ～ ${hi.toFixed(3)}`;
  return <Stack gap={20} style={{padding:24,maxWidth:1160,margin:"0 auto",color:theme.text.primary}}>
    <Text style={{color:theme.text.secondary}}>평가 설계 v2 · 2026-11-17 · 임상 검증 전 연구용 수정안</Text>
    <H1>주 평가안 제안 철회: 검증되지 않은 새 루브릭</H1>
    <Text weight="semibold">임상적 모사 성능의 우열을 입증할 근거가 없습니다. 아래는 개발용 산술 설명과 설계 이력입니다. TLC 원척도의 타당성은 이 수정안에 승계되지 않습니다.</Text>
    <Text>6개 블록 × 2회 응답. 블록별 DER·INC·POS 0~4 → 항목별 6블록 평균 → 사전 목표와의 단계 거리. 선호 선택이나 원문 길이당 증상 빈도가 주 지표가 아닙니다.</Text>
    <div style={{padding:16,borderLeft:`3px solid ${theme.accent.primary}`,background:theme.fill.tertiary}}>
      <Text weight="semibold">실제 모델 결과가 없는 산술 설명 도구입니다.</Text>
      <Text>아래 A·B는 가상 숫자입니다. 원 TLC 점수·검증된 한국어 단축판·환자 유사도 백분율이 아닙니다. 등급 간 같은 비용을 둔 연구용 손실함수입니다.</Text>
    </div>
    <Row align="center" wrap>
      <Text>가상 예시</Text>
      <Select value={example} onChange={v => {setExample(v);setScores(fixtures[v as "A"|"B"].scores);}} options={[{value:"A",label:"산술 예시 A"},{value:"B",label:"산술 예시 B"}]} />
      <Text>수정할 항목</Text>
      <Select value={item} onChange={v=>setItem(v as Item)} options={itemKeys.map(k=>({value:k,label:k+" · "+specification.items[k].name}))} />
      <Text>목표 점수</Text>
      <Select value={String(targets[item])} onChange={v=>setTargets({...targets,[item]:Number(v)})} options={[0,1,2,3,4].map(v=>({value:String(v),label:String(v)}))} />
    </Row>
    <Text style={{color:theme.text.secondary}}>POS의 주 실험 목표는 0~3으로 제한합니다. 이 계산 도구의 4는 산술 범위를 보여주는 값입니다. 실제 설계에서는 목표 구간도 허용합니다.</Text>
    <Row wrap gap={16}>{scores[item].map((grade,b)=><Stack key={b} gap={5}>
      <Text>B{b+1}</Text>
      <Select value={grade===null?"null":String(grade)} onChange={v=>{const copy=[...scores[item]];copy[b]=v==="null"?null:Number(v);setScores({...scores,[item]:copy});}} options={[0,1,2,3,4].map(v=>({value:String(v),label:String(v)})).concat([{value:"null",label:"평가 불가"}])} />
    </Stack>)}</Row>
    <H2>대화별 독립 점수와 목표 이탈거리</H2>
    <Table headers={["항목","목표","6블록 평균 / 가능 범위 (0~4)","목표 이탈거리 (단계)","평가 불가 블록"]} rows={calculated.map(r=>[r.key,targets[r.key],display(r.lo,r.hi),display(r.errLo,r.errHi),`${r.missing} / 6`])} />
    <Text weight="semibold">세 항목 등가중 오차 요약: {display(summaryLo,summaryHi)} 단계 · 작을수록 목표에 가까움</Text>
    <Text style={{color:theme.text.secondary}}>평가 불가가 있으면 분모 6을 유지한 범위만 표시합니다. 이 범위는 신뢰구간이 아닙니다. 항목별 결과와 등급 분포를 우선 보고하며 요약 오차만으로 임상적 우월성을 주장하지 않습니다.</Text>
    <Divider />
    <H2>{item} 블록 채점 기준</H2>
    <Table headers={["등급","이번 연구의 수정 앵커"]} rows={Object.entries(specification.items[item].anchors).map(([grade,anchor])=>[grade,anchor])} />
    <H2>질문과 맥락의 표준화</H2>
    <Table headers={["블록","열린 질문","중립적 추가 질문"]} rows={specification.blocks.map(b=>[b.block_id+" · "+b.topic,b.questions[0],b.questions[1]])} />
    <H2>길이와 맥락: 해결하는 부분과 남는 부분</H2>
    <Text>각 블록을 동일 가중으로 채점해 긴 응답에 표본 수를 더 주지 않습니다. 정상 주제 전환·일관된 기이한 믿음·한국어 생략·요청받은 반복은 장애로 자동 처리하지 않습니다. 짧아서 연결을 평가할 수 없으면 0점이 아닌 평가 불가입니다.</Text>
    <Text>관찰 기회를 맞춰도 길이 영향이 완전히 없어지지는 않습니다. 자연 발화에서는 길이를 강제하지 않고, 의미를 유지한 길이 변환 점검과 별도의 공통 표현 제약 조건에서 DER·INC를 재확인합니다. 말수 감소는 길이 보정으로 제거하지 않습니다.</Text>
    <H2>기존 척도와의 관계</H2>
    <Text>TLC에서 관찰 개념을, TLI에서 표준화된 발화 유도 원칙을 참고했습니다. 블록별 앵커·평균·목표 거리는 연구용 수정입니다. TALD는 공개 초록만 검토했습니다. 전문의는 나중에 같은 자료와 같은 앵커로 독립 채점합니다.</Text>
    <Row wrap>{specification.sources.map(s=><a key={s.name} href={s.url} target="_blank" rel="noreferrer" style={{color:theme.text.link}}>{s.name}</a>)}</Row>
  </Stack>;
}
