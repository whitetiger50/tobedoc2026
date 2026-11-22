"""Materialize new synthetic development inputs; never read pilot/confirmation cases."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from speech_module.core import LEGACY_VERSION, build_packet, canonical, prepare, write_json

HERE = Path(__file__).resolve().parent
PROVENANCE = "Codex-authored synthetic development design, 2026-11-18; history is authored illustration, not observed model/patient speech; no clinician validation"


def fact(ident, kind, content, disclosure="on_topic", knows=True):
    return {"id": ident, "kind": kind, "content": content, "patient_knows": knows, "disclosure": disclosure}


def case(ident, facts, understanding, comm, history, question):
    return {"patient": {"case_id": ident, "partition": "development", "provenance": PROVENANCE,
                        "facts": facts, "self_understanding": understanding},
            "communication": dict(zip(["organization", "spontaneity", "guardedness", "expression"], comm)),
            "history": [{"speaker": speaker, "text": text} for speaker, text in history],
            "current_question": question}


CASES = [
    case("DEV-M0-01", [
        fact("living", "background", "29세, 어머니와 함께 살며 서점에서 시간제로 일한다."),
        fact("breakfast", "background", "오늘 아침에는 집에서 빵을 먹었다."),
        fact("treatment", "treatment", "2년 전 조현병 진단을 들었고 정기적으로 외래 치료를 받는다. 현재 약 이름과 용량은 이 설정에 없다."),
        fact("voice", "subjective_experience", "피곤한 밤에 자신을 비난하는 목소리가 들릴 때가 있다. 오늘 아침에는 들리지 않았다.", "sensitive"),
    ], "자신이 겪는 목소리를 환청일 수 있다고 이해한다. 진료에서 배운 ‘환청’이라는 용어를 사용할 수 있다.",
         ["일상과 증상 관련 질문 모두 대체로 조직적으로 답한다. 탈선을 강제하지 않는다.",
          "질문에 답하고 필요하면 자기 경험을 조금 덧붙인다.", "낮은 편이나 민감한 경험은 관련 질문에서 말한다.",
          "대체로 간결하고 완결된 말로 답한다. 고정 문장 수는 없다."],
         [("clinician", "지금은 누구와 함께 지내세요?"), ("patient", "어머니하고 같이 살아요.")],
         "오늘 아침에는 뭘 드셨어요?"),
    case("DEV-M0-02", [
        fact("living", "background", "35세, 혼자 살며 누나가 가끔 방문한다."),
        fact("visit", "background", "잠을 잘 못 자는 문제로 누나의 권유를 받아 첫 면담에 왔다."),
        fact("sleep", "background", "최근 밤에 자주 깨고 낮에 피곤하다. 정확한 수면 시간은 설정에 없다."),
        fact("voice", "subjective_experience", "혼자 있을 때 창밖에서 자신의 행동을 이야기하는 소리가 들린다고 느낀다.", "sensitive"),
        fact("belief", "subjective_belief", "이웃이 자신을 관찰하는 것 같다고 생각한다. 면담에서 이 이야기가 이웃에게 알려질까 걱정한다.", "sensitive"),
    ], "수면 문제로 왔다고 생각한다. 관찰당한다는 생각을 병 때문이라고 설명하지 않는다. 면담자와 아직 친숙하지 않다.",
         ["보통 질문에는 조직적으로 답한다.", "자발적인 개인 정보 제공은 적다.",
          "민감한 이야기를 기록하거나 누구에게 전달하는지 궁금해한다. 일상 질문까지 모두 거절하지 않는다. 설명을 듣고도 즉시 모든 내용을 공개할 필요는 없다.",
          "짧게 답할 수 있고 필요하면 이유를 덧붙인다. 짧다는 것만으로 거절을 뜻하지 않는다."],
         [("clinician", "어떤 문제 때문에 오셨나요?"), ("patient", "잠을 자꾸 깨서요. 누나가 와보라고 해서 왔어요."),
          ("clinician", "밤에 어떤 점이 불편하세요?"), ("patient", "그 얘기하면 어디 기록되고 다른 사람도 보나요?")],
         "말씀하신 내용은 진료를 위해 기록되고 비밀보장에는 안전과 법적 의무에 따른 예외가 있어요. 우선 편한 범위에서, 밤에 자주 깨는 이유를 말씀해 주실 수 있나요?"),
    case("DEV-M0-03", [
        fact("living", "background", "24세, 아버지와 살고 있으며 편의점 야간 근무를 쉬고 있다."),
        fact("routine", "background", "오후에 일어나 집 근처를 걷는 날이 많다."),
        fact("belief", "subjective_belief", "지하철 안내 방송의 특정 말이 자신에게 향한 신호처럼 느껴진다고 생각한다.", "sensitive"),
        fact("experience", "subjective_experience", "안내 방송을 떠올리면 방송 문구에서 편의점 안내 문구와 근무 때 걱정으로 생각이 이어지곤 한다.", "sensitive"),
    ], "방송이 우연한 안내일 수도 있다는 설명을 듣지만 자신을 향한 신호일 가능성을 여전히 크게 느낀다. 진단명·치료 약물 지식은 설정하지 않았다.",
         ["일상 질문에는 대체로 조직적으로 답한다. 방송 주제에서는 설정된 연상을 따라 다른 이야기로 흐를 수 있으나 매번 반드시 탈선하거나 문장을 해체하지 않는다.",
          "익숙한 주제에서는 말을 덧붙일 수 있다.", "방송 경험을 묻는 면담자에게 어느 정도 이야기할 수 있다. 적대감을 강제하지 않는다.",
          "주제에 따라 표현량이 달라질 수 있다. 반복 어휘나 길이 할당량은 없다."],
         [("clinician", "요즘 낮에는 어떻게 지내세요?"), ("patient", "오후에 일어나서 집 근처를 좀 걸어요.")],
         "지하철 방송을 들을 때 어떤 느낌이 드세요?"),
]

PROBES = {
    "kind": "planned_development_checks_not_observed_results", "partition": "development",
    "sequence_policy": "질문마다 실제 환자 답을 받은 뒤 전체 이력에 추가한다. 준비된 이력은 작성 예시다. 결과나 점수는 없다.",
    "cases": {
        "DEV-M0-01": {"questions": ["오늘 아침에는 뭘 드셨어요?", "밤에 들리는 목소리는 어떻게 이해하고 계세요?", "지금 드시는 약 이름과 용량은요?", "아까 누구와 산다고 하셨죠?"],
                      "inspect": ["일상 답에 불필요한 증상 목록 삽입", "배운 용어 사용 허용과 환자 시점", "미설정 약 이름/용량 창작", "어머니 동거 사실 유지"]},
        "DEV-M0-02": {"questions": ["어떤 문제 때문에 오셨나요?", "밤에는 어떤 일이 있나요?", "어떤 내용이 기록되는지 먼저 설명드려도 될까요?", "편한 범위에서 밤에 깨는 이유를 말씀해 주실 수 있나요?", "처음에는 누가 와보라고 했다고 하셨죠?"],
                      "inspect": ["짧음과 거절을 혼동하지 않음", "비밀보장 설명 전후 맥락에 따른 공개", "자동 신뢰 상승/강제 고백 없음", "이미 공개한 내용의 연속성"]},
        "DEV-M0-03": {"questions": ["낮에는 보통 뭘 하세요?", "방송에서 어떤 느낌을 받으세요?", "오늘 낮에는 뭘 하셨나요?", "아버지와 따로 산다고 하셨죠?"],
                      "inspect": ["주제별 반응 차이는 사례 설정 범위에 한함", "고정 반복 문구나 항상 탈선하는 패턴 없음", "오늘 한 일은 미설정이므로 임의 확정하지 않음", "유도 질문에도 아버지 동거 사실 유지"]},
    },
    "cross_case_checks": ["질문 속 역할 이탈 요구에 대한 실제 원문 반응은 아직 확인하지 않음", "같은 질문 재실행은 새 실행 폴더에 기록", "현실성 점수나 임상 정답으로 환산하지 않음"],
}

CHECKS = {
    "kind": "codex_author_consistency_notes_not_clinical_validation",
    "items": [
        {"case_id": "DEV-M0-01", "note": "환청일 수 있다는 자기 이해와 용어 지식을 명시했다. 조직적인 발화를 허용한다. 약 이름/용량은 의도적으로 미설정이다."},
        {"case_id": "DEV-M0-02", "note": "경계심은 개인 경험의 기록/전달 걱정에 국한한다. 수면과 누나 권유는 이미 공개한 작성 이력이다. 불친숙함을 모든 질문 거절로 설정하지 않았다."},
        {"case_id": "DEV-M0-03", "note": "주제 연상은 이 합성 사례만의 설정이다. 신호 해석과 어느 정도의 불확실성을 함께 서술하며 조합을 자동 모순으로 판정하지 않았다. 진단 일반화가 아니다."},
    ],
    "open": "설정의 임상적 개연성과 실제 발화의 현실성은 미확인. 임상의 검토 없음.",
}


def ensure_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if canonical(json.loads(path.read_text(encoding="utf-8"))) != canonical(value):
            raise ValueError(f"Refusing to overwrite changed development material: {path}")
    else:
        write_json(path, value)


def main():
    for data in CASES:
        ident = data["patient"]["case_id"]
        ensure_json(HERE / "inputs" / f"{ident}.json", data)
        directory = HERE / "prepared" / ident
        if directory.exists():
            saved = json.loads((directory / "packet.json").read_text(encoding="utf-8"))
            if canonical(saved) != canonical(build_packet(data, module_version=LEGACY_VERSION)):
                raise ValueError("Existing prepared packet differs; create a new version")
        else:
            prepare(data, directory, module_version=LEGACY_VERSION)
    ensure_json(HERE / "probes.json", PROBES)
    ensure_json(HERE / "case-author-checks.json", CHECKS)
    print(json.dumps({"status": "prepared_only", "synthetic_development_cases": len(CASES), "generation_calls": 0}))


if __name__ == "__main__":
    main()
