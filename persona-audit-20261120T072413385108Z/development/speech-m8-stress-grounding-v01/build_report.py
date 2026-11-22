"""Write descriptive results from actual scores; qualitative interpretation stays separate."""
from pathlib import Path
import json

HERE=Path(__file__).resolve().parent


def main():
    s=json.loads((HERE/'scores.json').read_text())
    plan=json.loads((HERE/'plan.json').read_text())
    lines=['# M8: 추론 유도 질문에서 v0.2/v0.5 사실 근거·회피 비교','',
      '2026-11-18. 두 프롬프트·사례 사실·시작 이력·생성 모델을 고정하고, 기존 네 질문 뒤에 시간·인물·인과 유도 3문항과 정상 재확인 1문항을 추가했다. **18개 새 8턴 대화·144개 실제 생성 발화**를 만들고 두 모델이 같은 묶음을 각각 한 번 검토했다. 실제 생성 CLI 144호출·검토 CLI 2호출·현실성 원평점 36개다. 과거 대화의 첫 네 답변을 재사용하지 않았다.','',
      '점수·지적 수·회피 범주는 기술값이다. 원응답과 대조한 해석·지적별 판단은 **`interpretation.md`**에 별도로 기록한다. 프롬프트와 질문은 결과를 보고 재수정하지 않는다.','',
      '## 조건과 질문','',
      'M7과 같은 `gpt-6.1-sol` high로 질문당 한 출력만 생성했다. 후보·기준 모두 같은 질문을 받고 매 대화는 같은 작성 이력에서 새로 시작한 뒤 자신의 실제 답만 누적했다. 사례별 3개 worker를 쓰고 먼저 생성할 버전은 반복마다 교대했다. 공유 sampling seed가 아니며 서버 스냅샷·temperature·seed는 CLI에 노출되지 않는다. best-of·wrapper 재시도·사후 환자 발화 편집은 없다.','',
      '검토는 기존 공식 구독 CLI의 GPT-6.1 Sol High·Claude Opus 5.5(medium effort) 각 1회다. 같은 PATIENTSIM Realism 1–4 앵커를 사용하며 P01~P08의 사실 근거와 회피 범주를 추가로 요청했다. 버전·반복 번호·생성 모델·과거 점수·환자 프롬프트·비공개 문항 허용 메모는 제공하지 않았다. 유사 대화가 한 묶음에 있어 완전한 눈가림·대화별 독립 제시는 보장하지 않는다.','']
    for c in plan['cases']:
        lines.append('### '+c['case_id']);lines.append('')
        for index,(q,typ) in enumerate(zip(c['questions'],c['turn_types']),1):
            lines.append(f'- P{index:02d} ({typ}): {q}')
        lines.append('')
    lines+=['## 점수와 생성물별 변동','',
       f"전체 두 모델 평균: **v0.2 {s['condition_means']['v02']:.4f}/4, v0.5 {s['condition_means']['v05']:.4f}/4**, 차이 **{s['v05_minus_v02']:+.4f}점**. 각 대화는 두 원평점 평균이며 사례별 세 생성물과 세 사례에 같은 가중치를 줬다. 과거 4턴 실험과 직접 합치지 않는다.",'']
    for c in s['cases']:
        for v in ('v02','v05'):
            d=c[v]['combined_scores'];j=c[v]['judges']
            lines.append(f"- {c['case_id']} {v}: GPT {'·'.join(map(str,j['codex']['values']))}, Claude {'·'.join(map(str,j['claude']['values']))}; 두 모델 평균 {d['values']}; 그룹 평균 {d['mean']:.4f}, 표본 SD {d['sample_sd']:.4f}, 범위 {d['min']:.2f}–{d['max']:.2f}.")
    lines+=['','점수 SD에는 생성 차이와 단회 판독 변동이 함께 포함된다. 18대화가 독립 환자 18명은 아니며 같은 합성 개발 프로필 3개다. 평균은 순서형 점수의 기술값이다.','', '## 사실 근거 지적','']
    for p,versions in s['grounding_summary'].items():
        for v,g in versions.items():
            lines.append(f"- {p} {v}: 9대화 status {g['status_counts']}; 지적 {g['finding_count']}개, 종류 {g['finding_kind_counts']}.")
    lines+=['','P05 시간 / P06 인물 / P07 인과의 응답별 지적 수(불확실 포함):','']
    for p,versions in s['challenge_grounding_summary'].items():
        for v,types in versions.items():
            for typ,g in types.items():
                lines.append(f"- {p} {v} {typ}: {g['responses_with_findings']}/9응답, 지적 종류 {g['finding_kind_counts']}.")
    lines+=['','지적 수는 임상적 정답 오류 수가 아니다. 같은 응답의 여러 지적과 두 모델의 같은 지적은 독립 오류 기회가 아니다. 미확정 사건을 부정하는 것에도 근거가 필요하다. 작성자의 수용 범위와 실제 모델 지적은 구분해 해석한다.','', '## 회피와 정상 재확인','']
    for p,versions in s['avoidance_summary'].items():
        for v,a in versions.items():
            lines.append(f"- {p} {v}: 전체 환자 72턴 라벨 {a['all_turn_label_counts']}; 불필요 회피가 있는 대화 {a['dialogues_with_unnecessary_evasion']}/9; P08 정상 재확인 9응답 라벨 {a['recovery_P08_label_counts']}.")
        diff=versions['v05']['recovery_P08_label_counts'].get('unnecessary_evasion',0)-versions['v02']['recovery_P08_label_counts'].get('unnecessary_evasion',0)
        lines.append(f'- {p} P08 불필요 회피 수 차이(v0.5−v0.2): {diff:+d}응답.')
    lines+=['','`substantive_answer`는 근거 있는 답변, `appropriate_limit_or_correction`은 정당한 제한/정정, `contextual_withholding`은 맥락상 민감 정보 유보, `unnecessary_evasion`은 불필요 회피, `uncertain`은 판정 불확실이다. 정당한 제한·유보를 회피 증가로 합치지 않는다. 양쪽 0건이면 회피 불변 또는 오류 감소를 입증하지 않는다.','',
      '## 보존과 검증','',
      '- 사전 방법·문항: `methods.md`, `probes.json`, `plan.json`. 비공개 허용 메모는 작성자 설계 기준이며 임상가가 인증한 정답이 아니다.',
      '- 모든 실제 원문: `runs/{case}/rep{01,02,03}/{v02,v05}/transcript.json`; 각 `turn*/transport/`에 CLI 입력·명령·시각·stdout/stderr·원응답·모델 선택 메타데이터가 있다.',
      '- 판독 원문: `reviews/{codex,claude}/response.txt`, 검증 JSON `validated.json`; 평점·분포·지적·회피 집계 `scores.json`.',
      '- 작성자 원문 대조: `author-stress-observations.json`; 해석과 지적별 판단 `interpretation.md`. 임상의 주석이나 독립 인간 정답이 아니다.',
      '- 검증: `verification.json`; 당시 구현·프롬프트·문항·역할 `implementation-snapshot/`; 문항 구성/집계 fixture 2개 통과. Python으로 구조·인용·해시·모델 선택·실제 이력·144출력·36평점과 평균을 대조한다.',
      '- 결과 화면: `patient-speech-v02-v05-stress.canvas.tsx`.', '',
      '프롬프트/모듈 구현·사례 설정·최종 파일럿은 변경하지 않았다. 실제 환자 발화·전문의 평정·임상 타당성·새 모델 학습·유료 API·새 모델/패키지·자격 증명 출력·최종 720회 판독은 없다. 불변 서버 버전·temperature 비노출, 같은 GPT 계열의 생성/판독, 단회 판독, 유사 대화의 묶음 영향이 남는다. p값·CI·일반적 우월성/동등성/최적화를 선언하지 않는다.']
    with (HERE/'README.md').open('x') as f:f.write('\n'.join(lines)+'\n')
    print('Wrote descriptive results from actual JSON; qualitative interpretation remains separately traceable')


if __name__=='__main__':main()
