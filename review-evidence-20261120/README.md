# MindCraft 영어 면담 연구 · 자료 안내

[포스터 인쇄본](학회포스터/MindCraft_조현병_영어_모의면담_학회포스터_A0.pdf) · [발표자 노트](학회포스터/speaker-notes.ko.md) · [팀 공유 편집용 요약](팀공유_영어_조현병_모의면담_최종연구요약.docx) · [인계 기록](handoff.md)

## 실제 면담과 가상 면담

DAIS-C 비교는 공개 저장소에 질문별 집계, 그림, 절차와 분석 코드를 제공한다. 사람별 입력·인용·판독·전사·부속 자료는 로컬에 보관한다. 원자료는 [UK Data Service](https://reshare.ukdataservice.ac.uk/855021/)에서 별도로 받는다. 실제 전사나 그 판독을 쓰는 스크립트의 전체 실행에는 관련 입력이 필요하다. 가상 면담의 입력과 답, 필요한 스코어를 별도 재현 자료로 제공한다.

- [T2 재현 자료](next-english-study/release/연구_재현자료.zip)를 빈 디렉터리에 풀고 `python3 -I -B reproduce.py`로 검산한다.
- [B·BC·T2 재현 자료](b-clarification-study/release/clarification-research.zip)를 별도의 빈 디렉터리에 풀고 `python3 -I -B verify.py`로 검산한다.
- [Gruber–Kring 본실험](gruber-kring-study2/main/RESULTS.ko.md)과 [카드 세부 삭제 대조](gruber-kring-study2/card-detail-pilot/RESULTS.ko.md)는 가상 응답과 기존 판독을 함께 보존한다.
- [이전 전체 연구 아카이브](../archive/README.md)와 [이관된 추가 연구 기록](../persona-audit-20261120T072413385108Z/README.md)은 초기 팀 연구, 페르소나 v0.1–v0.6 개발 및 측정 파일럿을 포함한다.

다운로드한 제3자 원문과 도구의 실행·계정 관련 로그는 로컬 보관본에 있다. 연구 결과나 집계는 원래 분석 시점의 판정을 보존한다.

## 포스터 다시 만들기

macOS에서 포스터 소스가 있는 `학회포스터` 디렉터리로 이동한 뒤 `swift render-poster.swift poster-layout.json output.pdf`를 실행하면 A0 세로 PDF를 생성한다. 발표자 노트는 별도의 Markdown 파일이다.
