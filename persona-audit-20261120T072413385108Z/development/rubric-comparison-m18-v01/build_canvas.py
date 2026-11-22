"""Presentation only. Embeds actual completed data, never calls a model."""
import json
from common import HERE,read

NAMES={'codex':'GPT-6.1 Sol High','claude':'Claude Opus5.5'}
CRITERIA={'realism':'기존 Realism','ccf':'CCF-R1'}
FACETS={'grounding':'사실근거','responsiveness':'질문대응','continuity':'연속성','naturalness':'당사자표현'}
LABELS={'N':'자연 원문·D04 재확인','P':'원문 동일 별칭','G':'경험 재지칭','U':'내용 재사용+미대응','F':'형식 반복+보고말투','X':'역할 실패 표적'}

def main():
    result=read(HERE/'results.json');corpus=read(HERE/'corpus.json');notes=read(HERE/'author-prejudge-audit.json')
    interpretation=read(HERE/'interpretation-summary.json')
    source={r['item_id']:r for r in corpus['items']};note={r['item_id']:r for r in notes['rows']};items=[]
    for row in result['items']:
        original=source[row['item_id']];cells={}
        for criterion in CRITERIA:
            cells[criterion]={}
            for provider in NAMES:
                readings=[]
                for r in row['cells'][criterion][provider]['readings']:
                    if r is None:continue
                    v=r['validated'];facets=[]
                    for key,label in FACETS.items():
                        f=v.get('facets',{}).get(key,{})
                        facets.append({'label':label,'rating':f.get('rating'),'uncertain':f.get('uncertain'),
                          'reason':f.get('reason')or'' if f.get('rating')in[0,1] or f.get('uncertain') else '',
                          'evidence':[{'turn':e.get('patient_turn_id')or'','quote':e.get('quote')or'',
                                       'valid':e.get('valid_quote',False)} for e in f.get('evidence',[])]})
                    readings.append({'score':r['score'],'reason':v.get('realism_reason')or'',
                      'facets':facets,'target':r['target_flags']['record_state'],
                      'schema':v.get('fully_schema_valid',False),'boundary':v.get('ccf_extra',{}).get('boundary_34',{}).get('flag'),
                      'source':r['source']})
                cells[criterion][provider]=readings
        items.append({'id':row['item_id'],'case':row['case_id'],'label':LABELS[row['condition']],
          'kind':row['kind'],'alias':row['semantic_id']!=row['item_id'],'semantic':row['semantic_id'],
          'facts':[f['content'] for f in original['payload']['patient_profile']['facts']],
          'dialogue':original['payload']['dialogue'],'notes':note[row['item_id']]['notes'],
          'status':note[row['item_id']]['status'],'cells':cells})
    natural=[];targets=[]
    for g in result['groups']:
        st=g['statistics'];ceiling=g['ceiling4'];eligible=g['eligible_target_counts']
        common={'criterion':CRITERIA[g['criterion']],'provider':NAMES[g['provider']],
          'mean':g['mean'],'same':st['exact_numeric_pair_matches'],'pairs':st['numeric_pair_count'],
          'all3':st['all3equal_texts'],'n':len(g['item_ids']),'alpha':st['ordinal_alpha']['value'],
          'icc':st['ICC_primary_exploratory_oneway']['ICC11'],'ceiling':ceiling['n'],'ceilingN':ceiling['denominator']}
        if g['stratum']=='natural':natural.append(common)
        if g['stratum']in['natural','G','U','F','X']:
            targets.append(dict(common,label=LABELS['N' if g['stratum']=='natural' else g['stratum']],
              texts=eligible['texts'],assessable=eligible['assessable'],target=eligible['target_problem_explicit'],
              planned=eligible['planned_readings'],returned=eligible['returned_readings'],
              lexical=eligible['repeat_lexical_candidate'],unobserved=eligible['no_explicit_target_problem'],
              states=' / '.join(f'{k}:{v}'for k,v in g['target_record_states'].items())))
    vectors=[]
    for i in result['items']:
        if i['condition']=='N':vectors.append({'id':i['item_id'],'cells':{c:{p:i['cells'][c][p]['scores']for p in NAMES}for c in CRITERIA}})
    data={'completion':result['completion'],'natural':natural,'targets':targets,'vectors':vectors,
      'items':items,'findings':interpretation['findings'],'limits':interpretation['limits']}
    source_text='''import { Stack, Grid, H1, H2, H3, Text, Table, Select, useState } from "cursor/canvas";
type Reading={score:number|null;reason:string;facets:{label:string;rating:number|null;uncertain:boolean|null;reason:string;evidence:{turn:string;quote:string;valid:boolean}[]}[];target:string;schema:boolean;boundary:boolean|null;source:string};
type Item={id:string;case:string;label:string;kind:string;alias:boolean;semantic:string;facts:string[];dialogue:{turn_id:string;speaker:string;text:string}[];notes:string[];status:string;cells:Record<string,Record<string,Reading[]>>};
type Overall={criterion:string;provider:string;mean:number|null;same:number;pairs:number;all3:number;n:number;alpha:number|null;icc:number|null;ceiling:number;ceilingN:number};
type Target=Overall&{label:string;texts:number;assessable:number;planned:number;returned:number;target:number;lexical:number;unobserved:number;states:string};
const DATA:{completion:Record<string,number>;natural:Overall[];targets:Target[];vectors:{id:string;cells:Record<string,Record<string,(number|null)[]>>}[];items:Item[];findings:string[];limits:string[]}=__DATA__;
const f=(x:number|null)=>x===null?"미정의/결측":x.toFixed(3);
const triple=(a:(number|null)[])=>a.map(x=>x??"결측").join(" · ");
const pct=(a:number,b:number)=>b?`${(100*a/b).toFixed(1)}%`:"적용 불가";
export default function Comparison(){
 const [selected,setSelected]=useState(DATA.items[0].id);const [provider,setProvider]=useState("claude");
 const item=DATA.items.find(i=>i.id===selected)??DATA.items[0];
 return <Stack gap={28} style={{padding:26,maxWidth:1380,margin:"0 auto"}}>
 <Stack gap={10}><Text tone="secondary" size="small">M18 · 2026-11-19 · 3개 새 합성 개발 프로필 · 환자v0.2 고정</Text><H1>같은 대화의 기존 Realism · CCF-R1 비교</H1><Text>9개 새 생성 대화/72환자턴 + 작성자15조건. 원문동일3별칭을공유해21고유입력×2기준×2모델×3새세션=252판독을계획했습니다. 실제수신 {DATA.completion.recorded}/252, 유효총점 {DATA.completion.numeric_valid}, 인용오류 {DATA.completion.quote_errors}건입니다.</Text></Stack>
 <Stack gap={9}><H2>관찰 결과와 판단 범위</H2>{DATA.findings.map((s,i)=><div key={i}><Text>{s}</Text></div>)}</Stack>
 <Stack gap={10}><H2>자연9원문 · 동일 모델 내부의 반복 일관성</H2><Table headers={["판독자","기준","평균 /4","정확반복쌍","세번동일/원문","순서형 α","탐색ICC(1,1)","4점/유효평점"]} rows={DATA.natural.map(x=>[x.provider,x.criterion,f(x.mean),`${x.same}/${x.pairs} (${pct(x.same,x.pairs)})`,`${x.all3}/${x.n}`,f(x.alpha),f(x.icc),`${x.ceiling}/${x.ceilingN} (${pct(x.ceiling,x.ceilingN)})`])}/><Text size="small" tone="secondary">출처: M18 results.json · 새 자연 원문만. 세쌍은원문내종속입니다. 상수일치100%는관측정보이나미세변별력을입증하지않고α/ICC는미정의입니다. ICC는등간가정의보조값이며모집단CI/임상통과선이아닙니다.</Text></Stack>
 <Stack gap={10}><H2>같은 자연 원문의 실제 세 판독값</H2><Table headers={["원문","GPT 기존","GPT CCF","Claude 기존","Claude CCF"]} rows={DATA.vectors.map(x=>[x.id,triple(x.cells.realism.codex),triple(x.cells.ccf.codex),triple(x.cells.realism.claude),triple(x.cells.ccf.claude)])}/></Stack>
 <Stack gap={10}><H2>사전 표적의 명시 지적 · 공통 출력만</H2><Table headers={["표적","판독자/기준","성립원문"," 지적/예정","판정가능","반복어휘후보","정상미관찰","전체조건의기록상태"]} rows={DATA.targets.map(x=>[x.label,`${x.provider} / ${x.criterion}`,x.texts,`${x.target}/${x.planned}`,x.assessable,x.lexical,x.unobserved,x.states])}/><Text size="small" tone="secondary">P3별칭은자연D04판독공유이며별도조작효과가아닙니다. U사례3은사전부분성립으로주표적분모에서분리했지만원점수는보존했습니다. 기록상태열은부분성립을포함한전체조건반환수라주표적분모와다를수있습니다. ClaudeCCF의G는4/9지적과5/9불확실언급이며5건을정상무언급으로세지않습니다. G는경험재지칭,U는미대응,F는형식/보고말투,X는역할단서입니다. 지적에는반복외의문제도포함될수있으며어휘후보는의미정답이아닙니다. 조작정렬점검이며임상과잉/누락률이아닙니다.</Text></Stack>
 <Stack gap={10}><H2>조건별 최고점 집중 · 대조에서도4점인가</H2><Table headers={["조건","판독자/기준","4점/전체조건유효평점","비율"]} rows={DATA.targets.map(x=>[x.label,`${x.provider} / ${x.criterion}`,`${x.ceiling}/${x.ceilingN}`,pct(x.ceiling,x.ceilingN)])}/><Text size="small" tone="secondary">이표는각조건전체점수입니다. 위표의성립표적분모와다를수있습니다. 전체4와표적문제지적이함께있으면숫자만보고탐지누락으로세지않습니다.</Text></Stack>
 <Stack gap={12}><H2>원문·두 기준·실제 판독 근거</H2><Select value={selected} onChange={setSelected} options={DATA.items.map(x=>({value:x.id,label:`${x.id} · ${x.label}${x.alias?" · 판독공유":""}`}))}/><Text>유형: {item.kind==="natural_generated"?"실제v0.2새생성":"작성자대조"} · 사전표적: {item.status}{item.alias?` · ${item.semantic}와동일입력/동일판독공유`:""}</Text>
 <Select value={provider} onChange={setProvider} options={[{value:"claude",label:"Claude Opus5.5"},{value:"codex",label:"GPT-6.1 Sol High"}]}/>
 <Table headers={["기준","총점1·2·3","사실근거","질문대응","연속성","당사자표현"]} rows={["realism","ccf"].map(c=>[c==="realism"?"기존 Realism":"CCF-R1",triple(item.cells[c][provider].map(r=>r.score)),...[0,1,2,3].map(k=>triple(item.cells[c][provider].map(r=>r.facets[k].rating)))])}/>
 <Grid columns={2} gap={24}><Stack gap={8}><H3>고정 합성 설정</H3>{item.facts.map((s,i)=><div key={i}><Text size="small">{s}</Text></div>)}<H3>판독 전 작성자 노트</H3>{item.notes.map((s,i)=><div key={i}><Text size="small" tone="secondary">{s}</Text></div>)}</Stack><Stack gap={8}><H3>이번 평가에 실제 제시한 대화</H3>{item.dialogue.map(t=><div key={t.turn_id}><Text size="small" tone={t.speaker==="patient"?"primary":"secondary"}>{t.turn_id}: {t.text}</Text></div>)}</Stack></Grid>
 <Grid columns={2} gap={24}>{["realism","ccf"].map(c=><div key={c}><Stack gap={14}><H3>{c==="realism"?"기존 Realism":"CCF-R1"} 실제 이유</H3>{item.cells[c][provider].map((r,i)=><div key={i}><Stack gap={7}><Text weight="medium">{i+1}회 · 총점{r.score??"결측"} · 형식{r.schema?"통과":"오류기록"}{r.boundary?" · 3/4경계표지":""}</Text><Text size="small">{r.reason}</Text>{r.facets.filter(x=>x.reason).map((x,k)=><div key={k}><Text size="small">{x.label} {x.rating??"NA/결측"}{x.uncertain?" · 불확실":""}: {x.reason}</Text>{x.evidence.map((e,j)=><div key={j}><Text size="small" tone="secondary">{e.turn}: “{e.quote}” {e.valid?"원문일치":"인용불일치"}</Text></div>)}</div>)}<Text size="small" tone="secondary">표적기록: {r.target}</Text></Stack></div>)}</Stack></div>)}</Grid></Stack>
 <Stack gap={9}><H2>해석의 한계</H2>{DATA.limits.map((s,i)=><div key={i}><Text size="small" tone="secondary">{s}</Text></div>)}<Text size="small" tone="secondary">출처: generation-freeze.json·72실제생성응답·author-prejudge-audit.json·freeze.json·252계획원응답·results.json·author-claim-extraction.json·verification.json. 최종12내용미열람/720미실행·환자/두역할문구불변입니다.</Text></Stack>
 </Stack>;
}
'''
    target=HERE/'patient-speech-rubric-comparison-m18.canvas.tsx'
    target.write_text(source_text.replace('__DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':')))+'\n')
    checker=(HERE.parent/'rater-reliability-m12-v01/check_canvas.cjs').read_text().replace('patient-speech-rater-reliability-m12.canvas.tsx',target.name)
    (HERE/'check_canvas.cjs').write_text(checker)
    print('Built actual-data M18 canvas',target.stat().st_size,'bytes')

if __name__=='__main__':main()
