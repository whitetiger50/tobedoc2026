import { Stack, Row, H1, H2, Text, Table, Select, useState, useHostTheme } from "cursor/canvas";
type Measure={key:string;label:string;exact:number;alpha:number|null;a1:number|null;a3:number|null;sd:number;matrix:number[][]};
const DATA:{ids:string[];measurements:Measure[];m8:{agreement:number;kappa:number;iccA1:number}}={"ids":["DEV-M0-01-v02","DEV-M0-01-v04","DEV-M0-02-v02","DEV-M0-02-v04","DEV-M0-03-v02","DEV-M0-03-v04"],"measurements":[{"key":"codex","label":"GPT-6.1 Sol High","exact":1.0,"alpha":null,"a1":null,"a3":null,"sd":0.0,"matrix":[[4,4,4],[4,4,4],[4,4,4],[4,4,4],[4,4,4],[4,4,4]]},{"key":"claude","label":"Claude Opus 5.5","exact":0.6666666666666666,"alpha":0.08928571428571429,"a1":0.16666666666666666,"a3":0.375,"sd":0.408248290463863,"matrix":[[4,4,4],[4,4,4],[4,4,4],[4,3,3],[4,4,3],[4,4,3]]},{"key":"mean","label":"두 모델 산술평균 /회차","exact":0.6666666666666666,"alpha":0.08928571428571429,"a1":0.16666666666666666,"a3":0.375,"sd":0.2041241452319315,"matrix":[[4.0,4.0,4.0],[4.0,4.0,4.0],[4.0,4.0,4.0],[4.0,3.5,3.5],[4.0,4.0,3.5],[4.0,4.0,3.5]]}],"m8":{"agreement":0.0,"kappa":0.0,"iccA1":0.0}};
const fmt=(x:number|null)=>x===null?"미정의":x.toFixed(3);
export default function ReliabilityStatistics(){
 const t=useHostTheme();const [selected,setSelected]=useState("claude");const chosen=DATA.measurements.find(m=>m.key===selected)??DATA.measurements[0];
 return <Stack gap={26} style={{padding:24,maxWidth:1180,color:t.text.primary}}>
  <Stack gap={9}><H1>평가 신뢰도 검증을 성능 비교보다 먼저</H1><Text>2026-11-19 · 기존 원평정의 통계 재분석 · 새 발화·새 평정0</Text>
   <H2>통계 지표를 계산할 수 있습니다. 현재 자료의 정밀도는 제한됩니다.</H2>
   <Text>같은 원문을 반복 평정하는 신뢰도 검증을 우선하고, 그 결과에 맞춰 평가 기준·운용을 점검한 뒤 B/T 성능 비교를 재개할지 판단합니다. B 원형 문서 감사는 병행할 수 있습니다.</Text>
  </Stack>
  <Stack gap={10}><H2>M5: 고정 원본6대화 × 같은 측정3회 · 프로필3개</H2>
   <Table headers={["측정","반복쌍 단순 일치율","ordinal α","ICC(A,1)","ICC(A,3)","대화 내 합동 SD /점"]} rows={DATA.measurements.map(m=>[m.label,`${(m.exact*100).toFixed(1)}%`,fmt(m.alpha),fmt(m.a1),fmt(m.a3),fmt(m.sd)])}/>
   <Text tone="secondary" size="small">출처: M5 원평정2026-11-18, results.json의 Python 재계산2026-11-19. 반복쌍18개는 독립 표본이 아닙니다. 원본과 가족 교체 대조가 같은9항목 묶음에 제시된 맥락은 남으며, 주계수는 원본6개만 계산했습니다.</Text>
   <Text>GPT는18평점 모두4여서 α·ICC의 분모가0입니다. 100% 일치율을 신뢰도1로 대체하지 않습니다. 두 모델 평균은 이 자료에서2+Claude/2이므로 SD와 대화 간 차이가 함께 줄고 ICC는 그대로 남습니다.</Text>
   <Text tone="secondary" size="small">A는 절대일치입니다. ICC(A,1)은 한 회차 측정, ICC(A,3)은 같은 측정을 세 회차 평균한 경우이며 현재 개발의 단회 판독을 자동 대체하지 않습니다. ICC는1~4점을 등간으로 보는 보조적 분석입니다. SD는 SEM·최소검출차이·일반 오차 한계가 아닙니다.</Text>
  </Stack>
  <Stack gap={10}><H2>실제 반복 원점수</H2>
   <Row gap={12}><Text>측정 선택</Text><Select value={selected} onChange={setSelected} options={DATA.measurements.map(m=>({value:m.key,label:m.label}))}/></Row>
   <Table headers={["고정 원문","1회차","2회차","3회차"]} rows={DATA.ids.map((id,i)=>[id,...chosen.matrix[i]])}/>
   <Text tone="secondary" size="small">환자 발화를 다시 생성하지 않은 같은6개 원문입니다. 평균 조건은 각 회차의 실제 GPT/Claude 원평정을 산술평균했습니다. 반복 회차를 독립 환자 사례로 세지 않습니다.</Text>
  </Stack>
  <Stack gap={10}><H2>M8: 서로 다른 두 모델의 절대일치</H2>
   <Table headers={["고정18대화·3프로필","값"]} rows={[["같은 점수",`${DATA.m8.agreement*18}/18`],["선형 가중 κ",fmt(DATA.m8.kappa)],["절대일치 ICC(A,1)",fmt(DATA.m8.iccA1)]]}/>
   <Text>GPT모두4/Claude모두3이었습니다. 대화 간 점수변동이 없어 일관성형 ICC(C,1)은 미정의입니다. 이는 이번 자료의 분포이며 어떤 모델이 임상적으로 옳다는 판정이 아닙니다.</Text>
  </Stack>
  <Stack gap={10}><H2>다음 검증에서 고정할 것</H2>
   <Text>고정 텍스트 × 평가 모델 × 반복 회차를 교차하고, 실제 운용할 제시 단위·앵커·평가 역할·순서를 명시합니다. 모델별 반복성·모델 간 절대일치·두모델 평균의 재현성을 구별합니다.</Text>
   <Text>프로필 군집과 반복 구조를 반영한 신뢰구간·절대 변동을 확인하고, 필요한 정밀도에 맞춰 사례 수와 반복 수를 설계합니다. 자연 대화와 큰 오류 대조의 신뢰도를 분리합니다. 점수가 잘 나오도록 검증세트를 고르지 않습니다.</Text>
   <Text>평가 기준을 고치면 별도 자료로 재검증한 뒤 B/T 비교 재개를 판단합니다. 기존 최종12프로필과720판독 계획은 변경하거나 실행하지 않았습니다.</Text>
  </Stack>
  <Text tone="secondary" size="small">표본6개·프로필3개·점수3/4집중의 사후 탐색 값입니다. 안정적인 모집단95%신뢰구간·통과 임계값은 확보하지 않았습니다. 신뢰도와 임상 타당성은 별도로 확인해야 합니다. 계산은 원저자 α 예제·상수 퇴화·가산편향 ICC fixture로 점검했습니다. 원문 출처와 전체 계수는 README.md·results.json에 있습니다.</Text>
 </Stack>;
}
