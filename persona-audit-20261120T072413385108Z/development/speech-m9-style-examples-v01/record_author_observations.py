"""Save Codex's unblinded observations before any M9 judge call; no score."""
from datetime import datetime, timezone
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    assert not (HERE/'reviews').exists(), 'Author observations must precede judge calls'
    files = sorted((HERE/'runs').glob('*/rep*/*/transcript.json'))
    assert len(files) == 18
    rows = []
    for f in files:
        t = json.loads(f.read_text())
        turns = {a['turn_id']: a['text'] for a in t['generated_dialogue'] if a['speaker']=='patient'}
        case = t['case_id'][-1]
        notes = {
            '1': '일상 사실 재확인과 약명/용량의 지식 한계가 유지된다. P05~P07은 전제·인과를 구분하라고 요구한 질문이므로 답변의 정정 표현 자체를 설명조 오류로 세지 않는다.',
            '2': '비밀보장 우려가 명시 질문 뒤에도 답을 듣지 못한 문맥을 고려한다. 소리 경험의 공개/유보와 같은 우려의 반복은 별도로 읽으며, 짧은 답변 자체를 개선으로 판정하지 않는다.',
            '3': 'P05는 오늘 산책과 평소 기상 시점을, P07은 동시 서술과 원인을 구별한다. 유도 질문의 설명 요구와 중립 질문의 직접 답변을 나눠 읽는다.',
        }[case]
        uncertain = []
        if t['item_id']=='DEV-M0-02-rep03-none':
            uncertain.append({'patient_turn_id':'P04','quote':turns['P04'],
                'observation':'누나가 ... 잠을 잘 못 자니까의 한국어 생략으로 수면 주체가 모호하다. 누나의 증상을 새로 지어냈다고 확정하지 않으며 P06의 자기 정정을 함께 보존한다.'})
        if t['item_id']=='DEV-M0-03-rep01-examples':
            uncertain.append({'patient_turn_id':'P02','quote':turns['P02'],
                'observation':'쉬고 있어서요가 일상 설명의 배경인지, 미설정 인과 단정인지 경계가 모호하다. P07에서 인과 의도를 부정하므로 확정 오류로 세지 않는다.'})
        if t['item_id']=='DEV-M0-02-rep01-examples':
            notes += ' 이 생성의 P03은 수면 설명을 반복하고 소리 경험은 말하지 않는다. 경계심에 따른 유보일 수 있지만 문맥 적합성은 판독자의 독립 판단을 남긴다.'
        rows.append({'item_id':t['item_id'],'author_notes':notes,
            'evidence':[{'patient_turn_id':p,'quote':turns[p]} for p in ('P03','P07')],
            'author_uncertain_findings':uncertain})
    out = {'timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'role':'unblinded_developer_Codex_observation_not_independent_clinical_rating',
        'timing':'after reading actual 18 transcripts; before M9 judge calls or scores',
        'not_sent_to_judges':True,'numeric_scores':None,'rows':rows}
    (HERE/'author-example-observations.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print('Saved 18 pre-judge unblinded author observations with actual quotations')


if __name__=='__main__':main()
