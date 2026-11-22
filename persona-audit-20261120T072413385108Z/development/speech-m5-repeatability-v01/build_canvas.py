"""Build an offline interactive display from actual validated ratings only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    scores = json.loads((HERE / 'scores.json').read_text())
    items = json.loads((HERE / 'items-private.json').read_text())
    plan = json.loads((HERE / 'plan.json').read_text())
    reviews = {p: {} for p in ('codex', 'claude')}
    for r in plan['rounds']:
        key = json.loads((HERE / r['key']).read_text())
        for p in reviews:
            raw = json.loads((HERE / 'reviews' / p / f"round{r['repeat']:02d}" / 'validated.json').read_text())
            for row in raw['reviews']:
                reviews[p].setdefault(key[row['blind_id']], []).append(row)
    packet = json.loads((HERE / plan['rounds'][0]['packet']).read_text())
    def pick(value, fields):
        return {k: value[k] for k in fields.split()}
    visible_scores = pick(scores, 'rating_outputs original_version_means v04_minus_v02')
    visible_scores['items'] = [dict(pick(v, 'item_id kind condition equal_model_mean'),
        judges={p: pick(j, 'scores mean range exact_pair_agreement') for p, j in v['judges'].items()}) for v in scores['items']]
    visible_scores['repeatability_originals_only'] = {p: pick(v, 'all_three_equal_count exact_pair_agreements pair_count range_at_least_2_count score4_fraction') for p,v in scores['repeatability_originals_only'].items()}
    visible_scores['error_sensitivity'] = {p: pick(v, 'pairs_with_strictly_lower_error_mean mean_error_minus_source lower_count tie_count higher_count') for p,v in scores['error_sensitivity'].items()}
    visible_scores['error_pairs'] = [dict(pick(v, 'case_id combined_error_minus_source'),
        judges={p: pick(j, 'source_scores error_scores mean_error_minus_source') for p,j in v['judges'].items()}) for v in scores['error_pairs']]
    visible_items = []
    for v in items:
        item = pick(v, 'item_id case_id kind condition profile_ref generated_dialogue')
        if 'manipulation' in v: item['manipulation'] = pick(v['manipulation'], 'before after')
        visible_items.append(item)
    visible_reviews = {p: {ident: [dict(pick(v, 'score reason uncertainty'),
        issues=[pick(issue, 'id patient_turn_id quote issue suggestion') for issue in v['issues']]) for v in rows]
        for ident,rows in by_item.items()} for p,by_item in reviews.items()}
    profiles = {ident: dict(pick(v, 'communication authored_context'), patient_setting={
        'facts': [pick(f, 'id content') for f in v['patient_setting']['facts']],
        'self_understanding': v['patient_setting']['self_understanding']}) for ident,v in packet['profiles'].items()}
    data = {'scores': visible_scores, 'items': visible_items, 'reviews': visible_reviews, 'profiles': profiles}
    source = '''import { Stack, Row, H1, H2, H3, Text, Table, Select, useState, useHostTheme } from "cursor/canvas";
type Review={score:number;reason:string;uncertainty:string;issues:{id:string;patient_turn_id:string;quote:string;issue:string;suggestion:string}[]};
type Judge={scores:number[];mean:number;range:number;exact_pair_agreement:number};
type ItemScore={item_id:string;kind:string;condition:string;equal_model_mean:number;judges:Record<string,Judge>};
type Item={item_id:string;case_id:string;kind:string;condition:string;profile_ref:string;generated_dialogue:{turn_id:string;speaker:string;text:string}[];manipulation?:{before:string;after:string}};
type Repeat={all_three_equal_count:number;exact_pair_agreements:number;pair_count:number;range_at_least_2_count:number;score4_fraction:number};
type Sensitivity={pairs_with_strictly_lower_error_mean:number;mean_error_minus_source:number;lower_count:number;tie_count:number;higher_count:number};
type Scores={rating_outputs:number;items:ItemScore[];repeatability_originals_only:Record<string,Repeat>;error_sensitivity:Record<string,Sensitivity>;original_version_means:Record<string,number>;v04_minus_v02:number;error_pairs:{case_id:string;judges:Record<string,{source_scores:number[];error_scores:number[];mean_error_minus_source:number}>;combined_error_minus_source:number}[]};
type Profile={patient_setting:{facts:{id:string;content:string}[];self_understanding:string};communication:Record<string,string>;authored_context:{speaker:string;text:string}[]};
const DATA:{scores:Scores;items:Item[];reviews:Record<string,Record<string,Review[]>>;profiles:Record<string,Profile>}=__DATA__;
const fmt=(n:number)=>n.toFixed(2);
const sign=(n:number)=>(n>0?"+":"")+fmt(n);
const names:Record<string,string>={codex:"GPT-6.1 Sol High",claude:"Claude Opus 5.5"};
const title=(i:Item)=>`사례 ${i.case_id.slice(-1)} · ${i.condition==="error"?"인위적 오류 대조":i.condition==="v02"?"v0.2 원본":"v0.4 원본"}`;
export default function RepeatabilityDiagnostic(){
 const theme=useHostTheme();
 const [selected,setSelected]=useState(DATA.items[0].item_id);
 const [provider,setProvider]=useState("codex");
 const [round,setRound]=useState("0");
 const item=DATA.items.find(i=>i.item_id===selected)??DATA.items[0];
 const profile=DATA.profiles[item.profile_ref];
 const score=DATA.scores.items.find(i=>i.item_id===item.item_id)!;
 const review=DATA.reviews[provider][item.item_id][Number(round)];
 return <Stack gap={24} style={{padding:24,maxWidth:1200,color:theme.text.primary}}>
  <Stack gap={8}><H1>9대화 반복성·설정 오류 민감도</H1>
   <Text>2026-11-18 · 기존 합성 6대화 + 인위적 오류 대조 3개 · 두 모델 × 새 세션 3회 · {DATA.scores.rating_outputs}개 원평점</Text>
   <Text tone="secondary">환자 프롬프트와 원본 발화는 고정했습니다. 오류 대조는 v0.2 원본의 마지막 가족 지칭 한 곳만 같은 문자 수로 바꿨습니다. 임상 검증·최종 720회 판독은 미실시입니다.</Text>
  </Stack>
  <Stack gap={10}><H2>원본 6대화에서 점수가 얼마나 반복되는가</H2>
   <Table headers={["평가자","3회 모두 같은 대화","반복 쌍 정확 일치","범위 ≥2점 대화","최고점 비율"]}
    rows={Object.entries(DATA.scores.repeatability_originals_only).map(([p,r])=>[names[p],`${r.all_three_equal_count}/6`,`${r.exact_pair_agreements}/${r.pair_count} (${(100*r.exact_pair_agreements/r.pair_count).toFixed(1)}%)`,`${r.range_at_least_2_count}/6`,`${(100*r.score4_fraction).toFixed(1)}%`])}/>
   <Text tone="secondary" size="small">대화당 3회의 가능한 반복 쌍은 3개입니다. 최고점 몰림은 높은 일치율과 함께 볼 필요가 있습니다. 출처: M5 검증 원응답·scores.json, 2026-11-18.</Text>
  </Stack>
  <Stack gap={10}><H2>명백한 설정 모순에 점수가 내려가는가</H2>
   <Table headers={["평가자","오류 평균이 낮은 쌍","같은 라운드 하락 / 동점 / 상승","오류 − 원본 평균 (점)"]}
    rows={Object.entries(DATA.scores.error_sensitivity).map(([p,r])=>[names[p],`${r.pairs_with_strictly_lower_error_mean}/3`,`${r.lower_count} / ${r.tie_count} / ${r.higher_count}`,sign(r.mean_error_minus_source)])}/>
   <Table headers={["사례","GPT 원본 → 오류 (각 3회)","Claude 원본 → 오류 (각 3회)","두 모델 평균 차이 (점)"]}
    rows={DATA.scores.error_pairs.map(r=>[`사례 ${r.case_id.slice(-1)}`,`${r.judges.codex.source_scores.join("·")} → ${r.judges.codex.error_scores.join("·")}`,`${r.judges.claude.source_scores.join("·")} → ${r.judges.claude.error_scores.join("·")}`,sign(r.combined_error_minus_source)])}/>
   <Text tone="secondary" size="small">엄격한 점수 하락만 탐지로 셉니다. 라운드별 비교 9개는 오류 종류 3개의 반복이며 독립 사례 9개가 아닙니다. 오류 감점 규칙이나 정답은 평가자에게 제공하지 않았습니다.</Text>
  </Stack>
  <Stack gap={10}><H2>9대화의 모든 원평점</H2>
   <Table headers={["대화","GPT 1·2·3회","GPT 평균","Claude 1·2·3회","Claude 평균","두 모델 평균"]}
    rows={DATA.items.map(i=>{const s=DATA.scores.items.find(r=>r.item_id===i.item_id)!;return [title(i),s.judges.codex.scores.join(" · "),fmt(s.judges.codex.mean),s.judges.claude.scores.join(" · "),fmt(s.judges.claude.mean),fmt(s.equal_model_mean)];})}/>
   <Row gap={24} wrap><Text>원본 v0.2 평균 {fmt(DATA.scores.original_version_means.v02)}/4</Text><Text>원본 v0.4 평균 {fmt(DATA.scores.original_version_means.v04)}/4</Text><Text>v0.4 − v0.2: {sign(DATA.scores.v04_minus_v02)}점</Text></Row>
   <Text tone="secondary" size="small">각 모델의 3회 평균에 같은 가중치를 부여했습니다. 과거 M4 점수는 합치지 않았습니다. 같은 고정 발화의 새 판독이며 생성 반복 실험이 아닙니다.</Text>
  </Stack>
  <Stack gap={10}><H2>발화와 각 라운드의 실제 판정 근거</H2>
   <Select value={selected} onChange={setSelected} options={DATA.items.map(i=>({value:i.item_id,label:title(i)}))}/>
   {item.manipulation&&<Text>작성자 변형: “{item.manipulation.before}” → “{item.manipulation.after}”</Text>}
   <Table headers={["턴","화자","평가에 제공한 실제 원문"]} rows={item.generated_dialogue.map(t=>[t.turn_id,t.speaker==="patient"?"환자":"면담자",t.text])}/>
   <details><summary style={{cursor:"pointer",color:theme.text.link}}>공통 환자 설정과 작성 문맥</summary><Stack gap={8} style={{paddingTop:12}}>
    <Text>{profile.patient_setting.self_understanding}</Text>
    {profile.patient_setting.facts.map(f=><div key={f.id}><Text>{f.id}: {f.content}</Text></div>)}
    {Object.entries(profile.communication).map(([k,v])=><div key={k}><Text>{k}: {v}</Text></div>)}
    {profile.authored_context.map((t,i)=><div key={i}><Text>{t.speaker}: {t.text}</Text></div>)}
   </Stack></details>
   <Row gap={12} wrap><Select value={provider} onChange={setProvider} options={Object.entries(names).map(([value,label])=>({value,label}))}/>
    <Select value={round} onChange={setRound} options={[0,1,2].map(i=>({value:String(i),label:`독립 라운드 ${i+1}`}))}/></Row>
   <H3>{review.score}/4 · {names[provider]} · 라운드 {Number(round)+1}</H3><Text>{review.reason}</Text>
   {review.issues.map(issue=><div key={issue.id}><Stack gap={6} style={{borderLeft:`2px solid ${theme.stroke.secondary}`,paddingLeft:12}}>
    <Text weight="semibold">{issue.patient_turn_id}: “{issue.quote}”</Text><Text>{issue.issue}</Text><Text tone="secondary">검토자 제안: {issue.suggestion}</Text>
   </Stack></div>)}
   <Text tone="secondary">판독자 불확실성: {review.uncertainty}</Text>
  </Stack>
  <Stack gap={8}><H2>해석 범위</H2>
   <Text>9대화는 3개의 합성 개발 프로필에서 나왔습니다. 반복 점수는 새 환자 표본이 아니며, 오류 대조는 실제 생성 실패가 아닙니다. 높은 반복성만으로 임상적 정확성을 입증하지 않습니다.</Text>
   <Text>이 점검은 가족 관계의 명백한 모순만 다룹니다. 민감한 정보 공개의 적절한 속도나 미세한 대화 연속성에 대한 민감도는 별도 확인이 필요합니다.</Text>
   <Text tone="secondary" size="small">버전·변형 여부·이전 점수는 가렸지만 유사한 대화가 같은 묶음에 있어 관련성을 알아볼 수 있습니다. 실제로 Claude 라운드 2의 오류 대화 근거에서 다른 대화 ID(Q658)를 참조했습니다. 대화별 완전 독립 판독이나 완전한 눈가림으로 해석하지 않습니다. 라운드마다 제시 순서·ID를 바꿨으므로 관측 변동에는 순서 영향도 포함됩니다. GPT 생성·판독의 같은 계열 의존성 및 불변 모델 스냅샷·temperature 비노출 한계가 남습니다. 결과를 보고 프롬프트를 수정하지 않았습니다.</Text>
  </Stack>
 </Stack>;
}
'''
    source = source.replace('__DATA__', json.dumps(data, ensure_ascii=False, separators=(',', ':')))
    (HERE / 'patient-speech-repeatability.canvas.tsx').write_text(source)
    print('Canvas embedded 54 validated scores, 9 transcripts, 6 independent review outputs')


if __name__ == '__main__': main()
