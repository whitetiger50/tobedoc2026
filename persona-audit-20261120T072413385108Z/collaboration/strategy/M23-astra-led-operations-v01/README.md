# M23 Astra 주도 운영과 맥미니 이전

현재 리더 판단은 `astra-lead.md`, Opus 반론 처리·근거표 최종 검증은 `decision.md`, 실제 근거 완성물은 `patient-language-evidence-brief.md`다. 원래 질환언어 재현 목표는 아직 미해결이며 M21 본실험은 보류다. 기존 전체 1~2개월 작업을 전수 감사한 것이 아니다.

팀 운영의 기준은 프로젝트 `AGENTS.md`, `collaboration/OPERATING_MODEL.md`, `AUTONOMY_STATE.json`, `NEXT_ACTION.md`다. 실제 Astra 주도 판단, Sol의 이전 구현 및 근거 요약, 별도 공식 Opus 응답이 이번에 실행됐다. 과거 발화 점수와 새 방법론 비평, 임상 검증을 구분한다. 일상 선택과 의견차는 Astra가 결정하며 현재 사용자 결정 요청은0건이다. 상시 실행 스케줄러는 없다.

이전 안내는 `collaboration/migration/README.md`, 새 기기 시작 문구는 루트 `START_ON_MAC_MINI.txt`다. ZIP은 원본을 보존하는 working-tree 스냅샷이며 untracked 파일과 역할 지시를 포함하고 Git 커밋 이력·기기 인증은 제외한다. source-vcs-provenance.json에 원래 HEAD와 dirty상태를 남겼다. 기존 내부 alias는 internal-link-map.json에서 canonical 원출력 위치를 찾을 수 있다.

정적 TOML 구문검사는 통과했다. 현재 CLI는 features 명령의 --strict-config를 지원하지 않아 이 명령으로 프로젝트 agent discovery를 검증했다고 주장하지 않는다. 새 기기에서 실제 역할·인증 확인이 남는다. 공식 에이전트 설정 문서: https://learn.chatgpt.com/docs/agent-configuration/subagents ; 저장소 지시 문서: https://learn.chatgpt.com/docs/agent-configuration/agents-md

fixture12개와 이 기기의 무모델·무인증 doctor를 검증했다. 최종 ZIP과 실제 복원 검증은 파일쓰기 종료 후 진행하고, 완료/해시는 ZIP 옆 export-receipt.json에 기록한다. 소스에 발행 후 자신의 해시를 다시 쓰지 않는다.
