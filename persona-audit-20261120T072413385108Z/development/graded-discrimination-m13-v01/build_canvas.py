"""Render actual M13 raw ratings, profiles and controlled texts as a standalone canvas."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
NAMES={'codex':'GPT-6.1 Sol High','claude':'Claude Opus 5.5'}
CONDITIONS=['R','I','F1','F2','N1','N2']
LABELS={'R':'생성 기준원문','I':'의미보존 편집','F1':'사소한 미설정 세부','F2':'핵심 사실 반전','N1':'국소 격식 표현','N2':'설정 보고·역할 이탈'}
def main():
    s=json.loads((HERE/'results.json').read_text());c=json.loads((HERE/'corpus.json').read_text())
    assert s['completion']['recorded_responses']>0
    cases=sorted({i['case_id'] for i in c['items']});items=[]
    sources={i['item_id']:i for i in c['items']};result={i['item_id']:i for i in s['items']}
    for src in c['items']:
        row=result[src['item_id']];judges={}
        for p in NAMES:
            readings=[]
            for r in row['judges'][p]['readings']:
                fs=[]
                for key,label in [('grounding','사실근거'),('responsiveness','질문대응'),('continuity','연속성'),('naturalness','당사자 표현')]:
                    x=r.get('facets',{}).get(key,{})
                    fs.append({'name':label,'rating':x.get('rating'),'uncertain':x.get('uncertain'),
                               'reason':x.get('reason') or '', 'evidence':[{'turn':e.get('patient_turn_id') or '',
                               'quote':e.get('quote') or '', 'valid':e.get('valid_quote',False)} for e in x.get('evidence',[])]})
                readings.append({'score':r.get('realism_score'),'reason':r.get('realism_reason') or '', 'facets':fs})
            judges[p]=readings
        items.append({'id':src['item_id'],'case':src['case_id'],'condition':src['condition'],'label':LABELS[src['condition']],
                     'target':next(t['text'] for t in src['payload']['dialogue'] if t['turn_id']=='P02'),
                     'chars':src['target_characters'],'eojeol':src['target_eojeol'],'mean':row['six_score_mean'],'judges':judges})
    profiles=[]
    for case in cases:
        src=next(i for i in c['items'] if i['case_id']==case and i['condition']=='R')
        profiles.append({'id':case,'facts':[v['content'] for v in src['payload']['patient_profile']['facts']],
                         'self':src['payload']['patient_profile']['self_understanding'],'dialogue':src['payload']['dialogue']})
    means=[{'label':NAMES.get(p,'두 모델 평균'),'values':[v[cond] for cond in CONDITIONS],
            'withoutCase2':[s['case02_omitted_descriptive']['condition_means'][p][cond] for cond in CONDITIONS]}
           for p,v in s['condition_means'].items()]
    repeat=[]
    for p in NAMES:
        v=s['repeatability'][p]['realism']['all_conditions']
        repeat.append({'label':NAMES[p],'matches':v['exact_numeric_pair_matches'],'pairs':v['numeric_pair_count'],
                       'all3':v['all3equal_texts'],'alpha':v['ordinal_alpha']['value'],
                       'icc':v['ICC_primary_exploratory_oneway']['ICC11']})
    comparisons=[]
    for row in s['contrasts']:
        if (row['baseline'],row['candidate']) not in [('R','I'),('R','F1'),('F1','F2'),('R','F2'),('R','N1'),('N1','N2'),('R','N2')]:continue
        for p in NAMES:
            v=row['judges'][p]['realism']
            comparisons.append({'case':row['case_id'],'label':NAMES[p],'a':row['baseline'],'b':row['candidate'],
                                'lower':v['candidate_lower'],'tie':v['tie'],'higher':v['candidate_higher'],
                                'category':v['descriptive_class']})
    findings=[]
    for row in s['target_findings']:
        for p in NAMES:
            v=row['judges'][p]
            findings.append({'case':row['case_id'],'label':NAMES[p],'condition':row['condition'],
                'target':v['mechanical_target_findings'],'any':v['secondary_any_facet_marker_findings'],
                'ratings':[r['numeric_rating'] for r in v['readings']]})
    data={'completion':s['completion'],'means':means,'repeat':repeat,'items':items,'profiles':profiles,
          'comparisons':comparisons,'findings':findings}
    source='''import { Stack, Row, Grid, H1, H2, H3, Text, Table, Select, useState, useHostTheme } from "cursor/canvas";
type Facet={name:string;rating:number|null;uncertain:boolean|null;reason:string;evidence:{turn:string;quote:string;valid:boolean}[]};
type Reading={score:number|null;reason:string;facets:Facet[]};
type Item={id:string;case:string;condition:string;label:string;target:string;chars:number;eojeol:number;mean:number|null;judges:Record<string,Reading[]>};
type Profile={id:string;facts:string[];self:string;dialogue:{turn_id:string;speaker:string;text:string}[]};
const DATA:{completion:{recorded_responses:number;expected_responses:number;valid_primary_scores:number;fully_schema_valid_responses:number;quote_errors:number;schema_errors:number};means:{label:string;values:(number|null)[];withoutCase2:(number|null)[]}[];repeat:{label:string;matches:number;pairs:number;all3:number;alpha:number|null;icc:number|null}[];items:Item[];profiles:Profile[];comparisons:{case:string;label:string;a:string;b:string;lower:number;tie:number;higher:number;category:string}[];findings:{case:string;label:string;condition:string;target:number;any:number;ratings:(number|null)[]}[]}=__DATA__;
const names:Record<string,string>={codex:"GPT-6.1 Sol High",claude:"Claude Opus 5.5"};
const f=(v:number|null)=>v===null?"미정의/결측":v.toFixed(3);
const points=(xs:(number|null)[])=>xs.map(v=>v===null?"결측":v).join(" · ");
export default function GradedDiscrimination(){
 const theme=useHostTheme();const [caseId,setCaseId]=useState(DATA.profiles[0].id);const [condition,setCondition]=useState("R");
 const profile=DATA.profiles.find(p=>p.id===caseId)??DATA.profiles[0];const selected=DATA.items.find(x=>x.case===caseId&&x.condition===condition)??DATA.items[0];const caseItems=DATA.items.filter(x=>x.case===caseId);
 return <Stack gap={28} style={{padding:24,maxWidth:1280,color:theme.text.primary}}>
  <Stack gap={10}><H1>M13 · 고정 평가체계의 단계 대조 구분력</H1><Text>2026-11-19 · 신규 개발 프로필3개 · 8턴 기준원문3개와 작성자편집15개 · GPT/Claude각3회</Text>
   <Row gap={36} wrap><Stack gap={4}><H2>{DATA.completion.recorded_responses}/108</H2><Text>실제 수신 판독</Text></Stack><Stack gap={4}><H2>{DATA.completion.valid_primary_scores}/108</H2><Text>유효1–4점 총점</Text></Stack><Stack gap={4}><H2>{DATA.completion.quote_errors}건</H2><Text>인용 불일치</Text></Stack></Row>
   <Text>같은 평가자의 반복 일관성과 정한 편집에 대한 반응을 구별합니다. 모델 간 점수를 같게 맞추는 것이 목표는 아닙니다. 환자v0.2와 M12평가역할·앵커·파서는 그대로이며 최종12사례는 쓰지 않았습니다.</Text>
  </Stack>
  <Stack gap={10}><H2>조건별 총점 · 모델별3회·3프로필의 기술 평균</H2>
   <Table headers={["판독자 /1–4점","R 원문","I 의미보존","F1 미설정세부","F2 사실반전","N1 격식","N2 역할이탈"]} rows={DATA.means.map(x=>[x.label,...x.values.map(f)])}/>
   <Text tone="secondary" size="small">R이4점정답이라는 가정은 없습니다. F1/F2는 종류·핵심성, N1/N2는격식·인칭·역할이함께달라 저자정의단계이지 임상서열gold가아닙니다. 평균은보조이며 아래세원점수/동점/역전을함께봅니다. 출처:M13실제108판독·results.json.</Text>
  </Stack>
  <Stack gap={10}><H2>원문별3회 판단의 반복 일관성</H2>
   <Table headers={["판독자","정확 반복쌍","세번 모두 동일 /18","ordinal α","탐색ICC(1,1)"]} rows={DATA.repeat.map(x=>[x.label,`${x.matches}/${x.pairs}`,`${x.all3}/18`,f(x.alpha),f(x.icc)])}/>
   <Text tone="secondary" size="small">반복쌍은독립시행이아닙니다. 전체계수는큰조작으로원문간분산이넓어질수있어M12보다신뢰도가개선됐다는뜻이아닙니다. 계수의미정의는1로바꾸지않았습니다.3프로필조건부기술값이며모집단CI/임상타당성없음.</Text>
  </Stack>
  <Stack gap={12}><H2>프로필별 원점수와 실제 편집</H2>
   <Select value={caseId} onChange={setCaseId} options={DATA.profiles.map(p=>({value:p.id,label:p.id+(p.id.endsWith("02")?" · 판독전개정/기저둘이문제":"")}))}/>
   <Table headers={["조건","P02실제문구","글자/어절","GPT1·2·3","Claude1·2·3","6평점평균"]} rows={caseItems.map(x=>[`${x.condition} ${x.label}`,x.target,`${x.chars}/${x.eojeol}`,points(x.judges.codex.map(r=>r.score)),points(x.judges.claude.map(r=>r.score)),f(x.mean)])}/>
   <Text tone="secondary" size="small">편집은P02한턴만이고나머지7환자턴·의사말·프로필은동일합니다. R은실제GPT생성,다른조건은작성자편집이며새모델생성이아닙니다. 서로다른표현15종을독립환자15명으로세지않습니다.</Text>
  </Stack>
  <Stack gap={10}><H2>인접·양끝 대비 · 같은3평정의9재사용조합</H2>
   <Table headers={["판독자","기준→조작","총점낮음","동점","높음"]} rows={DATA.comparisons.filter(x=>x.case===caseId).map(x=>[x.label,`${x.a} → ${x.b}`,x.lower,x.tie,x.higher])}/>
   <Text tone="secondary" size="small">각행9조합은6개기존평정재사용이며9독립실험이아닙니다. 양끝하락이인접모든단계의구분을뜻하지않고,동점은역전이아니지만미세구분증거도아닙니다. F1/N1총점동점은그자체로실패가아닙니다.</Text>
  </Stack>
  <Stack gap={10}><H2>편집 지목 · 총점과 분리한 진단</H2>
   <Table headers={["판독자","조건","목표축0·1+P02+변경토큰 /3","임의축동일표지 /3","목표축세원점수"]} rows={DATA.findings.filter(x=>x.case===caseId).map(x=>[x.label,x.condition,`${x.target}/3`,`${x.any}/3`,points(x.ratings)])}/>
   <Text tone="secondary" size="small">F목표축grounding,N목표축naturalness. 기계표지는정확P02인용과변경단어·0/1점을함께요구합니다. 실제의미해석정확성/임상오류탐지율은아닙니다. N2역할이탈은continuity에도예상중첩됩니다. 사례2의‘둘이’만지적하면F1층수탐지로세지않습니다.</Text>
  </Stack>
  <Stack gap={12}><H2>원문·근거를 나란히 읽기</H2>
   <Select value={condition} onChange={setCondition} options={caseItems.map(x=>({value:x.condition,label:`${x.condition} · ${x.label}`}))}/>
   <Grid columns={2} gap={24}>
    <Stack gap={8}><H3>새 합성 프로필</H3>{profile.facts.map((v,i)=><div key={i}><Text size="small">{v}</Text></div>)}<Text tone="secondary" size="small">자기이해: {profile.self}</Text></Stack>
    <Stack gap={8}><H3>{selected.condition}의 실제 대화</H3>{profile.dialogue.map(t=><div key={t.turn_id}><Text size="small" tone={t.speaker==="patient"?"primary":"secondary"}>{t.turn_id} {t.speaker==="patient"?"환자":"의사"}: {t.turn_id==="P02"?selected.target:t.text}</Text></div>)}</Stack>
   </Grid>
   <Grid columns={2} gap={24}>{Object.entries(selected.judges).map(([p,rs])=><div key={p}><Stack gap={14}><H3>{names[p]} 실제판독</H3>{rs.map((r,j)=><div key={j}><Stack gap={6}><Text weight="medium">{j+1}회 · 총점{r.score??"결측"}</Text><Text size="small">{r.reason}</Text>{r.facets.map((x,k)=><div key={k}><Text size="small">{x.name} {x.rating??"NA/결측"} · 불확실{x.uncertain?"예":"아니오"}: {x.reason}</Text>{x.evidence.map((ev,q)=><div key={q}><Text size="small" tone="secondary">{ev.turn}: “{ev.quote}” {ev.valid?"원문일치":"인용불일치"}</Text></div>)}</div>)}</Stack></div>)}</Stack></div>)}</Grid>
  </Stack>
  <Stack gap={10}><H2>사례2 제외 · 사전지정 기술 민감도</H2>
   <Table headers={["판독자 /2프로필평균","R","I","F1","F2","N1","N2"]} rows={DATA.means.map(x=>[x.label,...x.withoutCase2.map(f)])}/>
   <Text>사례2원문의‘둘이’는프로필밖가구원수구체화일수있습니다. I/N이이명제를생략하는문제로원래적격성실패/중단규칙예외가있었고,점수를보기전명제보존개정후동결했습니다. 원규칙준수/완전한생성전사전등록으로쓰지않습니다. 전체결과를버리지않고두프로필민감도를함께보입니다. 추가자극수정/재판독없음.</Text>
  </Stack>
  <Text tone="secondary" size="small">자료:methods.md·freeze.json·reference-audit.json·108개원응답·results.json·verification.json,2026-11-19.3새프로필/한위치/저자조작조건부. 실제환자/전문의gold/임상타당성/최종720/미세프롬프트우월성없음. 근거개념:CheckList의invariance/directionalexpectation행동검사,한국어조현병척도타당성근거아님.</Text>
 </Stack>;
}
'''
    out=HERE/'patient-speech-discrimination-m13.canvas.tsx'
    out.write_text(source.replace('__DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':'))))
    print('Built actual M13 canvas,bytes',out.stat().st_size)
if __name__=='__main__':main()
