"""Build a proposed pilot manifest. Does not generate, score, or call any model."""
from pathlib import Path
import csv
import hashlib
import json
import random

ROOT = Path(__file__).resolve().parent
CASES = [
    ("C01", "내용 증상·조직 보존", 22, "남성", "대학생", "기숙사 생활. 지난 학기부터 혼자 있을 때 자신을 비난하는 목소리를 경험하며 수업 집중이 어렵다. 수면이 줄어 상담에 왔다.", "문장과 사건 순서는 보존된다. 경험을 확신하면서도 스트레스 때문일 가능성을 조금 인정한다. 처음에는 조심스럽고 구체적 질문에는 답한다."),
    ("C02", "내용 증상·조직 보존", 34, "여성", "사무직", "혼자 살며 직장 동료들이 자신을 관찰한다고 믿는다. 업무 실수가 늘어 가족 권유로 왔다. 최근 새로운 치료를 시작하지 않았다.", "의심의 내용은 있으나 질문과 답의 연결은 보존된다. 신뢰를 확인하려고 질문 의도를 되묻기도 한다. 모든 질문을 거부하거나 공격적으로 말하도록 설정하지 않는다."),
    ("C03", "내용 증상·조직 보존", 45, "남성", "소매점 운영", "가족과 살고 가게를 운영한다. 최근 혼자 있을 때 들리는 목소리 때문에 손님 응대와 잠에 어려움이 생겼다. 도움을 받으러 자발적으로 왔다.", "말은 다소 길고 불안을 표현하지만 이야기의 목적과 순서는 보존된다. 협조적이며 자신의 해석에 확신과 의문이 섞여 있다."),
    ("C04", "사고형식 변화", 26, "여성", "대학원 휴학", "가족과 지낸다. 휴학 후 일상을 정리하기 어렵고 대화가 길어졌다는 말을 들었다. 수면이 불규칙하다.", "경미한 우회와 주제 이탈이 있지만 구체적인 질문을 받으면 돌아올 수 있다. 모든 문장을 무작위로 만들거나 의미 없는 단어를 나열하지 않는다. 회상 능력 저하나 섬망은 설정하지 않는다."),
    ("C05", "사고형식 변화", 31, "남성", "물류 업무 휴직", "동생과 산다. 최근 일을 쉬며 대화 중 생각이 다른 방향으로 이어져 동생이 내용을 따라가기 어렵다고 한다.", "일부 답변에서 주제 연결이 약해지지만 생활 사건 자체는 이해할 수 있다. 반복 언어·기억상실은 설정하지 않는다. 모든 질문에 같은 방식의 탈선을 넣도록 요구하지 않는다."),
    ("C06", "사고형식 변화", 39, "여성", "프리랜서", "배우자와 산다. 최근 작업 진행과 집안일을 설명할 때 이야기 흐름을 유지하기 어렵다고 느낀다. 면담에는 참여하려 한다.", "중간 정도의 주제 연결 어려움과 평범한 답변이 섞인다. 설명을 다시 요청하면 일부는 명료해진다. 기계적 반복이나 모든 문장의 비문법성은 설정하지 않는다."),
    ("C07", "자발적 발화 감소", 28, "남성", "구직 중", "부모와 산다. 최근 활동과 친구 연락이 줄었다. 부모 권유로 왔으며 일상에 대한 기억은 유지된다.", "먼저 긴 설명을 덧붙이는 일이 적고 답변은 짧다. 구체적인 질문에는 관련된 사실을 말한다. 짧다는 이유로 적대적이거나 이해가 부족하다고 설정하지 않는다. 음성의 단조로움은 텍스트로 확정하지 않는다."),
    ("C08", "자발적 발화 감소", 51, "여성", "세탁 업무 시간제", "가족과 살고 시간제로 일한다. 치료를 받고 있으며 최근 여가 활동과 대화량이 줄었다. 수면과 식사는 대체로 일정하다.", "필요한 내용에 짧고 직접적으로 답한다. 질문을 받으면 추가 설명이 가능하다. 망상·탈선을 새로 추가하지 않는다. 공손하고 낮은 자발성이 함께 있을 수 있다."),
    ("C09", "자발적 발화 감소", 36, "남성", "음식점 휴직", "가족과 살며 일을 쉬고 있다. 하루 활동이 적고 본인이 먼저 말할 일이 줄었다. 정기 진료에 참여 중이다.", "짧고 구체적인 답변이 중심이다. 질문을 이해하고 사실관계는 유지한다. 생성 지연을 사고 지연의 증거로 취급하지 않는다. 반복 답변·무관한 답변은 목표 설정이 아니다."),
    ("C10", "안정·병식 보존", 24, "여성", "복학한 대학생", "치료 후 복학했고 가족과 산다. 과거의 목소리 경험을 증상으로 이해한다. 현재는 학업과 규칙적인 수면을 유지하며 정기 진료 중이다.", "자연스럽고 조직적인 대화와 협조적 태도. 자신의 경험을 일부 의학용어로 설명할 수 있다. 현실성을 높인다는 이유로 탈선·저항을 추가하지 않는다."),
    ("C11", "안정·병식 보존", 47, "남성", "의료 지식이 있는 약국 업무 경험자", "배우자와 산다. 장기간 치료 중이며 최근 생활이 안정적이다. 과거 증상과 치료 경과를 비교적 구체적으로 기억한다.", "의학용어 사용이 배경상 가능하고 질문에 논리적으로 답한다. 용어 사용 자체를 인공적인 역할 해설과 혼동하지 않는다. 기본 진료 협조와 보존된 병식을 설정한다."),
    ("C12", "안정·병식 보존", 58, "여성", "은퇴한 도서관 직원", "가족과 살며 치료를 지속한다. 가끔 과거와 비슷한 목소리 경험을 느끼지만 대처 방법을 알고 일상을 유지한다.", "경험과 해석을 구분하며 차분하게 설명한다. 치료 경험에 관한 지식이 있지만 면담 중 모든 문제가 갑자기 해결되는 상황은 설정하지 않는다."),
]
QUESTIONS = [
    "오늘 이 면담에서 이야기하고 싶은 점부터 말씀해 주세요.",
    "요즘 보통 하루를 어떻게 보내시는지, 일어나서부터 순서대로 말씀해 주세요.",
    "최근에 불편하거나 신경 쓰였던 일을 한 가지 구체적으로 말씀해 주실 수 있나요? 특별한 변화가 없다면 없다고 말씀하셔도 됩니다.",
    "그 일이나 경험이 있었을 때 어떤 상황이었고, 주변에는 누가 있었나요? 해당하는 경험이 없다면 평소 상황을 말씀해 주세요.",
    "그런 경험이나 생활의 변화는 언제부터 있었고, 최근에는 어떻게 달라졌나요?",
    "본인은 그 경험이나 변화가 왜 생긴다고 생각하시나요?",
    "그 일에 대해 다른 설명도 가능하다고 느끼시나요? 어떻게 생각하시는지 말씀해 주세요.",
    "최근 잠과 식사는 어떠신가요?",
    "일이나 공부, 집안일에는 어떤 영향이 있나요?",
    "가족이나 주변 사람들은 요즘 상황에 대해 뭐라고 이야기하나요?",
    "이전에 도움이나 치료를 받아보신 적이 있다면 어떤 경험이었는지 말씀해 주세요.",
    "지금 가장 필요한 도움이나 앞으로 바라는 점은 무엇인가요?",
]
REPORT = {"C03", "C04", "C07", "C12"}
CONTEXT = {"C01", "C02", "C10", "C11"}


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    cases = []
    dialogues = []
    for idx, entry in enumerate(CASES, 1):
        case_id, group, age, gender, occupation, facts, communication = entry
        cases.append(dict(case_id=case_id, group=group, age=age, gender=gender,
                          occupation=occupation, facts=facts, communication=communication,
                          provenance="Created by Codex (LLM) for this pilot; synthetic case draft, not real patient data or clinician-validated cases",
                          status="requires complete factual case sheet and freeze before generation"))
        for condition in ["B", "T"]:
            dialogues.append(dict(dialogue_id=f"{case_id}-{condition}", case_id=case_id,
                                  set="natural", condition=condition, source_dialogue_id="",
                                  transformation="none", status="planned_not_generated"))
        corruption_source = "B" if idx % 2 else "T"
        length_source = "T" if idx % 2 else "B"
        corruption = "reportification" if case_id in REPORT else "context_permutation" if case_id in CONTEXT else "mechanical_repetition"
        direction = "shorten_70_to_80_percent" if idx % 4 in [1, 2] else "expand_130_to_150_percent"
        dialogues.append(dict(dialogue_id=f"{case_id}-E", case_id=case_id, set="corruption", condition="derived",
                              source_dialogue_id=f"{case_id}-{corruption_source}", transformation=corruption,
                              status="planned_not_generated"))
        dialogues.append(dict(dialogue_id=f"{case_id}-L", case_id=case_id, set="length", condition="derived",
                              source_dialogue_id=f"{case_id}-{length_source}", transformation=direction,
                              status="planned_not_generated"))
    rng = random.Random(20261118)
    shuffled = list(dialogues)
    rng.shuffle(shuffled)
    blind_lookup = {d["dialogue_id"]: f"D{n:03d}" for n, d in enumerate(shuffled, 1)}
    key = [dict(blind_id=blind_lookup[d["dialogue_id"]], **d) for d in dialogues]
    slots = []
    for judge in ["A", "B", "C"]:
        for repeat in range(1, 6):
            batch = list(dialogues)
            for _ in range(10000):
                rng.shuffle(batch)
                if all(a["case_id"] != b["case_id"] for a, b in zip(batch, batch[1:])):
                    break
            else:
                raise RuntimeError("Could not construct a case-separated order")
            for order, d in enumerate(batch, 1):
                slots.append(dict(slot_id=f"{judge}-R{repeat}-{blind_lookup[d['dialogue_id']]}",
                                  judge_slot=judge, repeat=repeat, order=order,
                                  blind_id=blind_lookup[d["dialogue_id"]], status="planned_no_rating"))
    spec = {
        "design_version": "0.2", "date": "2026-11-18", "status": "panel_selected_not_preregistered_not_executed",
        "counts": {"cases": 12, "questions_per_dialogue": 12, "natural_dialogues": 24,
                   "corruption_dialogues": 12, "length_dialogues": 12, "total_dialogues": 48,
                   "judge_families": 3, "repeats": 5, "planned_judgments": 720},
        "primary_reliability_set": "natural_only",
        "case_creator": "Codex (LLM); twelve synthetic profile drafts created specifically for this pilot",
        "case_origin": "Not sampled from real patient records or a clinically validated case bank",
        "judge_slots": {
            "A": {"provider": "OpenAI", "model_name": "GPT-6.1 Sol", "api_model_id": "gpt-6.1-sol",
                  "proposed_reasoning_effort": "high", "release_and_runtime_settings_lock": "pending execution verification"},
            "B": {"provider": "Anthropic", "model_name": "Claude Opus 5.5", "api_model_id": "claude-opus-5-5",
                  "proposed_reasoning_effort": "medium", "release_and_runtime_settings_lock": "pending execution verification"},
            "C": {"provider": "Google", "model_name": "Gemini 4 Argon", "api_model_id": "gemini-4-argon",
                  "proposed_reasoning_effort": "platform default, record actual supported setting before lock",
                  "release_and_runtime_settings_lock": "pending execution verification"},
        },
        "judge_selection_reason": "capable general-purpose models from three families; practical panel choice, not task-specific validated superiority",
        "judge_tools": "no web search, retrieval, external patient information, or evaluator discussion during rating",
        "aggregation": "median_of_three_model_medians_of_five_integer_scores",
        "missing": "require all five valid ratings per model and all three model medians for aggregate",
        "gates_are": "proposed operational choices, NOT PATIENTSIM or schizophrenia clinical standards",
        "gates": {
            "valid_rating_fraction_min": .99, "complete_natural_fraction_min": .95,
            "within_each_model": {"ordinal_alpha_min": .80, "alpha_ci_lower_min": .67,
                                  "pair_exact_agreement_min": .80, "range_ge_2_fraction_max": .10},
            "across_model_medians": {"ordinal_alpha_min": .67, "alpha_ci_lower_min": .50,
                                     "range_ge_2_fraction_max": .10,
                                     "clear_opposite_prompt_effects": "disqualify sole aggregate claim"},
            "corruption": {"panel_strict_decreases_min": 10, "total": 12,
                           "per_type_min": 3, "per_type_total": 4,
                           "each_judge_strict_decreases_min": 9},
            "length": {"panel_unchanged_min": 10, "total": 12, "abs_difference_ge_2_max": 0,
                       "neutrality": "must be audited before rating; otherwise indeterminate"},
            "expert_later_natural_only": {"ordinal_alpha_min": .67, "alpha_ci_lower_min": .50,
                                          "exact_agreement_min": .60, "abs_difference_ge_2_fraction_max": .10},
        },
        "uncertainty": {"method": "case_cluster_percentile_bootstrap", "replicates": 4000,
                        "seed": 20261118, "ci": .95, "invalid_bootstrap_fraction_max": .05},
        "indeterminate_if": ["expected_disagreement_zero", "dominant_natural_score_fraction_ge_0.80",
                             "CI insufficient despite adequate point estimate", "length-control neutrality uncertain"],
        "expert_phase": {"natural": 24, "corruption": 6, "length": 6, "total": 36,
                         "clinical_raters": 1, "status": "not secured_not_performed",
                         "selected_corruption_cases": ["C01", "C03", "C05", "C07", "C08", "C11"],
                         "selected_length_cases": ["C01", "C02", "C03", "C04", "C07", "C10"]},
        "claims_after_LLM_pass": "Primary endpoint permitted only as LLM-rated realism under an adapted research rubric",
        "not_established": ["clinical validity by LLM consensus", "real patient speech equivalence",
                            "clinical severity", "augmentation utility"],
        "new_model_outputs": False,
    }
    for name, data in [("pilot-design.json", spec), ("cases-and-questions.json", {"cases": cases, "questions": QUESTIONS})]:
        (ROOT/name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    write_csv(ROOT/"analysis_key_DO_NOT_SHOW_JUDGES.csv", key)
    write_csv(ROOT/"planned_judgment_slots.csv", slots)
    assert len(dialogues) == 48 and len(slots) == 720
    assert len({s["slot_id"] for s in slots}) == 720
    assert len({blind_lookup[d["dialogue_id"]] for d in dialogues}) == 48
    assert sum(d["set"] == "natural" for d in dialogues) == 24
    assert sum(d["set"] == "corruption" for d in dialogues) == 12
    assert sum(d["set"] == "length" for d in dialogues) == 12
    assert sum(d["transformation"] == "shorten_70_to_80_percent" for d in dialogues) == 6
    assert sum(d["transformation"] == "expand_130_to_150_percent" for d in dialogues) == 6
    for tag in ["reportification", "context_permutation", "mechanical_repetition"]:
        assert sum(d["transformation"] == tag for d in dialogues) == 4
    for cases_selected in [spec["expert_phase"]["selected_corruption_cases"], spec["expert_phase"]["selected_length_cases"]]:
        assert len(set(cases_selected)) == 6
    control_map = {d["case_id"]: d for d in dialogues if d["set"] == "corruption"}
    assert all(sum(control_map[c]["transformation"] == t for c in spec["expert_phase"]["selected_corruption_cases"]) == 2 for t in ["reportification", "context_permutation", "mechanical_repetition"])
    length_map = {d["case_id"]: d for d in dialogues if d["set"] == "length"}
    assert sum(length_map[c]["transformation"].startswith("shorten") for c in spec["expert_phase"]["selected_length_cases"]) == 3
    verification = {"status": "design arithmetic and assignment checks passed; NOT experimental findings",
                    "planned_dialogues": len(dialogues), "planned_slots": len(slots),
                    "new_model_outputs": False,
                    "sha256": {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
                               ["파일럿_계획.md", "pilot-design.json", "cases-and-questions.json",
                                "analysis_key_DO_NOT_SHOW_JUDGES.csv", "planned_judgment_slots.csv"]}}
    (ROOT/"design-verification.json").write_text(json.dumps(verification, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"planned_dialogues": 48, "planned_judgments": 720, "case_clusters": 12,
                      "status": "design verified; no model generation or judging performed"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
