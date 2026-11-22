# Codex가 개발하고 Claude가 비평하는 최소 협업 환경

현재 개발 검토는 **GPT-6.1 Sol High + Claude Opus 5.5 각 1회**, 수치 평정은 **두 값의 산술평균**이다. 720회 반복 판독은 최종 결과 단계로 미룬다. 아래 기존 운영 설명과 다른 부분은 [최신 개발 검토 규칙](development-review-policy.md)을 우선한다.

이 폴더는 한 로컬 프로젝트에서 작은 검토 요청과 응답을 교환하는 환경이다. 연결 시험은 `connection-test.json`, 현재 실제 개발 진행은 `development-status.json`으로 구분한다. M0 Claude 설계 비평 1회에 이어 M1에서 실제 합성 면담 3개·12발화를 생성하고 GPT·Claude가 각 1회 검토했다. v0.1의 평균 3.17/4와 지적을 반영해 v0.2를 구현했고, 수정 후 평점 없는 3발화를 추가 확인했다. 최신 원문·반영 근거·한계는 `../development/speech-m1-v01/README.md`를 읽는다. 최종 연구 판독·전문의 평정·B/T 성능 비교는 아직 수행하지 않았다.

## 바로 사용할 파일

- `START_HERE.md`: 새 Codex 개발 채팅에 읽힐 최신 목표·평가 결정·시작 지시.
- `NEW_CHAT_PROMPT.txt`: 연결 완료 상태를 반영한 새 채팅 첫 메시지.
- `connection-status.json` / `connection-test.json`: Pro 구독 인증·Opus 연결 확인 기록. 계정 이메일과 토큰은 포함하지 않는다.
- `review_request.md`: 첫 발화기 구조에 대한 구체적인 M0 검토 요청. 아직 구현 결과가 아니다.
- `reviewer_prompt.txt`: Claude의 비평 역할과 응답 범위.
- `claude_packet_M0.txt`: 위 두 파일을 합친 최초 요청. Claude 앱에 그대로 전달하는 수동 경로용이다.
- `review_once.py`: 공식 Claude Code CLI에 작은 요청 한 건을 전달하고 응답을 보존하는 선택적 보조 스크립트. 기본 실행은 준비 상태 확인만 한다.

## 권장 순서

1. 같은 로컬 프로젝트에서 발화기 개발용 새 Codex 채팅을 연다. `START_HERE.md`의 첫 메시지를 사용한다.
2. Codex가 프롬프트 모듈을 작게 구현하고, 별도 개발 사례에서 나온 실제 입출력을 검토 요청에 넣는다.
3. Claude에 한 번의 검토를 요청한다. 프롬프트 변경마다 전체 연구와 저장소를 다시 읽히지 않는다.
4. Codex가 피드백에 대한 수용·보류·반박과 근거를 기록하고 수정한다. 단계별 최초 1회, 중대한 수정 후 추가 1회까지를 기본으로 한다.
5. 같은 문제에서 두 번 검토해도 근거가 부족하면 새 확인 실험으로 넘어간다. 서로 동의할 때까지 자동 대화하지 않는다.

## Claude 앱만 사용하는 경로

Claude Pro 앱에서 새 검토 대화를 열고 `claude_packet_M0.txt`를 전달한다. 받은 답변을 이 프로젝트에 저장하거나 Codex에 전달하면 된다. 두 앱이 서로의 채팅을 자동으로 읽는 방식은 아니다. 전체 채팅 내역이나 미사용 최종 성능 평가 자료를 보내지 않는다.

## Claude Code를 사용하는 경로

이 Mac에는 `/Users/ohs/.local/bin/claude`에 공식 CLI가 설치돼 있다. 현재 셸 PATH에 이 디렉터리가 없더라도 보조 스크립트는 네이티브 경로를 직접 찾는다. 전역 PATH는 변경하지 않았다.

이 Mac에서는 사용자가 공식 브라우저 로그인 흐름을 완료했고 Pro 구독 인증이 확인됐다. 재설치·재로그인부터 반복하지 않는다. 다른 Mac에서 새로 설정한다면 [공식 설치 안내](https://code.claude.com/docs/en/setup)에 따라 설치하고 본인이 Pro 계정으로 로그인한다. 계정 토큰을 다른 에이전트나 채팅에 전달하지 않는다.

프로젝트 폴더에서 실행:

```bash
~/.local/bin/claude auth status --text
python3 collaboration/review_once.py
```

마지막 명령은 검토 요청의 크기·해시·실행 파일 존재 여부만 출력한다. Claude 추론을 호출하지 않는다. 구독 로그인이 확인된 뒤 한 번의 검토를 요청하려면 다음 명령을 사용한다.

```bash
python3 collaboration/review_once.py --run
```

실제 응답이 오면 `reviews/M0-design-round1/`에 입력·원응답·메타데이터·검토문이 기록된다. 해당 경로가 이미 있으면 덮어쓰지 않는다. 중대한 수정 후 두 번째 검토는 새로운 실제 요청을 작성한 다음 `--round 2`로 요청한다. 새 단계는 고유한 `--milestone`을 사용한다.

이 스크립트는 공식 CLI의 `-p`를 사용하며, 구현 파일 읽기·쓰기·명령 실행·MCP 도구는 제공하지 않는다. 입력에 필요한 정보가 없으면 Claude는 결론 대신 질문해야 한다. 항상 전체 저장소를 훑는 에이전트 팀보다 적은 문맥으로 검토할 수 있게 한 방식이다.

## 사용량과 인증

Claude Pro에서 공식 Claude Code에 접근할 수 있지만 실제 할당량은 계정 상태에 따른다. 앱과 Code 사용량도 함께 고려한다. Pro를 보유했다는 이유로 API 호출이 무료인 것은 아니다.

`review_once.py --run`은 API 키·외부 제공자 관련 환경변수가 있거나, CLI의 구독 인증을 확인할 수 없으면 중지한다. 변수 이름만 확인하며 값이나 계정 이메일은 출력하지 않는다. 지원하지 않는 플래그·실패 응답·시간 초과는 자동 재시도하거나 다른 결제 방식으로 전환하지 않는다. 사용자의 전역 환경변수나 Claude 설정은 바꾸지 않는다.

실제 Pro 계정 로그인과 필수 CLI 옵션을 확인했다. 짧은 연결 확인과 실제 연구 검토를 구분하며, 연결 확인 결과는 `connection-test.json`에 보존한다. `--safe-mode`를 지원하지 않는 구버전에서는 멈추도록 했다. Pro 사용량의 하드 상한을 이 스크립트가 보장하지는 않는다. Codex 도구 샌드박스에서만 Keychain 인증이 보이지 않으면, 설정을 바꾸지 말고 해당 CLI 명령을 정상 로컬 권한에서 다시 확인한다.

## 개발 검토와 연구 판독의 구분

Claude의 개발 비평은 대화당 3모델×5회 판독을 반복하는 작업이 아니다. 개발 검토는 작은 변경의 오류와 개선 방향을 찾는 데 쓰고, 고정된 3모델 패널의 독립 반복 평정은 평가자 파일럿·후속 성능 비교에 쓴다.

자료의 원문과 모델·프롬프트 버전·입력 해시는 기록한다. 기존 저장소에는 미추적 연구 파일도 있으므로 Git diff만으로 모든 변경이 보인다고 가정하지 않는다. 검토 요청에는 실제 변경 원문 또는 명시적으로 선택한 파일을 포함한다.

## 공식 문서

- [Claude Pro와 Code](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-max-or-ultra-plan)
- [공식 단발 실행](https://code.claude.com/docs/en/headless)
- [CLI 옵션](https://code.claude.com/docs/en/cli-reference)
- [구독·API 인증 구분](https://code.claude.com/docs/en/authentication)
- [API 키 우선순위](https://support.claude.com/en/articles/12304248-manage-api-key-environment-variables-in-claude-code)
