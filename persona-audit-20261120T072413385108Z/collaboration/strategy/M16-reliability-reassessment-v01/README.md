# M16 · Claude 반복 일치 77.8% 재검토

**자연성 총점의 미세 차이로 개발안을 선택할 신뢰도가 확보됐다는 포괄적 판단을 정정했다.** 원문·설정의 명시적 대조와 경계 기록만 유지한다. 기존 환자 프롬프트와 평가 기준은 변경하지 않았다.

- 결론·실제 불일치·표본 구성·다음 범위: `reassessment.md`
- Astra/Claude 지적별 수용·보류·반박: `decision.md`
- 원수치·층화: `analysis.json`, 재현 코드 `analyze_existing.py`
- 실제 기존 판독·대화: `rationale-excerpts.json`
- 기존 문안 대응12기록: `criterion-mapping.json`, 후속 해석 정정 `mapping-interpretation-addendum.md`
- 실제 Astra 두 응답: `astra-round01.md`, `astra-round02.md`
- 실제 별도 Claude high 두 응답: `claude-round01/response.txt`, `claude-round02/response.txt`
- 전달한 반론·후속입력: `codex-response-round01.md`, `round02-request.md`
- 입력·범위 동결/검증: `scope-freeze.json`, `request-freeze.json`, `round02-freeze.json`, `verification.json`
- 분석 화면: `patient-speech-reliability-reassessment-m16.canvas.tsx`

M13 전체 Claude92.59%에는 안정적인 조작대조가 포함됐고 생성R만은7/9였다. M15는21/27, 세 원문에서3·4점 판정이 바뀌었다. 따라서 갑작스러운 악화도 불변도 증명하지 않는다. 같은 평균은 개별 판정의 재현성을 보장하지 않는다.

새 발화/평정0. 실제 전략 검토는 Claude high2CLI응답과 Astra2검토턴이며 수치 판독 횟수에 합산하지 않는다. 최종12내용 미열람·720미실행·임상 검증 없음. 화면은 TypeScript 검사0오류를 확인했으며 Codex 열기 요청은 queued여서 시각 렌더 확인을 주장하지 않는다.
