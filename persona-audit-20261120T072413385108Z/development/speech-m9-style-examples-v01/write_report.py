"""Write an offline index from actual M9 outputs; never calls a model."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def main():
    s=json.loads((HERE/'scores.json').read_text())
    lines=['# M9: v0.6의 예시 없음/있음 비교', '',
        '2026-11-18. 별도 방향성 멘토 검토 뒤 한 번 실행한 개발 실험이다. 실제 환자/전문의 검증·최종 720회 판독은 없다.', '',
        '## 실제 실행과 비교 범위', '',
        '- M8과 같은 합성 개발 3사례·8질문·시작 이력·GPT-6.1 Sol High, 조건별 각 3회 새 생성.',
        '- 18개 대화·144환자 발화·두 판독자 각 1회(2호출)·36원평점. 과거 출력을 대조군으로 재사용하지 않았다.',
        '- 두 조건 모두 v0.2 원문 전체 + 동일한 예시 해석 안내. 다른 가상 인물의 참고 목록만 []/3예시로 다르다. raw v0.2와 공통 안내 자체의 효과는 미측정이다.',
        '- GPT-6.1 Sol High와 Claude Opus 5.5 medium은 조건·예시·멘토 응답을 받지 않았다. 유사 대화의 묶음 제시로 완전한 독립성/눈가림은 보장하지 않는다.',
        '- 별도 Claude Opus 5.5 high 전략 검토는 두 실제 응답과 Codex 반론으로 이루어졌으며 이 평점에 합산하지 않았다.', '',
        '## 평점', '',
        f"- 예시 없음 평균: **{s['condition_means']['none']:.4f}/4**.",
        f"- 예시 있음 평균: **{s['condition_means']['examples']:.4f}/4**.",
        f"- 있음 − 없음: **{s['examples_minus_none']:+.4f}점**."]
    for p,name in [('codex','GPT-6.1 Sol High'),('claude','Claude Opus 5.5')]:
        d=s['judge_condition_means'][p]
        lines.append(f"- {name}: 없음 {d['none']:.4f}, 있음 {d['examples']:.4f}.")
    for c in s['cases']:
        lines.append(f"- {c['case_id']}: 없음 {c['none']['combined_scores']['mean']:.4f}, 있음 {c['examples']['combined_scores']['mean']:.4f}.")
    lines+=['','## 설명조·형식 관찰','']
    for p in ('codex','claude'):
        for v,label in [('none','없음'),('examples','있음')]:
            d=s['style_summary'][p][v]
            lines.append(f"- {p}/{label}: 요구되지 않은 보고서식·메타 설명은 중립 {d['neutral'].get('unrequested_reportlike_or_meta',0)}/45턴, 유도 {d['prompted'].get('unrequested_reportlike_or_meta',0)}/27턴. 요청된 설명 {d['all'].get('requested_explanation',0)}/72턴, 문체 불확실 {d['all'].get('uncertain',0)}/72턴.")
    for v,label in [('none','없음'),('examples','있음')]:
        d=s['surface_metrics'][v]['all']
        lines.append(f"- 예시 {label}: 환자 문자 합계 {d['patient_characters']}, 프로필3어절 중복 {d['profile_trigram']['matched']}/{d['profile_trigram']['denominator']}={d['profile_trigram']['ratio']:.4f}, 직전 질문3어절 중복 {d['question_trigram']['matched']}/{d['question_trigram']['denominator']}={d['question_trigram']['ratio']:.4f}, 복사 위험 {d['copy_risk_turns']}/72턴.")
    lines+=['','## 사전 선택과 해석','',f"- 사전 규칙 출력: `{s['selection']['decision']}`.",
        '- 규칙별 충족 여부와 개별 턴 지표는 scores.json, 근거·반론·보류는 interpretation.md를 읽는다. 더 낮은 글자 수/중복률 자체는 현실성 향상의 증거가 아니다.',
        '- 같은 세 사례의 버전 경쟁은 종료한다. 차이 미확인은 최적화·동등성·임상 한계를 증명하지 않는다.', '',
        '## 기록', '',
        '- `methods.md`, `plan.json`, `preflight-audit.json`: 사전 계획·동결 해시·누출/복사 정의.',
        '- `reference-examples.json`, `model-reference-examples.json`, `common-scaffold.txt`: 작성 근거·모델 제공 예시·공통 안내.',
        '- `runs/`: 144개 원입력·원응답·자기 이력·명령·시각·해시와 18개 전체 대화.',
        '- `author-example-observations.json`: 판독 전의 눈가림하지 않은 개발자 관찰. 임상/독립 평정이 아니다.',
        '- `review-packet.json`, `review-key-private.json`, `reviews/`: 동일한 가림 묶음·조건 대응·실제 원평정.',
        '- `scores.json`, `patient-speech-v06-examples.canvas.tsx`: Python 집계와 전체 원문 비교 화면.',
        '- `verification.json`: 144개 원출력/이력·36평점/인용·동일성·해시 재검증.',
        '- `../../collaboration/strategy/M9-direction-review-v01/decision.md`: 별도 방향성 왕복과 지적별 결정.', '',
        '## 코드와 사용', '',
        '`speech_module.core.V06_VERSION`을 명시하고 `build_packet`/`generate`에 `style_reference_examples=[]` 또는 동결한 JSON 목록을 전달한다. 입력의 환자 설정/의사소통/이력은 그대로다. CLI 준비 모드는 `python3 -m speech_module prepare`의 `--module-version schizophrenia-speech-m9-v0.6 --style-reference-examples <JSON 경로>`를 지원하며 추론 호출을 하지 않는다. v0.6의 기존 case-bound experimental-examples 옵션과 혼용할 수 없다.', '',
        '관련 모듈 검사 45개·분석 fixture 2개를 준비 단계에서 통과했다. 과거 v0.1~v0.5 파일은 보존했고 역사적 런타임 기본값 v0.4를 자동 승격하지 않았다. 개발 T의 선택은 런타임 기본값과 분리해 기록한다.', '',
        '## 한계와 문구 정정', '',
        '독립 프로필은 3개이며 여러 번 개발에 재사용했다. 한 대화당 각 판독자는 한 번만 평가했다. GPT 생성/판독은 같은 계열이고 불변 서버 스냅샷·temperature·seed는 제공되지 않는다. 예시는 일반적인 별도 합성 미니사례로, 조현병 발화의 임상 표준이 아니다.', '',
        '`scores.json.limits`의 재사용 문장 “Question set intentionally changed; do not pool M7 scores”는 M7→M8의 질문 추가를 가리킨다. **M9 질문은 M8과 동일**하며 검증 코드가 이를 직접 비교한다. 역사적 분석 코드를 동결한 뒤 결과를 바꾸지 않기 위해 이 문구를 원본에 보존하고 여기서 정정한다.']
    (HERE/'README.md').write_text('\n'.join(lines)+'\n')
    print('Wrote README from actual scores; qualitative interpretation remains separate')


if __name__=='__main__':main()
