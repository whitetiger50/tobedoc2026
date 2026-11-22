"""Run the three bounded development conversations through official ChatGPT CLI."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from collaboration.subscription_call import call_once, dump
from speech_module.core import generate, TEMPLATE, VERSION

HERE = Path(__file__).resolve().parent


def freeze():
    config_path = HERE / "generation-plan.json"
    if config_path.exists():
        return json.loads(config_path.read_text(encoding="utf-8"))
    cases = []
    for ident in ["DEV-M0-01", "DEV-M0-02", "DEV-M0-03"]:
        data = json.loads((ROOT / "development/speech-m0-v01/inputs" / f"{ident}.json").read_text())
        if ident.endswith("01"):
            questions = [data["current_question"], "밤에 들리는 목소리는 어떻게 이해하고 계세요?",
                         "지금 드시는 약 이름과 용량은요?", "아까 누구와 산다고 하셨죠?"]
        elif ident.endswith("02"):
            questions = [data["current_question"], "평소에는 누구와 지내세요?",
                         "말씀하신 밤의 경험에 대해 조금 더 이야기해 주실 수 있나요?", "처음에는 누가 와보라고 하셨죠?"]
        else:
            questions = [data["current_question"], "낮에는 보통 뭘 하세요?", "오늘 낮에는 뭘 하셨나요?",
                         "아버지와 따로 산다고 하셨죠?"]
        cases.append({"case_id": ident, "input": data, "questions": questions})
    config = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "kind": "development_not_final_evaluation",
              "module_version": VERSION, "template_sha256": hashlib.sha256(TEMPLATE.read_bytes()).hexdigest(),
              "generation_model": "gpt-6.1-sol", "reasoning_effort": "high", "turns_per_case": 4,
              "existing_history": "Codex_authored_context_not_observed_generation",
              "sampling": "one_output_per_question_no_best_of_selection", "cases": cases}
    dump(config_path, config)
    (HERE / "generation-template-v01.txt").write_bytes(TEMPLATE.read_bytes())
    return config


def run_case(case):
    ident = case["case_id"]
    data = deepcopy(case["input"])
    generated = []
    for index, question in enumerate(case["questions"], start=1):
        data["current_question"] = question
        directory = HERE / "runs-v01" / ident / f"turn{index:02d}"
        if (directory / "patient.txt").exists():
            saved = json.loads((directory / "packet.json").read_text())
            if saved["input"] != data:
                raise ValueError("Existing run input differs; refusing reuse")
            answer = (directory / "patient.txt").read_text()
        else:
            def backend(messages):
                return call_once("codex", messages[1]["content"], messages[0]["content"], directory / "transport")
            answer = generate(data, backend, directory)
        generated.extend([{"turn_id": f"D{index:02d}", "speaker": "clinician", "text": question},
                          {"turn_id": f"P{index:02d}", "speaker": "patient", "text": answer}])
        data["history"].extend([{"speaker": "clinician", "text": question}, {"speaker": "patient", "text": answer}])
        print(f"{ident} generated {index}/4", flush=True)
    transcript = {"case_id": ident, "partition": "development", "patient": case["input"]["patient"],
                  "communication": case["input"]["communication"], "authored_context": case["input"]["history"],
                  "generated_dialogue": generated, "module_version": VERSION, "clinical_validation": "not_performed"}
    dump(HERE / "runs-v01" / ident / "transcript.json", transcript)
    return ident


def main():
    plan = freeze()
    if hashlib.sha256(TEMPLATE.read_bytes()).hexdigest() != plan["template_sha256"]:
        raise ValueError("Template changed after freeze")
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(run_case, plan["cases"]))
    print(json.dumps({"completed_cases": results, "new_patient_turns": 12, "judgments": 0}), flush=True)


if __name__ == "__main__":
    main()
