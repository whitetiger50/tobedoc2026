from pathlib import Path
import json
HERE=Path(__file__).resolve().parent

def main():
 audit=json.loads((HERE/'measurement-audit.json').read_text());old=json.loads((HERE/'existing-repeatability-audit.json').read_text());plan=json.loads((HERE/'next-plan.json').read_text())
 data={'repeat':audit['within_judge_fixed_text_M5'],'rounds':audit['same_fixed_text_M5_round_contrasts'],'originals':[{'id':r['item_id'],'codex':r['judges']['codex']['scores'],'claude':r['judges']['claude']['scores']} for r in old['same_text_original_item_scores']],'stages':audit['between_judge_distribution_and_arithmetic_leverage_by_stage'],'plan':plan['display_steps']}
 source='''import { Stack, Row, H1, H2, Text, Table, Select, useState, useHostTheme } from "cursor/canvas";
type Repeat={original_dialogues:number;underlying_profiles:number;ratings:number;all_three_equal_dialogues:number;equal_pairs:number;all_pairs:number;mean_absolute_within_text_pair_difference:number;max_within_text_pair_difference:number;scores:number[][];warning:string};
type Condition={dialogues:number;score_counts:Record<string,Record<string,number>>;GPT_minus_Claude_values:number[];exact_between_judge_agreement:number;one_integer_rating_point_effect_on_condition_mean:number};
const DATA:{repeat:Record<string,Repeat>;rounds:{round:number;means:Record<string,number>;v04_minus_v02:number}[];originals:{id:string;codex:number[];claude:number[]}[];stages:{stage:number;conditions:Record<string,Condition>}[];plan:{step:string;action:string;decision:string;status:string}[]}=__DATA__;
const labels:Record<string,string>={v02:"v0.2",v03:"v0.3",v04:"v0.4",v05:"v0.5",none:"v0.6 예시 없음",examples:"v0.6 예시 있음"};
const names:Record<string,string>={codex:"GPT-6.1 Sol High",claude:"Claude Opus 5.5"};
const f=(n:number)=>n.toFixed(3);
export default function MeasurementAudit(){
 const theme=useHostTheme();const [stage,setStage]=useState("9");const [judge,setJudge]=useState("claude");
 const s=DATA.stages.find(x=>String(x.stage)===stage)??DATA.stages[0];
 return <Stack gap={26} style={{padding:24,maxWidth:1180,color:theme.text.primary}}>
  <Stack gap={9}><H1>작은 점수 차이와 평가 일관성</H1><Text>2026-11-19 · M10 · 기존 실제 평정 재분석과 Astra/Claude 방향 검토</Text>
   <H2>미세한 평균 차이로 프롬프트의 개선 순위를 확정할 근거가 부족합니다.</H2>
   <Text>같은 원문에서도 Claude 평점이 달라졌고, GPT는 반복해서 같은 최고점을 줬습니다. 반복성·평가자 간 기준 차이·작은 차이의 구분력·임상 타당성은 각각 확인할 문제입니다.</Text>
  </Stack>
  <Stack gap={10}><H2>같은 고정 원문을 세 번 평가한 M5</H2>
   <Table headers={["판독자","동일한 반복 평점 쌍","세 번 모두 같은 원문","원문 내 최대 차이"]} rows={Object.entries(DATA.repeat).map(([p,r])=>[names[p],`${r.equal_pairs}/${r.all_pairs} (${(100*r.equal_pairs/r.all_pairs).toFixed(1)}%)`,`${r.all_three_equal_dialogues}/6대화`,`${r.max_within_text_pair_difference}점`])}/>
   <Text tone="secondary" size="small">분모: 원본 6대화·3프로필·모델별 18평점. 18개 비교 쌍은 같은 원문/라운드를 공유하므로 18개 독립 표본이 아닙니다. GPT 원본 18평점은 전부 4점이었습니다. 출처: M5 scores.json, 원평정 2026-11-18.</Text>
   <Row gap={12}><Text>판독자별 원평점</Text><Select value={judge} onChange={setJudge} options={[{value:"claude",label:names.claude},{value:"codex",label:names.codex}]}/></Row>
   <Table headers={["고정 대화","1차","2차","3차"]} rows={DATA.originals.map(r=>[r.id,...(judge==="claude"?r.claude:r.codex)])}/>
  </Stack>
  <Stack gap={10}><H2>고정 자료에서도 평균 차이가 달라졌습니다</H2>
   <Table headers={["M5 반복 라운드","v0.2 평균 /4","v0.4 평균 /4","v0.4−v0.2 /점"]} rows={DATA.rounds.map(r=>[r.round,f(r.means.v02),f(r.means.v04),f(r.v04_minus_v02)])}/>
   <Text tone="secondary" size="small">각 조건은 고정된 3대화 × 2평가자의 산술평균입니다. 동점→하락으로 달라졌으며 부호가 반대로 뒤집힌 결과는 아닙니다. 이 범위를 일반적인 측정오차 한계나 임상적으로 의미 있는 차이로 사용할 수 없습니다.</Text>
  </Stack>
  <Stack gap={10}><H2>평가자 간 점수 분포와 한 평점의 영향</H2>
   <Row gap={12}><Text>실험 선택</Text><Select value={stage} onChange={setStage} options={DATA.stages.map(x=>({value:String(x.stage),label:`M${x.stage}`}))}/></Row>
   <Table headers={["조건","대화 수","GPT 1/2/3/4점 개수","Claude 1/2/3/4점 개수","두 평가자의 동일 점수","원평점1점 변화의 평균 영향"]} rows={Object.entries(s.conditions).map(([v,c])=>[labels[v]??v,c.dialogues,[1,2,3,4].map(n=>c.score_counts.codex[String(n)]??0).join(" / "),[1,2,3,4].map(n=>c.score_counts.claude[String(n)]??0).join(" / "),`${c.exact_between_judge_agreement}/${c.dialogues}`,`${f(c.one_integer_rating_point_effect_on_condition_mean)}점`])}/>
   <Text tone="secondary" size="small">영향은 1/(2×대화 수)의 산술값입니다. 측정오차·검출 한계·신뢰구간이 아닙니다. M3~M9는 서로 다른 생성 원문이며 질문/판독 과제도 일부 바뀌어 단계 평균을 동일 원문의 반복 평정으로 비교할 수 없습니다. 같은 개발 프로필은3개입니다.</Text>
  </Stack>
  <Stack gap={10}><H2>다음 계획과 실행 여부</H2>
   <Table headers={["단계","할 일","판단 조건","현재 상태"]} rows={DATA.plan.map(x=>[x.step,x.action,x.decision,x.status])}/>
   <Text>이번 재검토에서는 새 환자 발화·새 Realism 평점을 만들지 않았습니다. 기존 두 평가자·산술평균과 원자료는 보존합니다. 최종720회 판독·미사용12프로필·전문의 평정은 미실시입니다.</Text>
  </Stack>
  <Text tone="secondary" size="small">출처: collaboration/strategy/M10-astra-measurement-review-v01/measurement-audit.json·decision.md·실제 Astra/Claude 응답. 두 모델의 전략 비평은 독립 임상의 검증이나 새로운 수치 평정이 아닙니다.</Text>
 </Stack>;
}
'''
 (HERE/'patient-speech-measurement-audit.canvas.tsx').write_text(source.replace('__DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':'))))
 print('Built measurement audit canvas from existing actual ratings and completed direction decisions')
if __name__=='__main__':main()
