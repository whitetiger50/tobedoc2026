"""Create a source-to-rule ledger with locally verifiable primary-source anchors."""
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

ROWS = [
 {"id":"E1", "source":"psyche-v1.pdf", "file":"text/psyche-v1.pdf.txt", "locator":"Methods / Utterance Simulation / Simulated Patient, PDF pp.9-10",
  "anchor":"The MFC itself and its explanation", "availability":"reported_generation_instructions_not_complete_system_prompt",
  "finding":"환자 구성체를 주고 그 내용을 발화로 옮기는 지시를 별도로 둔다. 임상 설정을 정리해 보고하는 출력과 환자다운 반응을 구분한다.",
  "apply":"설정을 환자의 지식·경험·자기 이해로 해석한 다음 말로 표현하는 순서를 명시한다.",
  "limit":"v1 주요 검증 질환은 7개이며 조현병은 포함되지 않는다. Figure 8/9는 의사 에이전트용이다. 원형 전체 system prompt를 확보했다고 주장하지 않는다."},
 {"id":"E2", "source":"psyche-v1.pdf", "file":"text/psyche-v1.pdf.txt", "locator":"Table 11, PDF p.38; Methods / Simulated Patient, p.10",
  "anchor":"thought process in Bipolar Disorder", "availability":"actual_behavior_instruction_and_examples_for_bipolar_disorder",
  "finding":"사고과정에 이름만 주는 대신 구체적 지시와 예시를 제공하는 접근을 공개한다. 이 표의 내용은 양극성장애의 사고비약이다.",
  "apply":"사례별로 작성한 표현 예시를 선택적으로 제공할 수 있게 한다. 예시의 사용 방식만 참고한다.",
  "limit":"사고비약의 표현·속도·장황함을 조현병의 표준 발화로 이식하지 않는다. 단어 수 상한과 의학용어 일괄 금지도 채택하지 않는다."},
 {"id":"E3", "source":"psi_formatter", "file":"../../evidence/snapshots/psi_formatter.txt", "locator":"formatPromptString, pinned commit de72a768; lines around 168-191",
  "anchor":"avoid directly referencing the diagram", "availability":"actual_original_author_prompt_assembly_code",
  "finding":"이력과 인지모형을 역할에 제공하되 모형 이름을 직접 해설하지 않도록 한다. 스타일, 전체 문맥, 설정 일관성을 함께 사용한다.",
  "apply":"임상 메타언어의 자동 낭독을 피하고 경험과 자기 이해로 표현한다. 환자가 실제로 배운 용어는 허용한다.",
  "limit":"CBT용이다. 몇 주간 치료받았다는 배경, 자동 신뢰 상승, 3/5/8문장 제한, 반드시 주제로 돌아오지 않는 tangent 규칙은 가져오지 않는다."},
 {"id":"E4", "source":"roleplay-doh.pdf", "file":"text/roleplay-doh.pdf.txt", "locator":"Appendix E.2 pp.10584; E.3 pp.10585-10586 (PDF pp.15-17)",
  "anchor":"Context Relevance Check", "availability":"actual_generation_template_and_adherence_pipeline_prompts_in_appendix",
  "finding":"시나리오·원칙·대화 이력을 사용하며, 원칙이 현재 문맥에 적용되는지 구분한 뒤 준수를 확인한다.",
  "apply":"민감 정보·경계심·조직성 규칙의 현재 질문에 대한 적용 조건을 먼저 고려하도록 한다.",
  "limit":"이번 구현은 단일 호출용 문맥 조건 지시다. 원 연구의 다단계 생성·비평·재작성 파이프라인을 재현하지 않는다. 전체 개별 전문가 원칙은 미확보이며 gated 자료를 우회하지 않았다."},
 {"id":"E5", "source":"psychiatric-voice-table1.html", "file":"text/psychiatric-voice-table1.html.txt", "locator":"Table 1 / Constraints; article Methods / Communication and interaction guidelines",
  "anchor":"Do not talk about your symptoms unless asked.", "availability":"actual_prompt_architecture_example_for_MDD_only",
  "finding":"환자 배경·증상·역할 수행·제약·교육 피드백을 나눈 예시를 공개한다. 본문은 면담 방식에 대한 반응성도 설명한다.",
  "apply":"주어진 사례의 입장에서 반응하고, 답변을 증상 목록처럼 제시하지 않는 원칙을 참고한다.",
  "limit":"조현병 전체 프롬프트와 별도 보충파일은 확인한 공개 페이지에서 확보하지 못했다. 증상 자발적 언급의 일괄 금지, 용어 일괄 금지, END 시 의사 평가 전환은 채택하지 않는다."},
 {"id":"E6", "source":"jmir-web-extract", "file":"text/jmir-web-extract.txt", "locator":"Textbox 1 schizophrenia vignette; Textbox 2 standardized simulation prompt; web-tool text capture, direct raw article bytes unavailable",
  "anchor":"Do not speak unless the student initiates the conversation.", "availability":"actual_standardized_role_prompt_with_schizophrenia_case_in_same_paper",
  "finding":"구체적인 조현병 사례와 공통 역할 프롬프트를 함께 제공한다. 학습자 질문에 환자 역할을 유지하며 반응하도록 한다.",
  "apply":"사례의 경험·정서·의사소통 맥락에 근거해 다음 환자 발화만 생성한다.",
  "limit":"reflective Viewpoint이며 정신측정 검증·교육 효과 비교는 미실시다. 사례의 제한적 발화·불신을 모든 환자에 일반화하지 않는다. 비언어 행동 선행 서술과 영어 출력 지시는 텍스트 한국어 목적에 맞춰 제외한다."},
 {"id":"E7", "source":"nimh-schizophrenia.html", "file":"text/nimh-schizophrenia.html.txt", "locator":"What are the signs and symptoms? / Psychotic symptoms; How can I help?",
  "anchor":"symptoms can differ from person to person", "availability":"official_clinical_description_not_generation_prompt_validation",
  "finding":"개인차를 명시하고 환각·망상·사고장애를 구분한다. 환자에게 그 경험이나 믿음이 실제처럼 느껴질 수 있다고 설명한다.",
  "apply":"주관적 경험·믿음과 발화 조직성을 분리하고 사례에 설정한 특성만 표현한다.",
  "limit":"세부 발화 규칙의 효과나 한국어 조현병 현실성을 검증한 출처가 아니다. 어떤 증상도 진단명만으로 자동 추가하지 않는다."},
 {"id":"E8", "source":"local_engineering", "file":"../../speech_module/patient_v02.txt", "locator":"v0.2 and M1 disposition",
  "anchor":"자료에 적혀 있지 않다는 것과 환자가 모르거나", "availability":"project_design_hypothesis_and_observed_development_issue",
  "finding":"사실 누락과 환자 무지/회피를 구분하고, 전체 이력·버전·필수 사실 ID를 보존한다.",
  "apply":"기존 데이터 경계와 작성자 의존성 주석을 유지한다.",
  "limit":"필수 사실 ID 점검·한국어 표현·예시 오염 방지 등은 연구팀의 공학적 선택이며 임상 문헌에서 검증된 처방으로 표시하지 않는다."},
]


def main():
    lock = json.loads((HERE / "source-lock-v02.json").read_text())
    urls = {r["id"]: r["url"] for r in lock["sources"]}
    for row in ROWS:
        path = (HERE / row["file"]).resolve()
        text = path.read_text()
        normalized = re.sub(r"\s+", " ", text)
        assert row["anchor"] in normalized, row["id"]
        row["url"] = urls.get(row["source"], "local_project_design")
        row["verified_local_file_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with (HERE / "evidence-ledger.json").open("x") as f:
        json.dump({"date":"2026-11-18", "evidence":ROWS, "clinical_validation_of_new_module":"not_performed"}, f, ensure_ascii=False, indent=2)
    print("8 source-to-rule entries anchored in actual local evidence; no clinical scores generated")


if __name__ == "__main__": main()
