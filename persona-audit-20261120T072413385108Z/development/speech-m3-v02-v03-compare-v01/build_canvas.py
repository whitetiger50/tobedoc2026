"""Embed actual frozen results and transcripts in a single offline Codex Canvas."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def main():
    scores=json.loads((HERE/'scores.json').read_text())
    plan=json.loads((HERE/'plan.json').read_text())
    reviews={p:json.loads((HERE/'reviews'/p/'validated.json').read_text()) for p in ['codex','claude']}
    index={p:{r['blind_id']:r for r in v['reviews']} for p,v in reviews.items()}
    titles={'DEV-M0-01':'사례 1 · 조직적인 반응과 보존된 병식',
            'DEV-M0-02':'사례 2 · 정보 전달에 대한 경계',
            'DEV-M0-03':'사례 3 · 방송의 신호 해석과 연상'}
    cases=[]
    for row,config in zip(scores['cases'],plan['cases']):
        assert row['case_id']==config['case_id']
        output={'id':row['case_id'],'title':titles[row['case_id']],'delta':row['delta_v03_minus_v02'],
                'facts':config['input']['patient']['facts'],'self_understanding':config['input']['patient']['self_understanding'],
                'communication':config['input']['communication'],'authored_context':config['input']['history']}
        for label in ['v02','v03']:
            transcript=json.loads((HERE/'runs'/row['case_id']/label/'transcript.json').read_text())
            output[label]={'mean':row[label]['mean'],'original_scores':row[label]['original_scores'],
                           'dialogue':transcript['generated_dialogue'],
                           'reviews':{p:{k:index[p][row[label]['blind_id']][k] for k in ['score','reason','issues','uncertainty']} for p in reviews}}
        cases.append(output)
    data={'scores':{k:scores[k] for k in ['condition_means','delta_v03_minus_v02','judge_specific_means']},'cases':cases}
    source='''import { Stack, Row, Grid, H1, H2, H3, Text, Table, Select, useState, useHostTheme } from "cursor/canvas";
type Turn = {turn_id:string;speaker:string;text:string};
type Issue = {id:string;severity:string;patient_turn_id:string;quote:string;issue:string;suggestion:string};
type Review = {score:number;reason:string;issues:Issue[];uncertainty:string};
type Condition = {mean:number;original_scores:{codex:number;claude:number};dialogue:Turn[];reviews:{codex:Review;claude:Review}};
type Case = {id:string;title:string;delta:number;facts:{id:string;kind:string;content:string;patient_knows:boolean;disclosure:string}[];self_understanding:string;communication:Record<string,string>;authored_context:{speaker:string;text:string}[];v02:Condition;v03:Condition};
type Scores = {condition_means:{v02:number;v03:number};delta_v03_minus_v02:number;judge_specific_means:Record<string,{v02:number;v03:number;delta_v03_minus_v02:number}>};
const DATA: {scores:Scores;cases:Case[]} = __DATA__;
const fmt=(n:number)=>n.toFixed(2);
const delta=(n:number)=>(n>0?"+":"")+fmt(n);
export default function PatientSpeechComparison(){
 const theme=useHostTheme();
 const [selected,setSelected]=useState(DATA.cases[0].id);
 const [judge,setJudge]=useState("claude");
 const chosen=DATA.cases.find(c=>c.id===selected)??DATA.cases[0];
 const provider: "codex"|"claude"=judge==="codex"?"codex":"claude";
 const questions=chosen.v02.dialogue.filter(t=>t.speaker==="clinician");
 const answers02=chosen.v02.dialogue.filter(t=>t.speaker==="patient");
 const answers03=chosen.v03.dialogue.filter(t=>t.speaker==="patient");
 return <Stack gap={24} style={{padding:24,maxWidth:1200,color:theme.text.primary}}>
  <Stack gap={8}><H1>v0.3의 개발 점수 개선은 확인되지 않았습니다</H1>
   <Text>2026-11-18 · 동일 합성 개발 3사례 × 2버전 × 4턴 · GPT-6.1 Sol High 생성 · 각 검토자 1회</Text>
   <Text tone="secondary">설정·질문·시작 이력·생성 모델은 동일합니다. 이후에는 각 조건 자신의 실제 답을 누적했습니다. 예시는 두 조건 모두 사용하지 않았습니다.</Text>
  </Stack>
  <Row gap={36} wrap>
   <Stack gap={4}><H2>{fmt(DATA.scores.condition_means.v02)} / 4</H2><Text>v0.2 두 모델·세 사례 평균</Text></Stack>
   <Stack gap={4}><H2>{fmt(DATA.scores.condition_means.v03)} / 4</H2><Text>v0.3 두 모델·세 사례 평균</Text></Stack>
   <Stack gap={4}><H2>{delta(DATA.scores.delta_v03_minus_v02)}점</H2><Text>v0.3 − v0.2</Text></Stack>
  </Row>
  <Stack gap={8}><H2>사례별 원평점과 산술평균</H2>
   <Table headers={["사례","v0.2 GPT / Claude","v0.2 평균","v0.3 GPT / Claude","v0.3 평균","차이 (점)"]}
    rows={DATA.cases.map(c=>[c.title,`${c.v02.original_scores.codex} / ${c.v02.original_scores.claude}`,fmt(c.v02.mean),`${c.v03.original_scores.codex} / ${c.v03.original_scores.claude}`,fmt(c.v03.mean),delta(c.delta)])}
    columnAlign={["left","center","right","center","right","right"]}/>
   <Text tone="secondary" size="small">PATIENTSIM Realism 1–4의 정신과 맥락 적용. 각 원평점은 단회 정수 평정이며 두 값의 평균을 계산했습니다. 출처: M3 원응답·scores.json, 2026-11-18.</Text>
   <Text>GPT는 6대화 모두 4점으로 동점입니다. Claude의 평균은 3.33→3.00점이며, 차이는 사례 2의 4→3점에서 생겼습니다. 더 큰 표본의 성능 저하를 확정하는 결과는 아닙니다.</Text>
  </Stack>
  <Stack gap={10}><H2>원문을 나란히 비교</H2>
   <Select value={selected} onChange={setSelected} options={DATA.cases.map(c=>({value:c.id,label:c.title}))}/>
   <Table headers={["동일 면담자 질문","v0.2 환자 원문","v0.3 환자 원문"]}
    rows={questions.map((q,i)=>[<Text size="small">{q.text}</Text>,<Text size="small">{answers02[i].text}</Text>,<Text size="small">{answers03[i].text}</Text>])}/>
   <details><summary style={{cursor:"pointer",color:theme.text.link}}>공통 환자 설정과 시작 이력</summary>
    <Stack gap={8} style={{paddingTop:12}}><Text>{chosen.self_understanding}</Text>
     {chosen.facts.map(f=><div key={f.id}><Text size="small">{f.id} · {f.content}</Text></div>)}
     {Object.entries(chosen.communication).map(([k,v])=><div key={k}><Text size="small">{k} · {v}</Text></div>)}
     {chosen.authored_context.map((t,i)=><div key={i}><Text size="small">작성 문맥 {t.speaker}: {t.text}</Text></div>)}
    </Stack>
   </details>
  </Stack>
  <Stack gap={12}><H2>같은 검토자의 판정 근거</H2>
   <Select value={judge} onChange={setJudge} options={[{value:"claude",label:"Claude Opus 5.5"},{value:"codex",label:"GPT-6.1 Sol High"}]}/>
   <Grid columns="repeat(auto-fit, minmax(280px, 1fr))" gap={24}>
    {(["v02","v03"] as const).map(label=>{
     const review=chosen[label].reviews[provider];
     return <div key={label}><Stack gap={10} style={{borderTop:`1px solid ${theme.stroke.tertiary}`,paddingTop:12}}>
      <H3>{label==="v02"?"v0.2":"v0.3"} · {review.score}/4</H3><Text>{review.reason}</Text>
      {review.issues.length>0&&<Stack gap={12}>{review.issues.map(issue=><div key={issue.id}><Stack gap={6}>
       <Text weight="semibold">{issue.patient_turn_id} · {issue.severity}</Text>
       <Text style={{borderLeft:`2px solid ${theme.stroke.secondary}`,paddingLeft:10}}>“{issue.quote}”</Text>
       <Text>{issue.issue}</Text><Text tone="secondary">검토자의 제안: {issue.suggestion}</Text>
      </Stack></div>)}</Stack>}
      {review.uncertainty!=="없음"&&<Text tone="secondary" size="small">불확실성: {review.uncertainty}</Text>}
     </Stack></div>;
    })}
   </Grid>
  </Stack>
  <Stack gap={8}><H2>해석과 다음 수정 후보</H2>
   <Text>v0.3의 문헌 대응을 명시한 설계 변화가 이번 생성에서 점수 향상으로 이어지지는 않았습니다. 공개 속도와 이미 공개한 정보의 재설명이 다음 확인 대상입니다. 검토자가 제안한 감정이나 인과를 설정 밖에서 추가하지 않습니다.</Text>
   <Text>사례 2의 빠른 공개를 GPT는 자연스럽다고 봤고 Claude는 더 낮게 평정했습니다. 모든 환자에게 공개 지연이나 ‘아까 말했듯이’ 같은 문구를 강제할 근거로 쓰지 않습니다.</Text>
   <Text tone="secondary">개발 3사례·조건당 생성 1회·모델별 단회 평정입니다. GPT는 생성 모델과 같고, 짝 관계를 추측할 수도 있습니다. 임상 타당성·최종 우월성·반복 안정성은 미확인입니다. 최종 720회 판독은 실행하지 않았습니다.</Text>
   <Text tone="secondary" size="small">세 사례의 보완 사실은 출력 전에 양쪽에 동일 적용했습니다. 과거 M1의 3.17점과 직접 비교하지 않습니다. 전송 실패·재선택 없이 24개 실제 발화를 보존했습니다. 출처: persona-audit/development/speech-m3-v02-v03-compare-v01.</Text>
  </Stack>
 </Stack>;
}
'''
    source=source.replace('__DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':')))
    with (HERE/'patient-speech-v02-v03.canvas.tsx').open('w',encoding='utf-8') as f:f.write(source)
    print('Canvas source built from actual scores, reviews and transcripts; 3 selectable paired cases.')


if __name__=='__main__':main()
