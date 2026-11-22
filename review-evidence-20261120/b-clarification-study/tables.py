"""Korean result tables calculated from the read-only first results."""
import json
from pathlib import Path
from collections import Counter
from statistics import median
import re

HERE=Path(__file__).resolve().parent
def read(x):return json.loads((HERE/x).read_bytes())
def table(head,rows):
    return '\n'.join(['| '+' | '.join(head)+' |','|'+'---|'*len(head)]+['| '+' | '.join(map(str,r))+' |' for r in rows])
def main():
    primary=read('primary-results.json'); dec=read('decision.json'); chal=read('challenge/results.json')
    ids=sorted(primary['scores']['gpt']);arms=['B','BC','T2'];cl=['material','context_resolved','same_answer','clear']
    names=dict(B='B 원형',BC='B + 한 문장',T2='T2');labels=('답이 달라짐','문맥으로 해소','두 답이 같음','기타 명료')
    gpt,opus=[read('behavior/'+j+'-turns.json') for j in ('gpt','opus')]
    data={'gpt':gpt,'opus':opus}
    slides=['# B에 되묻기 규칙을 추가한 실험의 상세 결과',
      '각 사례·조건에서 12턴 면담을 독립적으로 두 번 생성하고 각 판독자가 면담별로 두 번 평가했다. B와 BC의 기반 시스템·역할별 이력·환자 설정은 같고, BC에는 영어 규칙 한 문장을 추가했다. 모든 사람과 문답은 가상이다.']
    for j in ('gpt','opus'):
        s=primary['scores'][j];bx=dec['readers'][j];bp=bx['behavior'];ra=bx['reality'];name='GPT' if j=='gpt' else 'Opus'
        slides+=['## '+name+'의 전체 면담 현실성',
         '각 칸은 첫 생성의 1·2회 점수 / 둘째 생성의 1·2회 점수다. 점수는 1–4점이다.',
         table(['사례',*map(names.get,arms)],[[c,*[' / '.join('·'.join(str(n) if n is not None else '결측' for n in s[c][a][k]) for k in ('1','2')) for a in arms]] for c in ids]),
         table(['앞 조건 대 뒤 조건','첫 생성 승·동률·패·불안정·결측','둘째 생성 승·동률·패·불안정·결측','네 번 모두 동점 이상','두 생성 모두 안정 패','사례 평균 점수 차이'],[
           [k.replace('_vs_',' 대 '),*['·'.join(str(v['by_replicate'][str(n)].get(e,0)) for e in ('win','tie','loss','unstable','missing')) for n in (1,2)],
            f"{len(v['preserved_cases'])}/8",f"{len(v['double_loss_cases'])}/8",f"{v['case_mean_difference']:.3f}" if v['case_mean_difference'] is not None else '결측'] for k,v in ra['contrasts'].items()]),
         '## '+name+'의 실제 응답 행동',
         '표적 확인은 의미를 구체적으로 되묻고 그 차례에 특정 해석으로 대답하지 않은 경우다. 확인 후 기다림은 표적 확인과 일반적인 명료화 요청을 합친다.',
         table(['설계한 질문','지표',*map(names.get,arms)],[[label,'표적 확인' if i==0 else '확인 후 기다림',*[
              str(bp['by_arm'][a][cls]['targeted' if i==0 else 'wait_any'])+'/'+str(bp['by_arm'][a][cls]['eligible']) for a in arms]] for i,(cls,label) in enumerate(zip(cl,labels))]),
         table(['설계한 질문','BC에만 관찰','B에만 관찰','BC−B 관찰차','유보·결측 허용 범위'],[
              [label,*[bp['paired_by_planned'][cls][k] for k in ('new_certain','lost_certain','observed_difference','bounds')]] for cls,label in zip(cl,labels)]),
         table(['사례','표적 확인 차이 가능한 범위 (BC−B)'],[[c,bp['paired_by_planned']['material']['by_case_bounds'][c]] for c in ids]),
         table(['설계상 답이 다른 질문에서의 행동',*map(names.get,arms)],[
              [label,*[bp['by_arm'][a]['material']['action'].get(cat,0) for a in arms]] for cat,label in
              [('targeted_yield','구체적으로 확인 후 기다림'),('generic_yield','막연히 확인 후 기다림'),('incidental_yield','다른 사항을 묻고 기다림'),('asks_and_answers','되묻고도 같은 차례에 답함'),('no_ask','직접 답하거나 되묻지 않음'),('uncertain','불확실'),('missing','결측')]]),
         table(['실제 직전 문맥에서 두 조건에 공통인 기회','공통 기회 / 평가 가능 64쌍','사례 수','BC−B 관찰차','불확실 반영 범위'],[
             [label,v['shared_count'],v['shared_decisive_cases'],v['difference'],v['bounds']] for label,v in [('답이 달라짐',bp['shared_actual_material']),('다시 물을 필요 없음',bp['shared_actual_nonmaterial'])]]),
         table(['기능',*map(names.get,arms)],[
             ['뜻을 특정한 후속 질문에 실질적으로 답함',*[str(bp['by_arm'][a]['followup_substantive'])+'/32' for a in arms]],
             ['중대한 임상 사실 추가·모순 판독',*[str(bp['by_arm'][a]['harm_turns'])+'/192' for a in arms]],
             ['기타 명료 질문에서 초점 이탈',*[str(bp['by_arm'][a]['clear_offtarget'])+'/128' for a in arms]]]),
         '### 설계와 앞 문맥 판독의 일치',
         '각 칸은 뜻이 달라짐 · 문맥 해소 · 같은 답 · 판단 불충분 · 결측 순서다. 각 조건의 고유한 앞선 답변 0–11개를 제공했다. 나머지 8개 명료 질문은 이 필요성 판독을 별도로 실시하지 않았다.',
         table(['질문 유형',*map(names.get,arms)],[[lab,*['·'.join(str(bp['by_arm'][a][cls]['need'].get(v,0)) for v in ('material','resolved','same_answer','insufficient','missing')) for a in arms]]for cls,lab in zip(cl[:3],labels[:3])])]
    rows=[]; key=lambda x:(x['case'],x['rep'],x['turn'],x['arm']);os={key(x):x for x in opus}
    for a in arms:
        for field,unk in [('action',('missing','uncertain')),('need',('missing','insufficient')),('harm',('missing','uncertain'))]:
            xs=[(x[field],os[key(x)][field]) for x in gpt if x['arm']==a and (field!='need' or x['planned']!='clear')]
            valid=[(v,w) for v,w in xs if v not in unk and w not in unk]
            label={'action':'응답 행동','need':'직전 문맥 필요성','harm':'임상적 사실 추가·모순'}[field]
            rows.append([names[a],label,sum(v==w for v,w in valid),len(valid),len(xs)-len(valid)])
    slides+=['## 두 판독자의 일치',table(['조건','판정','같은 범주','양쪽 확정','유보·결측'],rows),
     table(['오류 대조쌍','GPT 원본 / 오류','Opus 원본 / 오류'],[
         [lbl,*[str(chal[j]['pairs'][str(i)]['original'])+' / '+str(chal[j]['pairs'][str(i)]['error']) for j in ('gpt','opus')]] for i,lbl in enumerate(('문답 순서 이동','무관한 문구 반복','면담자 역할 이탈','차트식 보고'))])]
    keyrows=read('private/key.json'); lens={a:[] for a in arms}
    for cell in keyrows:
        x=read('blind/'+cell['id']+'.json')
        lens[cell['arm']].append(sum(len(re.findall(r"[A-Za-z]+(?:['’][A-Za-z]+)*",v['answer'])) for v in x['dialogue']))
    slides+=['## 12턴에 걸친 답변 길이',
        table(['조건','16개 면담의 총 단어 수 중앙값','범위'],[[names[a],median(lens[a]),f"{min(lens[a])}–{max(lens[a])}"] for a in arms]),
        '[사전 설계](DESIGN.ko.md) · [판정 기록](decision.json) · [실제 후보 프롬프트](BC.txt)']
    (HERE/'TABLES.ko.md').write_text('\n\n'.join(slides)+'\n')
if __name__=='__main__':main()
