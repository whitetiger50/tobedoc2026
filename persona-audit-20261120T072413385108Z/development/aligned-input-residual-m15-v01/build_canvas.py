"""Actual M15 dialogue, score and attribution viewer; no network/model calls."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
NAMES={'codex':'GPT-6.1 Sol High','claude':'Claude Opus 5.5'}
FACETS={'grounding':'사실근거','responsiveness':'질문대응','continuity':'연속성','naturalness':'당사자 표현'}
def main():
    s=json.loads((HERE/'results.json').read_text());c=json.loads((HERE/'corpus.json').read_text());a=json.loads((HERE/'author-prejudge-audit.json').read_text())
    by={i['item_id']:i for i in c['items']};items=[]
    for row in s['items']:
        source=by[row['item_id']];judges={}
        for p,j in row['judges'].items():
            readings=[]
            for r in j['readings']:
                fs=[]
                for f,label in FACETS.items():
                    x=r.get('facets',{}).get(f,{})
                    fs.append({'label':label,'rating':x.get('rating'),'uncertain':x.get('uncertain'),
                         'reason':x.get('reason') or '', 'evidence':[{'turn':v.get('patient_turn_id') or '',
                         'quote':v.get('quote') or '', 'valid':v.get('valid_quote',False)} for v in x.get('evidence',[])]})
                readings.append({'score':r.get('realism_score'),'reason':r.get('realism_reason') or '', 'facets':fs})
            judges[p]=readings
        items.append({'id':row['item_id'],'case':row['case_id'],'rep':row['generation_replicate'],'mean':row['six_rating_mean'],
             'facts':[v['content'] for v in source['payload']['patient_profile']['facts']],
             'self':source['payload']['patient_profile']['self_understanding'],'dialogue':source['payload']['dialogue'],'judges':judges})
    overall=[];profiles=[]
    for p in NAMES:
        r=s['repeatability'][p]['realism'];overall.append({'label':NAMES[p],'mean':s['model_means'][p],
             'matches':r['exact_numeric_pair_matches'],'pairs':r['numeric_pair_count'],'all3':r['all3equal_texts'],
             'alpha':r['ordinal_alpha']['value'],'icc':r['ICC_primary_exploratory_oneway']['ICC11']})
    for case,ps in s['per_profile'].items():
        for p,row in ps.items():
            if p not in [*NAMES,'two_model_mean']:continue
            profiles.append({'case':case,'label':NAMES.get(p,'두 모델 평균'),'means':row['generation_means'],
                 'mean':row['mean'],'sd':row['sample_SD_of_generation_means'],'min':row['min'],'max':row['max']})
    boundaries=[{'id':r['item_id'],'turn':r['patient_turn_id'],'quote':r['answer'],'reason':o['reason']} for r in a['turns'] for o in r['observations'] if o['category']=='boundary']
    attribution=json.loads((HERE/'issue-attribution.json').read_text()) if (HERE/'issue-attribution.json').exists() else {'events':[]}
    events=[{'id':x['item_id'],'turn':x['patient_turn_id'],'category':x['category'],'reason':x['reason'],'quote':x['quote']} for x in attribution['events']]
    data={'completion':s['completion'],'overall':overall,'mean':s['model_means']['two_model_mean'],'profiles':profiles,
          'items':items,'boundaries':boundaries,'events':events}
    source='''import { Stack, Row, Grid, H1, H2, H3, Text, Table, Select, useState, useHostTheme } from "cursor/canvas";
type Facet={label:string;rating:number|null;uncertain:boolean|null;reason:string;evidence:{turn:string;quote:string;valid:boolean}[]};
type Reading={score:number|null;reason:string;facets:Facet[]};
type Item={id:string;case:string;rep:number;mean:number|null;facts:string[];self:string;dialogue:{turn_id:string;speaker:string;text:string}[];judges:Record<string,Reading[]>};
const DATA:{completion:{expected_responses:number;recorded_responses:number;valid_primary_scores:number;fully_schema_valid_responses:number;quote_errors:number;schema_errors:number};overall:{label:string;mean:number|null;matches:number;pairs:number;all3:number;alpha:number|null;icc:number|null}[];mean:number|null;profiles:{case:string;label:string;means:(number|null)[];mean:number|null;sd:number|null;min:number|null;max:number|null}[];items:Item[];boundaries:{id:string;turn:string;quote:string;reason:string}[];events:{id:string;turn:string;category:string;reason:string;quote:string}[]}=__DATA__;
const names:Record<string,string>={codex:"GPT-6.1 Sol High",claude:"Claude Opus 5.5"};
const f=(x:number|null)=>x===null?"미정의/결측":x.toFixed(3);
const points=(v:(number|null)[])=>v.map(x=>x===null?"결측":x).join(" · ");
export default function AlignedInput(){
 const theme=useHostTheme();const [selected,setSelected]=useState(DATA.items[0].id);const item=DATA.items.find(x=>x.id===selected)??DATA.items[0];
 return <Stack gap={28} style={{padding:24,maxWidth:1280,color:theme.text.primary}}>
  <Stack gap={10}><H1>M15 · 정렬한 입력에서 남는 생성 문제</H1><Text>2026-11-19 · M13개발3프로필 × 독립생성3회 · 9대화/72환자턴 · GPT/Claude대화별새세션각3회</Text>
   <Row gap={36} wrap><Stack gap={4}><H2>{DATA.completion.recorded_responses}/54</H2><Text>실제 판독 응답</Text></Stack><Stack gap={4}><H2>{f(DATA.mean)}/4</H2><Text>두 모델·9대화 평균</Text></Stack><Stack gap={4}><H2>{DATA.completion.quote_errors}건</H2><Text>인용 불일치</Text></Stack></Row>
   <Text>환자v0.2·평가기준·파서는 유지했습니다. 질문24개 중 첫 질문의‘가장’3곳과 사례2의진료시점1곳을 생성전에 정렬했습니다. 환자사실·의사소통은 그대로이며 최종12사례는 쓰지 않았습니다.</Text>
  </Stack>
  <Stack gap={10}><H2>총점과 동일 원문의 반복 일관성</H2>
   <Table headers={["판독자","총점평균 /4","정확반복쌍","세번동일 /9","ordinal α","탐색ICC(1,1)"]} rows={DATA.overall.map(x=>[x.label,f(x.mean),`${x.matches}/${x.pairs}`,`${x.all3}/9`,f(x.alpha),f(x.icc)])}/>
   <Text tone="secondary" size="small">출처:M15실제54판독·results.json. 3프로필에서각3생성물을읽은조건부기술값입니다. 반복쌍은비독립이며상수의미정의는1로바꾸지않았습니다. 모델간점수차자체는실패조건이아닙니다.</Text>
  </Stack>
  <Stack gap={10}><H2>프로필별 생성물 차이 · 판독3회 평균</H2>
   <Table headers={["프로필","판독자","생성1·2·3 평균","전체평균","생성평균의표본SD","최소–최대"]} rows={DATA.profiles.map(x=>[x.case,x.label,x.means.map(f).join(" · "),f(x.mean),f(x.sd),`${f(x.min)}–${f(x.max)}`])}/>
   <Text tone="secondary" size="small">서로새로생성한글의평균차이며 같은글을다시읽는변동과구별합니다. 각생성평균에판독오차가남아있어순수생성분산은아닙니다. M13과의인과비교나프롬프트개선효과를측정한실험이아닙니다.</Text>
  </Stack>
  <Stack gap={12}><H2>실제 원문·6원평점·근거</H2>
   <Select value={selected} onChange={setSelected} options={DATA.items.map(x=>({value:x.id,label:x.id}))}/>
   <Table headers={["판독자","총점1·2·3","사실근거1·2·3","질문대응1·2·3","연속성1·2·3","당사자표현1·2·3"]} rows={Object.entries(item.judges).map(([p,rs])=>[names[p],points(rs.map(r=>r.score)),...[0,1,2,3].map(j=>points(rs.map(r=>r.facets[j].rating)))])}/>
   <Grid columns={2} gap={24}><Stack gap={8}><H3>동일한 합성 프로필</H3>{item.facts.map((v,i)=><div key={i}><Text size="small">{v}</Text></div>)}<Text tone="secondary" size="small">자기 이해: {item.self}</Text></Stack><Stack gap={8}><H3>이번 실제 생성 대화</H3>{item.dialogue.map(t=><div key={t.turn_id}><Text size="small" tone={t.speaker==="patient"?"primary":"secondary"}>{t.turn_id} {t.speaker==="patient"?"환자":"의사"}: {t.text}</Text></div>)}</Stack></Grid>
   <Grid columns={2} gap={24}>{Object.entries(item.judges).map(([p,rs])=><div key={p}><Stack gap={14}><H3>{names[p]} 실제 판독 이유</H3>{rs.map((r,j)=><div key={j}><Stack gap={6}><Text weight="medium">{j+1}회 · 총점{r.score??"결측"}</Text><Text size="small">{r.reason}</Text>{r.facets.map((x,k)=><div key={k}><Text size="small">{x.label} {x.rating??"NA/결측"} · 불확실{x.uncertain?"예":"아니오"}: {x.reason}</Text>{x.evidence.map((v,q)=><div key={q}><Text size="small" tone="secondary">{v.turn}: “{v.quote}” {v.valid?"원문일치":"인용불일치"}</Text></div>)}</div>)}</Stack></div>)}</Stack></div>)}</Grid>
  </Stack>
  {DATA.boundaries.length>0&&<Stack gap={10}><H2>판독 전 작성자 노트의 경계 후보</H2><Table headers={["생성물","위치","실제 표현","판단의 범위"]} rows={DATA.boundaries.map(x=>[x.id,x.turn,x.quote,x.reason])}/><Text tone="secondary" size="small">72턴을새판독전에읽고해시동결한비맹검작성자노트입니다. 임상gold/새수치평정이아닙니다. 반복출현만으로확정오류가되지는않습니다.</Text></Stack>}
  {DATA.events.length>0&&<Stack gap={10}><H2>판독 후 사건별 귀속·수용/보류</H2><Table headers={["생성물","위치","귀속","원문","근거"]} rows={DATA.events.map(x=>[x.id,x.turn,x.category,x.quote,x.reason])}/><Text tone="secondary" size="small">동일사건이모델·회차·여러축에반복돼도독립오류로더하지않습니다. 입력문제귀속을분리했으며점수가낮은대화를사후삭제하지않았습니다.</Text></Stack>}
  <Text>이자료는정렬된단일조건의새생성입니다. 모든입력차원이완결됐거나임상타당성이확보됐다는뜻은아닙니다. 관련자발적설명·정당한재확인·한국어생략을허용하며프롬프트를더수정하지않고정한범위에서이번주기를종료합니다.</Text>
  <Text tone="secondary" size="small">출처:question-audit.json·generation-freeze.json·author-prejudge-audit.json·freeze.json·54원응답·results.json·issue-attribution.json·verification.json,2026-11-19. 최종12/720·환자프롬프트·기존평가기준은불변입니다.</Text>
 </Stack>;
}
'''
    f=HERE/'patient-speech-aligned-input-m15.canvas.tsx';f.write_text(source.replace('__DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':'))));print('BuiltactualM15canvasbytes',f.stat().st_size)
if __name__=='__main__':main()
