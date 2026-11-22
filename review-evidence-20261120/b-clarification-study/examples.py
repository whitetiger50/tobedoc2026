"""Pair preselected illustrative turns of the validated interviews with their independent readings."""
import json
from pathlib import Path
BASE=Path(__file__).resolve().parent
def load(n):return json.loads((BASE/n).read_text())
def main():
    keys={(v['case'],v['rep'],v['arm']):v['id'] for v in load('private/key.json')}
    goal=load('opportunities.json')
    readers={j:{(r['case'],r['rep'],r['turn'],r['arm']):r for r in load('behavior/'+j+'-turns.json')} for j in ['gpt','opus']}
    out=['# 같은 질문에 대한 세 발화기의 실제 영어 답',
         '가상 면담의 최초 생성과 두 판독자의 기존 판정이다. 직접 답으로 두 뜻을 모두 해결한 장면, 후보가 확인한 장면과 불필요하게 되물은 장면을 읽기 위한 예시다. 선별한 예시는 효과 추정에 쓰지 않았다.']
    for c,i,t in [('C01',1,3),('C03',1,4),('C03',1,8),('C03',1,9),('C07',1,1),('C08',1,10)]:
        src=goal[c][str(t)]
        x=[load('blind/'+keys[c,i,a]+'.json')['dialogue'][t-1] for a in ['B','BC','T2']]
        out +=[f'## {c} · 첫 생성 · {t}턴','**Interviewer**  '+x[0]['question'],
              '카드에 따른 뜻과 답은 '+' / '.join(m['meaning']+' — '+m['expected_answer'] for m in src['interpretations'])+'이다.']
        for a,rec in zip(['B','BC','T2'],x):
            z=[readers[j][c,i,t,a] for j in ('gpt','opus')]
            out +=[f'**{a}**  '+rec['answer']+'\n\n'+
                   'GPT의 앞 문맥·행동 판정은 '+z[0]['need']+' / '+z[0]['action']+'이고 Opus는 '+z[1]['need']+' / '+z[1]['action']+'이다.']
    out+=['material은 가능한 뜻에 따라 답이 달라짐, resolved는 문맥으로 의미를 알 수 있음, same_answer는 가능한 두 뜻에서 실질적 답이 같음을 뜻한다. targeted_yield는 뜻을 구체적으로 확인하고 기다린 답, no_ask는 되묻지 않은 답이다.']
    (BASE/'EXAMPLES.ko.md').write_text('\n\n'.join(out)+'\n')
if __name__=='__main__':main()
