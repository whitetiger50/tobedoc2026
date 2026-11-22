from pathlib import Path
from collections import Counter
import json
HERE=Path(__file__).resolve().parent

def measure(s):
 return {'alpha':s['ordinal_alpha']['value'],'Do':s['ordinal_alpha'].get('observed_disagreement'),'De':s['ordinal_alpha'].get('expected_disagreement'),'matches':s['exact_numeric_pair_matches'],'pairs':s['numeric_pair_count'],'all3':s['all3equal_texts'],'complete':s['complete_texts_for_ICC'],'icc1':s['ICC_primary_exploratory_oneway']['ICC11'],'icck':s['ICC_primary_exploratory_oneway']['ICC1k'],'sd':s['ICC_primary_exploratory_oneway'].get('within_text_SD'),'A1':s['ICC_twoway_sensitivity'].get('A1')}
def main():
 s=json.loads((HERE/'results.json').read_text());c=json.loads((HERE/'corpus.json').read_text());by={r['item_id']:r for r in c['items']};rby={r['item_id']:r for r in s['items']}
 names={'codex':'GPT-6.1 Sol High','claude':'Claude Opus 5.5'};dnames={'grounding':'사실근거','responsiveness':'질문대응','continuity':'연속성·공개흐름','naturalness':'당사자 표현'}
 data={'completion':s['completion'],'global':[{'label':names[p],**measure(s['within_models'][p]['realism'])} for p in names]+[{'label':'두 모델 평균 /회차',**measure(s['aggregate_repeatability'])}],'strata':[],'facets':[],'controls':[],'contrasts':[],'lopo':[],'items':[]}
 for p in names:
  for group,x in s['strata'][p].items():data['strata'].append({'label':names[p],'group':'4턴 원문6개' if group=='four_turn' else '8턴 원문6개',**measure(x)})
  for d in dnames:
   x=s['within_models'][p][d];counts=Counter()
   for row in x['round_score_counts']:counts.update(row)
   miss=s['dimension_missingness'][p][d]
   data['facets'].append({'label':names[p],'facet':dnames[d],'counts':[counts.get(str(k),0) for k in [0,1,2]],'uncertain':miss['uncertain_true'],'NA':miss['state_counts'].get('NA',0),'technical_missing':miss['state_counts'].get('technical_missing',0),**measure(x)})
  for case,x in s['leave_one_profile_out_descriptive'][p].items():data['lopo'].append({'label':names[p],'omitted':case,**measure(x)})
 for row in s['control_probes']:
  for p,v in row['judges'].items():
   data['controls'].append({'label':names[p],'control':row['control_id'],'parent':row['parent_id'],'baseline':rby[row['parent_id']]['judges'][p]['global_scores'],'scores':[r['realism_score'] for r in v['readings']],'grounding':[r['grounding_rating'] for r in v['readings']],'target_hits':sum(r['clear_grounding_at_target_with_living_ref'] for r in v['readings'])})
 for row in s['contrasts']:
  data['contrasts'].append({'case':row['case_id'],'stage':row['stage'],'baseline':row['baseline_id'],'candidate':row['candidate_id'],'directions':{p:[v['candidate_lower'],v['tie'],v['candidate_higher']] for p,v in row['judges'].items()}})
 for item in s['items']:
  src=by[item['item_id']];row={'id':item['item_id'],'case':item['case_id'],'kind':item['kind'],'parent':item['parent_id'],'mean':item['six_rating_mean'],'facts':[f['content'] for f in src['payload']['patient_profile']['facts']],'understanding':src['payload']['patient_profile']['self_understanding'],'prior':src['payload']['prior_authored_context'],'dialogue':src['payload']['dialogue'],'judges':{}}
  for p,judged in item['judges'].items():
   readings=[]
   for r in judged['readings']:
    facets=[]
    for d,n in dnames.items():
     x=r.get('facets',{}).get(d,{})
     if x.get('rating')!=2 or x.get('uncertain'):
      facets.append({'name':n,'rating':x.get('rating'),'uncertain':x.get('uncertain'),'reason':x.get('reason') or '', 'evidence':[{'turn':e.get('patient_turn_id') or '', 'quote':e.get('quote') or '', 'valid':e.get('valid_quote',False)} for e in x.get('evidence',[])]})
    readings.append({'score':r.get('realism_score'),'reason':r.get('realism_reason') or '', 'facetScores':[r.get('facets',{}).get(d,{}).get('rating') for d in dnames],'findings':facets})
   row['judges'][p]=readings
  data['items'].append(row)
 source='''import { Stack, Row, Grid, H1, H2, H3, Text, Table, Select, useState, useHostTheme } from "cursor/canvas";
type Measure={alpha:number|null;Do:number|null;De:number|null;matches:number;pairs:number;all3:number;complete:number;icc1:number|null;icck:number|null;sd:number|null;A1:number|null};
type Finding={name:string;rating:number|null;uncertain:boolean|null;reason:string;evidence:{turn:string;quote:string;valid:boolean}[]};
type Reading={score:number|null;reason:string;facetScores:(number|null)[];findings:Finding[]};
type Item={id:string;case:string;kind:string;parent:string|null;mean:number|null;facts:string[];understanding:string;prior:{speaker:string;text:string}[];dialogue:{turn_id:string;speaker:string;text:string}[];judges:Record<string,Reading[]>};
const DATA:{completion:{expected_responses:number;recorded_responses:number;valid_primary_scores:number;fully_schema_valid_responses:number;quote_errors:number;schema_errors:number};global:(Measure&{label:string})[];strata:(Measure&{label:string;group:string})[];facets:(Measure&{label:string;facet:string;counts:number[];uncertain:number;NA:number;technical_missing:number})[];controls:{label:string;control:string;parent:string;baseline:(number|null)[];scores:(number|null)[];grounding:(number|null)[];target_hits:number}[];contrasts:{case:string;stage:string;baseline:string;candidate:string;directions:Record<string,number[]>}[];lopo:(Measure&{label:string;omitted:string})[];items:Item[]}=__DATA__;
const names:Record<string,string>={codex:"GPT-6.1 Sol High",claude:"Claude Opus 5.5"};
const f=(n:number|null)=>n===null?"미정의":n.toFixed(3);const scores=(a:(number|null)[])=>a.map(x=>x===null?"결측/NA":String(x)).join(" · ");
export default function RaterReliability(){
 const theme=useHostTheme();const [selected,setSelected]=useState(DATA.items[0].id);const item=DATA.items.find(i=>i.id===selected)??DATA.items[0];
 return <Stack gap={26} style={{padding:24,maxWidth:1280,color:theme.text.primary}}>
  <Stack gap={8}><H1>M12 · 대화별 새 세션의 평가 신뢰도</H1><Text>2026-11-19 · 자연 원문12개 + 작성자 대조3개 × GPT/Claude × 3회 · 고정 개발 프로필3개</Text>
   <Row gap={32} wrap><Stack gap={4}><H2>{DATA.completion.recorded_responses}/90</H2><Text>실제 수신 판독</Text></Stack><Stack gap={4}><H2>{DATA.completion.valid_primary_scores}/90</H2><Text>유효1–4점 총점</Text></Stack><Stack gap={4}><H2>{DATA.completion.quote_errors}건</H2><Text>인용 불일치</Text></Stack></Row>
   <Text>높은 전체 반복성 계수와 미세한 대화 차이의 구분력을 함께 확인합니다. GPT의 자연 총점은 모두4점이며, Claude의8턴층은 대부분3점입니다. 이 결과는 선정 개발 원문과 새 통합 판독체계에 조건부입니다.</Text>
  </Stack>
  <Stack gap={10}><H2>자연12개만의 반복성 · 대조는 제외</H2>
   <Text>주된 목표는 동일 모델의 반복 판독 일관성입니다. 이 고정 표본에서 높은 단순 반복 일치를 확인했습니다. 모델 간 점수 차이 자체를 실패 조건으로 삼지 않으며, 미세한 차이를 구분할 수 있는지는 별도로 확인합니다.</Text>
   <Table headers={["측정","정확 일치쌍","세번 모두 동일","ordinal α","ICC(1,1)","ICC(1,3)","대화 내 SD/점"]} rows={DATA.global.map(x=>[x.label,`${x.matches}/${x.pairs}`,`${x.all3}/12`,f(x.alpha),f(x.icc1),f(x.icck),f(x.sd)])}/>
   <Text tone="secondary" size="small">출처: M12실제원평정·results.json. ICC는 등간점수 가정의 보조분석이며 일원 측정모형입니다. 교환 가능한 세션이라는 가정과 블록시간 변화 가능성을 명시했고 이원A는 민감도로 보존했습니다. ICC(1,3)은3회평균이며 단회운영의 근거가 아닙니다. 반복쌍36개는12원문에서 나온 비독립 비교입니다.</Text>
   <Text>GPT가 상수4이면 두 모델 평균은2+Claude/2이므로 상대 반복성 계수는 같고 절대 변동은 절반입니다. 평균이 새로운 독립 판단을 만들지는 않습니다.</Text>
  </Stack>
  <Stack gap={10}><H2>모델 간 총점 일치 · 자연12개</H2>
   <Table headers={["명목 회차","정확 일치","GPT−Claude 평균/점","선형가중 κ","고정모델 ICC(A,1)"]} rows={[["1회","6/12","0.500","0.000","0.000"],["2회","5/12","0.583","0.000","0.000"],["3회","5/12","0.583","0.000","0.000"]]}/>
   <Text>총점 일치는 합계16/36=44.44%이고 GPT가 평균0.556점 높았습니다. 이36쌍은12원문을 반복 비교한 것입니다. GPT가 상수여서 관측/기대 불일치가 같아 κ=0이며 임상 정답률0이라는 뜻은 아닙니다. 모델내 반복성이 높아도 모델간 기준의 일치는 확보되지 않았습니다.</Text>
  </Stack>
  <Stack gap={10}><H2>4턴·8턴층을 나누면</H2>
   <Table headers={["모델","원문층","정확 일치쌍","ordinal α","ICC(1,1)","D_o","D_e"]} rows={DATA.strata.map(x=>[x.label,x.group,`${x.matches}/${x.pairs}`,f(x.alpha),f(x.icc1),f(x.Do),f(x.De)])}/>
   <Text tone="secondary" size="small">층마다6원문·3프로필입니다. 생성단계·질문·길이가 함께 다르므로 길이 효과로 귀속하지 않습니다. 8턴Claude는 한 원문의4·3·3 외에 모두3점이어서 높은 단순 일치와 α0이 공존합니다. 상수/낮은 범위에서의 미정의를1로 바꾸지 않습니다.</Text>
  </Stack>
  <Stack gap={10}><H2>저자 정의 보조4축 · 자연 원문만</H2>
   <Table headers={["모델","축","0 · 1 · 2 개수 /36","불확실true","NA / 기술결측","정확 일치쌍","ordinal α"]} rows={DATA.facets.map(x=>[x.label,x.facet,x.counts.join(" · "),x.uncertain,`${x.NA} / ${x.technical_missing}`,`${x.matches}/${x.pairs}`,f(x.alpha)])}/>
   <Text tone="secondary" size="small">0실질문제·1경미한확인문제·2문제미지적이며 불확실성과NA는 별도입니다. 검증된 임상 척도가 아니고 총합/평균을 만들지 않았습니다. 축을 나눈 것만으로 분산·타당성이 생기지는 않습니다. 자연성의 반복 지적은 임상 정답을 뜻하지 않습니다.</Text>
  </Stack>
  <Stack gap={10}><H2>동거 사실 반전3개 · 단독 세션의 대조 반응</H2>
   <Table headers={["모델","대조","원본 총점3회","조작 총점3회","조작 사실근거3회","표적턴+living근거+0점"]} rows={DATA.controls.map(x=>[x.label,x.control,scores(x.baseline),scores(x.scores),scores(x.grounding),`${x.target_hits}/3판독`])}/>
   <Text tone="secondary" size="small">세 작성자 조작을18번 판독한 결과이며18독립 오류나 임상 오류 탐지율이 아닙니다. 원본과조작은 다른세션입니다. Claude사례3은 총점이3점동점이지만 사실축은2→0으로 변했습니다. 주총점과 특정설정충실도는 같은 지표가 아닙니다.</Text>
  </Stack>
  <Stack gap={10}><H2>사전 지정6개 고정텍스트 대비</H2>
   <Table headers={["기준 원문 → 비교 원문","GPT: 낮음/동점/높음","Claude: 낮음/동점/높음"]} rows={DATA.contrasts.map(x=>[`${x.baseline} → ${x.candidate}`,x.directions.codex.join(" / "),x.directions.claude.join(" / ")])}/>
   <Text tone="secondary" size="small">각 모델3×3재호출 점수를 재사용한9조합입니다.9독립표본이 아니고 프롬프트 일반적 승패가 아닙니다. 동점은 강제승패로 바꾸지 않았습니다.</Text>
  </Stack>
  <Stack gap={12}><H2>원문·원점수·실제 지적 확인</H2>
   <Select value={selected} onChange={setSelected} options={DATA.items.map(x=>({value:x.id,label:`${x.id}${x.kind!=="natural"?" · 작성자 조작":" · 기존 생성 원문"}`}))}/>
   <Text>{item.kind==="natural"?"기존 GPT 생성 원문을 그대로 재평가했습니다.":`작성자가 ${item.parent}의 한 환자턴만 바꾼 조작이며 새 모델 생성이 아닙니다.`} 6개 총점 평균: {f(item.mean)} /4</Text>
   <Table headers={["모델","총점1·2·3","사실근거1·2·3","질문대응1·2·3","연속성1·2·3","당사자표현1·2·3"]} rows={Object.entries(item.judges).map(([p,rs])=>[names[p],scores(rs.map(r=>r.score)),...[0,1,2,3].map(j=>scores(rs.map(r=>r.facetScores[j])))])}/>
   <Grid columns={2} gap={24}>
    <Stack gap={8}><H3>합성 프로필과 이전 문맥</H3>{item.facts.map((fact,i)=><div key={`fact${i}`}><Text>{fact}</Text></div>)}<Text tone="secondary">자기 이해: {item.understanding}</Text>{item.prior.map((x,i)=><div key={`prior${i}`}><Text size="small">{x.speaker}: {x.text}</Text></div>)}</Stack>
    <Stack gap={8}><H3>이번 대화 원문</H3>{item.dialogue.map(x=><div key={x.turn_id}><Text tone={x.speaker==="patient"?"primary":"secondary"} size="small">{x.turn_id} {x.speaker==="patient"?"환자":"의사"}: {x.text}</Text></div>)}</Stack>
   </Grid>
   <Grid columns={2} gap={24}>{Object.entries(item.judges).map(([p,rs])=><div key={p}><Stack gap={14}><H3>{names[p]} 실제 이유</H3>{rs.map((r,j)=><div key={j}><Stack gap={6}><Text weight="medium">{j+1}회 · 총점{r.score??"결측"}</Text><Text size="small">{r.reason}</Text>{r.findings.map((d,k)=><div key={k}><Text size="small">{d.name} {d.rating??"NA"} · 불확실 {d.uncertain?"예":"아니오"}: {d.reason}</Text>{d.evidence.map((ev,q)=><div key={q}><Text tone="secondary" size="small">{ev.turn}: “{ev.quote}” {ev.valid?"원문일치":"인용불일치"}</Text></div>)}</div>)}</Stack></div>)}</Stack></div>)}</Grid>
  </Stack>
  <Stack gap={10}><H2>프로필 하나 제외 · 기술 민감도</H2>
   <Table headers={["모델","제외한 프로필","ordinal α","ICC(1,1)"]} rows={DATA.lopo.map(x=>[x.label,x.omitted,f(x.alpha),f(x.icc1)])}/>
   <Text tone="secondary" size="small">3개 제외 결과는95%신뢰구간이 아닙니다. 현재 고정3프로필로 모집단 정밀도·새프로필 신뢰도·임상 타당성을 확보했다고 하지 않습니다.</Text>
  </Stack>
  <Text>이번 절차의 수신·파싱·인용 검증은 완료됐습니다. 자연 총점의 미세순위는 충분히 검증되지 않았으므로 작은 점수차에 맞춘 프롬프트 경쟁과 최종720으로 넘어가지 않습니다. 판단기준을 명료화할 별도 교정자료와 최종12를 제외한 별도 개발 검증자료가 다음 평가개발 과제입니다.</Text>
  <Text tone="secondary" size="small">출처: methods.md·freeze.json·results.json·90개 원응답·interpretation.md·verification.json, 2026-11-19. 새 환자발화·새판독모델·임상평정·최종720 실행은 없습니다. 과거묶음판독과 다중요소가 함께 달라져 전후 개선효과를 주장하지 않습니다.</Text>
 </Stack>;
}
'''
 (HERE/'patient-speech-rater-reliability-m12.canvas.tsx').write_text(source.replace('__DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':'))))
 print('Built M12 actual90-rating canvas;bytes',(HERE/'patient-speech-rater-reliability-m12.canvas.tsx').stat().st_size)
if __name__=='__main__':main()
