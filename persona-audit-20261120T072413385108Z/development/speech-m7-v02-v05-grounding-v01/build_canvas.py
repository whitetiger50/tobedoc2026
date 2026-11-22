"""Offline report for actual v02/v05 generated dialogues and grounding judgments."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def read(p):return json.loads(p.read_text())
def pick(v,keys):return {k:v[k] for k in keys.split()}


def main():
    plan=read(HERE/'plan.json');scores=read(HERE/'scores.json');key=read(HERE/'review-key-private.json')
    reviews={p:{key[r['blind_id']]['item_id']:r for r in read(HERE/'reviews'/p/'validated.json')['reviews']} for p in ('codex','claude')}
    cases=[]
    for config,group in zip(plan['cases'],scores['cases']):
        assert config['case_id']==group['case_id']
        case={'id':config['case_id'],'facts':[pick(f,'id content') for f in config['input']['patient']['facts']],
              'self_understanding':config['input']['patient']['self_understanding'],'communication':config['input']['communication'],
              'authored_context':config['input']['history'],'stats':{v:group[v]['combined_scores'] for v in ('v02','v05')},'replicates':[]}
        for rep in (1,2,3):
            row={'replicate':rep}
            for v in ('v02','v05'):
                t=read(HERE/'runs'/config['case_id']/f'rep{rep:02d}'/v/'transcript.json')
                item=next(r for r in scores['items'] if r['item_id']==t['item_id'])
                judged={}
                for p in ('codex','claude'):
                    r=reviews[p][t['item_id']];g=r['grounding_review']
                    judged[p]=dict(pick(r,'score reason uncertainty'),
                        grounding=dict(pick(g,'checked_turn_ids status uncertainty'),findings=[pick(f,'patient_turn_id quote kind fact_ids explanation') for f in g['findings']]),
                        issues=[pick(i,'id severity patient_turn_id quote issue suggestion') for i in r['issues']])
                row[v]={'mean':item['mean'],'scores':item['scores'],'dialogue':t['generated_dialogue'],'reviews':judged}
            case['replicates'].append(row)
        cases.append(case)
    summary={p:{v:{'dialogues':g['dialogues'],'status_counts':g['status_counts'],'finding_count':g['finding_count']} for v,g in versions.items()} for p,versions in scores['grounding_summary'].items()}
    data={'means':scores['condition_means'],'delta':scores['v05_minus_v02'],'judge_means':scores['judge_condition_means'],'grounding':summary,'cases':cases}
    source='''import { Stack, Row, Grid, H1, H2, H3, Text, Table, Select, useState, useHostTheme } from "cursor/canvas";
type Turn={turn_id:string;speaker:string;text:string};
type Finding={patient_turn_id:string;quote:string;kind:string;fact_ids:string[];explanation:string};
type Review={score:number;reason:string;uncertainty:string;grounding:{checked_turn_ids:string[];status:string;uncertainty:string;findings:Finding[]};issues:{id:string;severity:string;patient_turn_id:string;quote:string;issue:string;suggestion:string}[]};
type Condition={mean:number;scores:Record<string,number>;dialogue:Turn[];reviews:Record<string,Review>};
type Desc={values:number[];mean:number;min:number;max:number;range:number;sample_sd:number};
type Rep={replicate:number;v02:Condition;v05:Condition};
type Case={id:string;facts:{id:string;content:string}[];self_understanding:string;communication:Record<string,string>;authored_context:{speaker:string;text:string}[];stats:{v02:Desc;v05:Desc};replicates:Rep[]};
type Ground={dialogues:number;status_counts:Record<string,number>;finding_count:number};
const DATA:{means:Record<string,number>;delta:number;judge_means:Record<string,Record<string,number>>;grounding:Record<string,Record<string,Ground>>;cases:Case[]}=__DATA__;
const names:Record<string,string>={codex:"GPT-6.1 Sol High",claude:"Claude Opus 5.5"};
const status:Record<string,string>={no_issue_identified:"이번 검토에서 문제 미지적",concern:"근거 문제 후보",uncertain:"불확실"};
const kind:Record<string,string>={unsupported_detail:"미설정 세부",scope_shift:"사실 범위 확장",contradiction:"설정 모순",causal_inference:"인과 추론",uncertain:"불확실"};
const fmt=(n:number)=>n.toFixed(2);const delta=(n:number)=>(n>0?"+":"")+fmt(n);
export default function GroundingComparison(){
 const theme=useHostTheme();const [selected,setSelected]=useState(DATA.cases[0].id);const [rep,setRep]=useState("1");const [judge,setJudge]=useState("claude");
 const c=DATA.cases.find(c=>c.id===selected)??DATA.cases[0];const r=c.replicates.find(r=>r.replicate===Number(rep))??c.replicates[0];
 const questions=r.v02.dialogue.filter(t=>t.speaker==="clinician"),a=r.v02.dialogue.filter(t=>t.speaker==="patient"),b=r.v05.dialogue.filter(t=>t.speaker==="patient");
 return <Stack gap={24} style={{padding:24,maxWidth:1250,color:theme.text.primary}}>
  <Stack gap={8}><H1>v0.2 → v0.5 · 사실 범위만 수정한 비교</H1>
   <Text>2026-11-18 · 같은 합성 개발 3사례 × 2버전 × 새 생성 3회 · 18대화·72발화 · 두 모델 각 단회 검토·36평점</Text>
   <Text tone="secondary">v0.5는 v0.2에 시간·빈도·확신·사건 관계의 근거를 보존하는 세 문단만 추가했습니다. 정보 공개·반복 규칙과 사례 입력은 유지했습니다. 환자 발화 사후 편집은 없습니다.</Text>
  </Stack>
  <Row gap={36} wrap><Stack gap={4}><H2>{fmt(DATA.means.v02)} / 4</H2><Text>v0.2 평균</Text></Stack><Stack gap={4}><H2>{fmt(DATA.means.v05)} / 4</H2><Text>v0.5 평균</Text></Stack><Stack gap={4}><H2>{delta(DATA.delta)}점</H2><Text>v0.5 − v0.2</Text></Stack></Row>
  <Stack gap={10}><H2>모델별 사실 근거 관찰 · 각 조건 9대화</H2>
   <Table headers={["평가자·버전","문제 미지적","문제 후보","불확실","지적 수"]}
    rows={Object.entries(DATA.grounding).flatMap(([p,versions])=>Object.entries(versions).map(([v,g])=>[`${names[p]} · ${v==="v02"?"v0.2":"v0.5"}`,`${g.status_counts.no_issue_identified??0}/9`,`${g.status_counts.concern??0}/9`,`${g.status_counts.uncertain??0}/9`,g.finding_count]))}/>
   <Text tone="secondary" size="small">각 모델에 P01~P04의 근거 대조를 요청하고 받은 관찰입니다. 문제 미지적은 오류가 없다는 임상적 보증이 아닙니다. v0.2에서도 0건이면 양쪽 0건으로 오류 감소 효과를 입증할 수 없습니다. 출처: M7 실제 원응답·scores.json, 2026-11-18.</Text>
  </Stack>
  <Stack gap={10}><H2>세 생성물의 원평점·평균·변동</H2>
   <Table headers={["사례·버전","GPT 1·2·3회","Claude 1·2·3회","두 모델 평균 1·2·3회","그룹 평균 ± 표본 SD","최소–최대"]}
    rows={DATA.cases.flatMap(c=>(["v02","v05"] as const).map(v=>{const s=c.stats[v];return [`사례 ${c.id.slice(-1)} · ${v==="v02"?"v0.2":"v0.5"}`,c.replicates.map(r=>r[v].scores.codex).join(" · "),c.replicates.map(r=>r[v].scores.claude).join(" · "),s.values.map(fmt).join(" · "),`${fmt(s.mean)} ± ${fmt(s.sample_sd)}`,`${fmt(s.min)}–${fmt(s.max)}`];}))}/>
   <Text tone="secondary" size="small">각 대화는 두 정수 평점의 산술평균입니다. 버전 평균은 세 사례에 같은 가중치를 줬습니다. 생성물의 점수 변동에는 단회 판독 변동도 포함됩니다. 과거 M6/M5 점수는 합치지 않았습니다.</Text>
  </Stack>
  <Stack gap={10}><H2>원문과 같은 평가자의 지적</H2>
   <Row gap={12} wrap><Select value={selected} onChange={setSelected} options={DATA.cases.map(c=>({value:c.id,label:`사례 ${c.id.slice(-1)}`}))}/><Select value={rep} onChange={setRep} options={[1,2,3].map(i=>({value:String(i),label:`새 생성 ${i}`}))}/><Select value={judge} onChange={setJudge} options={Object.entries(names).map(([value,label])=>({value,label}))}/></Row>
   <Table headers={["동일 질문","v0.2 환자 원문","v0.5 환자 원문"]} rows={questions.map((q,i)=>[q.text,a[i].text,b[i].text])}/>
   <details><summary style={{cursor:"pointer",color:theme.text.link}}>고정 사실·자기 이해·의사소통·시작 이력</summary><Stack gap={8} style={{paddingTop:12}}>
    <Text>{c.self_understanding}</Text>{c.facts.map(f=><div key={f.id}><Text>{f.id}: {f.content}</Text></div>)}
    {Object.entries(c.communication).map(([k,v])=><div key={k}><Text>{k}: {v}</Text></div>)}
    {c.authored_context.map((t,i)=><div key={i}><Text>{t.speaker}: {t.text}</Text></div>)}
   </Stack></details>
  </Stack>
  <Grid columns="repeat(auto-fit, minmax(300px, 1fr))" gap={28}>
   {(["v02","v05"] as const).map(v=>{const j=r[v].reviews[judge];return <div key={v}><Stack gap={12} style={{borderTop:`1px solid ${theme.stroke.tertiary}`,paddingTop:12}}>
    <H3>{v==="v02"?"v0.2":"v0.5"} · {j.score}/4</H3><Text>{j.reason}</Text>
    <Text weight="semibold">사실 근거: {status[j.grounding.status]??j.grounding.status}</Text>
    {j.grounding.findings.map((f,i)=><div key={i}><Stack gap={6} style={{borderLeft:`2px solid ${theme.stroke.secondary}`,paddingLeft:12}}>
     <Text weight="semibold">{f.patient_turn_id} · {kind[f.kind]??f.kind}</Text><Text>“{f.quote}”</Text><Text>{f.explanation}</Text><Text tone="secondary" size="small">참조 사실 ID: {f.fact_ids.length?f.fact_ids.join(", "):"직접 대응 사실 없음"}</Text>
    </Stack></div>)}
    <Text tone="secondary">근거 점검의 불확실성: {j.grounding.uncertainty}</Text>
    {j.issues.map(i=><div key={i.id}><Stack gap={6}><Text weight="semibold">현실성 지적 · {i.patient_turn_id} · {i.severity}</Text><Text>“{i.quote}”</Text><Text>{i.issue}</Text><Text tone="secondary">검토자 제안: {i.suggestion}</Text></Stack></div>)}
    <Text tone="secondary">현실성 판단의 불확실성: {j.uncertainty}</Text>
   </Stack></div>;})}
  </Grid>
  <Stack gap={8}><H2>해석 범위</H2><Text>같은 합성 개발 프로필 3개에서 얻은 기술적 비교입니다. 18대화가 독립 환자 18명은 아니며, 모델의 사실 지적은 임상 정답이나 전문가 평정이 아닙니다. 낮은 오류 빈도에서 동점·0건은 최적화·동등성·오류 감소의 입증이 아닙니다.</Text>
   <Text>단회 평가의 이유와 모든 인용은 실제 파일에 보존했습니다. 유사 대화가 같은 묶음에 있어 완전한 독립 제시·눈가림을 보장하지 않습니다. GPT 생성·판독은 같은 계열입니다. 불변 서버 스냅샷·temperature·seed는 CLI에 노출되지 않습니다.</Text>
   <Text tone="secondary" size="small">외부 유료 API·새 모델·새 패키지·실제 환자 자료·전문의 검증·최종 720회 판독은 없습니다. 기존 공개·반복 규칙의 텍스트는 유지했지만 생성 행동도 같다는 뜻은 아닙니다. 평정 후 프롬프트는 수정하지 않았습니다.</Text>
  </Stack>
 </Stack>;
}
'''
    (HERE/'patient-speech-v02-v05-grounding.canvas.tsx').write_text(source.replace('__DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':'))))
    print('Canvas built from 18 actual dialogues, 36 ratings and all grounding findings')


if __name__=='__main__':main()
