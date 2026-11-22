"""Display all eighteen new dialogues and their actual single-pass reviews."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def read(p): return json.loads(p.read_text())
def pick(v,keys): return {k:v[k] for k in keys.split()}


def main():
    scores=read(HERE/'scores.json');plan=read(HERE/'plan.json');key=read(HERE/'review-key-private.json')
    author=read(HERE/'author-flow-observations.json')['rows']
    index={p:{key[r['blind_id']]['item_id']:r for r in read(HERE/'reviews'/p/'validated.json')['reviews']} for p in ('codex','claude')}
    titles={'DEV-M0-01':'사례 1 · 조직적인 답변과 병식','DEV-M0-02':'사례 2 · 경계심과 정보 공개','DEV-M0-03':'사례 3 · 방송 연상과 일상 재질문'}
    case_rows=[]
    for case,group in zip(plan['cases'],scores['cases']):
        assert case['case_id']==group['case_id']
        observations=[]
        coded=[r for r in author if r['case_id']==case['case_id']]
        if case['case_id']=='DEV-M0-01':
            observations=[f"작성자 원문 관찰: P04에서 어머니 동거를 유지한 대화 {sum(r['reconfirmed_cohabitant']=='mother' for r in coded)}/6. 표현의 작은 차이가 있어도 재확인 사실은 유지됐습니다."]
        elif case['case_id']=='DEV-M0-02':
            for v,name in [('v02','v0.2'),('v04','v0.4')]:
                rows=[r for r in coded if r['condition']==v]
                observations.append(f"작성자 원문 관찰 {name}: 소리 경험의 첫 언급 P01 {sum(r['first_voice_experience_turn']=='P01' for r in rows)}/3, P03 {sum(r['first_voice_experience_turn']=='P03' for r in rows)}/3, 미공개 {sum(r['first_voice_experience_turn']=='none' for r in rows)}/3. 비밀보장 우려 자체와 소리/관찰 믿음 공개를 구분했습니다.")
            observations.append('v0.4의 P03은 두 대화에서 관찰당한다는 믿음을 추가하고, 한 대화에서 앞선 막연한 소리의 내용을 구체화했습니다. 미해결 우려를 되묻는 것 자체는 오류로 판정하지 않았습니다.')
        else:
            for v,name in [('v02','v0.2'),('v04','v0.4')]:
                rows=[r for r in coded if r['condition']==v]
                observations.append(f"작성자 원문 관찰 {name}: P02에서 오늘 산책까지 미리 언급 {sum(r['today_walk_already_mentioned_in_P02'] for r in rows)}/3; P03에서 이미 공개한 오늘 산책을 재확인 {sum(r['P03_reconfirms_previously_disclosed_today_walk'] for r in rows)}/3.")
            observations.append('v0.4 생성 1의 P03은 오늘의 기상 시점까지 구체화했습니다. 통상적인 오후 기상 설정만으로 오늘 기상 시점이 확정되지는 않아 근거 없는 구체화 우려로 남깁니다.')
        row={'id':case['case_id'],'title':titles[case['case_id']],'delta':group['v04_minus_v02'],'author_observations':observations,
             'facts':[pick(f,'id content') for f in case['input']['patient']['facts']],
             'self_understanding':case['input']['patient']['self_understanding'],
             'communication':case['input']['communication'],'authored_context':case['input']['history'],
             'stats':{v:group[v] for v in ('v02','v04')},'replicates':[]}
        for rep in (1,2,3):
            data={'replicate':rep}
            for v in ('v02','v04'):
                t=read(HERE/'runs'/case['case_id']/f'rep{rep:02d}'/v/'transcript.json')
                s=next(r for r in scores['items'] if r['item_id']==t['item_id'])
                reviews={}
                for p in ('codex','claude'):
                    r=index[p][t['item_id']]
                    flows={}
                    for field in ('disclosure_flow','repetition_flow'):
                        f=r[field]
                        flows[field]=dict(pick(f,'pattern explanation'),evidence=[pick(e,'patient_turn_id quote') for e in f['evidence']])
                        if 'first_sensitive_turn' in f:flows[field]['first_sensitive_turn']=f['first_sensitive_turn']
                    reviews[p]=dict(pick(r,'score reason uncertainty'),**flows,
                        issues=[pick(i,'id severity patient_turn_id quote issue suggestion') for i in r['issues']])
                data[v]={'mean':s['mean'],'scores':s['scores'],'dialogue':t['generated_dialogue'],'reviews':reviews}
            row['replicates'].append(data)
        case_rows.append(row)
    data={'means':scores['condition_means'],'delta':scores['v04_minus_v02'],
          'judge_means':scores['judge_condition_means'],'cases':case_rows}
    source='''import { Stack, Row, Grid, H1, H2, H3, Text, Table, Select, useState, useHostTheme } from "cursor/canvas";
type Turn={turn_id:string;speaker:string;text:string};
type Evidence={patient_turn_id:string;quote:string};
type Flow={pattern:string;explanation:string;evidence:Evidence[];first_sensitive_turn?:string};
type Review={score:number;reason:string;uncertainty:string;disclosure_flow:Flow;repetition_flow:Flow;issues:{id:string;severity:string;patient_turn_id:string;quote:string;issue:string;suggestion:string}[]};
type Desc={values:number[];mean:number;min:number;max:number;range:number;sample_sd:number};
type Stats={combined_scores:Desc;judges:Record<string,Desc>;unique_exact_patient_sequences:number;patient_characters:Desc;flow_counts:Record<string,Record<string,Record<string,number>>>};
type Condition={mean:number;scores:Record<string,number>;dialogue:Turn[];reviews:Record<string,Review>};
type Rep={replicate:number;v02:Condition;v04:Condition};
type Case={id:string;title:string;delta:number;author_observations:string[];facts:{id:string;content:string}[];self_understanding:string;communication:Record<string,string>;authored_context:{speaker:string;text:string}[];stats:{v02:Stats;v04:Stats};replicates:Rep[]};
const DATA:{means:Record<string,number>;delta:number;judge_means:Record<string,Record<string,number>>;cases:Case[]}=__DATA__;
const names:Record<string,string>={codex:"GPT-6.1 Sol High",claude:"Claude Opus 5.5"};
const labels:Record<string,string>={limited:"제한적 공개",partial_then_elaborated:"일부 공개 후 추가 설명",early_broad:"초기 다수 정보 공개",other:"기타",not_applicable:"비해당",uncertain:"불확실",brief_reconfirmation:"짧은 재확인",useful_elaboration:"관련 추가 설명",mechanical_replay:"기계적 되풀이",mixed:"혼합",no_repeated_topic:"반복 주제 없음"};
const fmt=(x:number)=>x.toFixed(2);
const delta=(x:number)=>(x>0?"+":"")+fmt(x);
const counts=(d:Record<string,number>)=>Object.entries(d).map(([k,n])=>`${labels[k]??k}: ${n}`).join(" / ");
export default function GenerationVariability(){
 const theme=useHostTheme();const [selected,setSelected]=useState(DATA.cases[0].id);const [rep,setRep]=useState("1");const [provider,setProvider]=useState("claude");
 const chosen=DATA.cases.find(c=>c.id===selected)??DATA.cases[0];
 const run=chosen.replicates.find(r=>r.replicate===Number(rep))??chosen.replicates[0];
 const questions=run.v02.dialogue.filter(t=>t.speaker==="clinician");
 const a=run.v02.dialogue.filter(t=>t.speaker==="patient"),b=run.v04.dialogue.filter(t=>t.speaker==="patient");
 return <Stack gap={24} style={{padding:24,maxWidth:1250,color:theme.text.primary}}>
  <Stack gap={8}><H1>고정 프롬프트의 생성 변동성 · v0.2 / v0.4</H1>
   <Text>2026-11-18 · 같은 합성 개발 3사례 × 2버전 × 새 시작 3회 · 18대화·72환자 발화 · 두 평가자 각 1회·36평점</Text>
   <Text tone="secondary">설정·질문·시작 이력·생성 모델(GPT-6.1 Sol High)을 유지했습니다. 매 대화는 독립 시작 후 자신의 실제 답변만 누적했습니다. 프롬프트와 모듈 구현은 수정하지 않았습니다.</Text>
  </Stack>
  <Row gap={36} wrap><Stack gap={4}><H2>{fmt(DATA.means.v02)} / 4</H2><Text>v0.2 평균</Text></Stack><Stack gap={4}><H2>{fmt(DATA.means.v04)} / 4</H2><Text>v0.4 평균</Text></Stack><Stack gap={4}><H2>{delta(DATA.delta)}점</H2><Text>v0.4 − v0.2</Text></Stack></Row>
  <Stack gap={10}><H2>사례별 세 생성물의 평점과 범위</H2>
   <Table headers={["사례·버전","생성 1·2·3 두 모델 평균","평균 ± 표본 SD","최소–최대","GPT 원평점","Claude 원평점"]}
    rows={DATA.cases.flatMap(c=>(["v02","v04"] as const).map(v=>{const s=c.stats[v];return [`사례 ${c.id.slice(-1)} · ${v==="v02"?"v0.2":"v0.4"}`,s.combined_scores.values.map(fmt).join(" · "),`${fmt(s.combined_scores.mean)} ± ${fmt(s.combined_scores.sample_sd)}`,`${fmt(s.combined_scores.min)}–${fmt(s.combined_scores.max)}`,s.judges.codex.values.join(" · "),s.judges.claude.values.join(" · ")];}))}/>
   <Text tone="secondary" size="small">출처: M6의 새 생성 18대화와 검증된 단회 원평점, 2026-11-18. 각 대화는 두 원평점의 산술평균이며 사례에 같은 가중치를 줬습니다. SD는 생성물에 부여된 점수의 표본 SD로, 단회 판독 변동도 포함합니다.</Text>
   <Table headers={["평가자","v0.2 평균","v0.4 평균","차이 (점)"]} rows={Object.entries(DATA.judge_means).map(([p,s])=>[names[p],fmt(s.v02),fmt(s.v04),delta(s.v04-s.v02)])}/>
  </Stack>
  <Stack gap={10}><H2>같은 사례의 원문과 흐름 비교</H2>
   <Row gap={12} wrap><Select value={selected} onChange={setSelected} options={DATA.cases.map(c=>({value:c.id,label:c.title}))}/><Select value={rep} onChange={setRep} options={[1,2,3].map(r=>({value:String(r),label:`새 생성 ${r}`}))}/></Row>
   <Table headers={["동일 질문","v0.2 환자 원문","v0.4 환자 원문"]} rows={questions.map((q,i)=>[q.text,a[i].text,b[i].text])}/>
   {chosen.author_observations.map((text,i)=><div key={i}><Text>{text}</Text></div>)}
   <Text tone="secondary" size="small">작성자 관찰은 두 모델의 평점 열람 전에 원문에서 기록했고 인용의 실제 존재를 확인했습니다. 임상의 평정이나 검증된 정답 라벨은 아닙니다.</Text>
   <Text tone="secondary" size="small">같은 생성 번호는 실행 블록입니다. 같은 난수 seed로 결합한 확률적 짝이 아닙니다. 이전 M4/M5 발화나 평점을 섞지 않았습니다.</Text>
   <details><summary style={{cursor:"pointer",color:theme.text.link}}>고정 환자 설정·의사소통·시작 이력</summary><Stack gap={8} style={{paddingTop:12}}>
    <Text>{chosen.self_understanding}</Text>{chosen.facts.map(f=><div key={f.id}><Text>{f.id}: {f.content}</Text></div>)}
    {Object.entries(chosen.communication).map(([k,v])=><div key={k}><Text>{k}: {v}</Text></div>)}
    {chosen.authored_context.map((t,i)=><div key={i}><Text>{t.speaker}: {t.text}</Text></div>)}
   </Stack></details>
  </Stack>
  <Stack gap={10}><H2>공개·반복 관찰: 세 생성물의 평가자별 분포</H2>
   <Select value={provider} onChange={setProvider} options={Object.entries(names).map(([value,label])=>({value,label}))}/>
   <Table headers={["버전","최초 민감 정보 턴","공개 흐름 분류","반복 흐름 분류","정확히 다른 답변 시퀀스 수","환자 문자 수 범위"]}
    rows={(["v02","v04"] as const).map(v=>{const s=chosen.stats[v],f=s.flow_counts[provider];return [v==="v02"?"v0.2":"v0.4",counts(f.first_sensitive_turn),counts(f.disclosure_flow),counts(f.repetition_flow),`${s.unique_exact_patient_sequences}/3`,`${s.patient_characters.min}–${s.patient_characters.max}자`];})}/>
   <Text tone="secondary" size="small">분류는 검증된 임상 척도가 아닌 관찰 범주입니다. 두 평가자가 비밀보장 우려 자체도 민감 정보에 포함한 경우가 있어, 위 작성자 관찰의 소리 경험 최초 공개 턴과 다를 수 있습니다. 초기 공개나 같은 질문에 대한 같은 사실 답변이 자동 오류는 아닙니다. 문자 수·정확한 문자열 차이는 의미적 다양성이나 품질 점수가 아닙니다.</Text>
  </Stack>
  <Grid columns="repeat(auto-fit, minmax(300px, 1fr))" gap={28}>
   {(["v02","v04"] as const).map(v=>{const r=run[v].reviews[provider];return <div key={v}><Stack gap={12} style={{borderTop:`1px solid ${theme.stroke.tertiary}`,paddingTop:12}}>
    <H3>{v==="v02"?"v0.2":"v0.4"} · 생성 {run.replicate} · {r.score}/4</H3><Text>{r.reason}</Text>
    {(["disclosure_flow","repetition_flow"] as const).map(field=>{const f=r[field];return <div key={field}><Stack gap={6}>
     <Text weight="semibold">{field==="disclosure_flow"?"공개":"반복"}: {labels[f.pattern]??f.pattern}{f.first_sensitive_turn?` · 최초 ${f.first_sensitive_turn}`:""}</Text><Text>{f.explanation}</Text>
     {f.evidence.map((e,i)=><div key={i}><Text size="small">{e.patient_turn_id}: “{e.quote}”</Text></div>)}
    </Stack></div>;})}
    {r.issues.map(i=><div key={i.id}><Stack gap={6}><Text weight="semibold">지적 · {i.patient_turn_id} · {i.severity}</Text><Text>“{i.quote}”</Text><Text>{i.issue}</Text><Text tone="secondary">검토자의 제안: {i.suggestion}</Text></Stack></div>)}
    <Text tone="secondary">불확실성: {r.uncertainty}</Text>
   </Stack></div>;})}
  </Grid>
  <Stack gap={8}><H2>해석 범위</H2>
   <Text>18대화는 같은 합성 프로필 3개에서 생성했습니다. 각 생성물에 단회 판독을 했으므로 점수 변동을 생성과 판독의 분산으로 분해하지 못합니다. 이전 고정 대화의 M5 반복성 결과를 보정값으로 빼지 않았습니다.</Text>
   <Text>동일한 18대화 묶음에서 버전·반복 번호·생성 모델과 과거 점수를 가렸습니다. 유사한 원문이 함께 있어 관련성을 알아볼 수 있고, 흐름 관찰 과제의 추가도 판독 문맥에 영향을 줄 수 있습니다. GPT 생성·판독은 같은 계열입니다.</Text>
   <Text tone="secondary" size="small">불변 모델 서버 스냅샷·temperature·seed는 CLI에 노출되지 않습니다. 새 환자 자료·전문의 검증·최종 720회 판독은 없으며 최적화·일반적 우월성·동등성을 주장하지 않습니다. 모든 원출력·입력·해시를 보존했고 결과에 따른 프롬프트 수정은 하지 않았습니다.</Text>
  </Stack>
 </Stack>;
}
'''
    (HERE/'patient-speech-generation-variability.canvas.tsx').write_text(source.replace('__DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':'))))
    print('Canvas built from all 18 real generated dialogues and 36 validated ratings')


if __name__=='__main__':main()
