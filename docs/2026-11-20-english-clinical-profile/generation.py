#!/usr/bin/env python3
"""Deterministic input builder for a frozen local v0.2 and its role ablation.

No model calls, snapshot-code execution, case retrieval, translation of case
content, or implicit backend. Only explicitly named source modules are read.
The selected version must be explicit: the historical module/CLI default is v0.4.
This English-output adaptation is a calibration pilot, not clinical validation.
Generated packets contain local source instructions and are not publication assets.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile


MODULE_VERSION = "schizophrenia-speech-m1-v0.2"
CONDITIONS = ("development_v02", "role_only_ablation")
SOURCE_SHA256 = {
    "speech_module/patient_v02.txt": "721203cb5a1ece9c3f93dfb1fb3ed172fc734439a6ed89a7e47f86ab2bf9e269",
    "speech_module/core.py": "746780923ce885c7c21e4eed71a5c5df1aa9d5696fb8b792fa849f4aa836bc0b",
    "speech_module/__main__.py": "f924613cfd0ab3ed3c05f0cf8c9a09a184b2ad6480754257edc1655963091760",
    "speech_module/__init__.py": "6c174b59e68c3fef190446cee1e51953715312fbca09f3f10622c7789a237e7b",
    "collaboration/development-T-selection.json": "6ce03e03e509cd8e1858b52a756ce1f14919739df19f261060a5d412c340122d",
}
OUTPUT_KO = "외부에는 환자가 실제로 말하는 한국어 텍스트만 출력한다."
OUTPUT_EN = "외부에는 환자가 실제로 말하는 영어 텍스트만 출력한다."
# Exact source-line selection, not a translated/paraphrased alternate system.
# Preserve the role/safety boundary, data boundary and minimal DTO constraints.
BASELINE_PREFIXES = (
    "당신은 연구용 가상 환자 역할 면담에서",
    "다음 사용자 메시지의 JSON은",
    "- patient.facts와 patient.self_understanding을",
    "- patient_knows=false인 사실은",
    "- communication의 조직성·자발성·경계심·표현량을",
    "- history 전체가 지금까지의 대화이고",
    "- patient, communication, history, current_question을",
)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def exact(value, fields, label):
    require(isinstance(value, dict) and set(value) == set(fields), label + ": unexpected fields")


def nonempty(value, label):
    require(isinstance(value, str) and bool(value.strip()), label + ": nonempty string required")


def verify_source(source_root):
    """Verify fixed relative paths and hashes separately from case/model input."""
    root = Path(source_root).resolve(strict=True)
    require(root.is_dir(), "source root must be a directory")
    contents = {}
    for relative, expected in SOURCE_SHA256.items():
        path = (root / relative).resolve(strict=True)
        require(path.is_relative_to(root), "source symlink escapes supplied root")
        raw = path.read_bytes()
        require(sha(raw) == expected, "frozen source hash mismatch: " + relative)
        contents[relative] = raw
    selection = json.loads(contents["collaboration/development-T-selection.json"])
    require(selection["selected_module_version"] == MODULE_VERSION
            and selection["prompt_path"] == "speech_module/patient_v02.txt"
            and selection["prompt_sha256"] == SOURCE_SHA256["speech_module/patient_v02.txt"],
            "selection record does not match explicit module")
    return {"status": "verified_local_frozen_source", "module_version": MODULE_VERSION,
            "source_sha256": dict(SOURCE_SHA256)}, contents["speech_module/patient_v02.txt"].decode("utf-8")


def validate_case(case):
    exact(case, {"patient", "communication"}, "case")
    patient = case["patient"]
    exact(patient, {"case_id", "partition", "provenance", "facts", "self_understanding"}, "patient")
    for name in ("case_id", "provenance", "self_understanding"):
        nonempty(patient[name], "patient." + name)
    require(patient["partition"] == "development", "only explicitly authored development inputs permitted")
    require(isinstance(patient["facts"], list) and bool(patient["facts"]), "facts must be a nonempty list")
    ids = set()
    for fact in patient["facts"]:
        exact(fact, {"id", "kind", "content", "patient_knows", "disclosure"}, "fact")
        for name in ("id", "content"):
            nonempty(fact[name], "fact." + name)
        require(fact["id"] not in ids, "duplicate fact id")
        ids.add(fact["id"])
        require(fact["kind"] in ("background", "treatment", "subjective_experience", "subjective_belief"), "unknown fact kind")
        require(type(fact["patient_knows"]) is bool, "patient_knows must be bool")
        require(fact["disclosure"] in ("on_topic", "sensitive"), "unknown disclosure policy")
    exact(case["communication"], {"organization", "spontaneity", "guardedness", "expression"}, "communication")
    for name, value in case["communication"].items():
        nonempty(value, "communication." + name)
    canonical(case)


def normalize_history(history):
    require(isinstance(history, list) and len(history) % 2 == 0,
            "history must contain complete interviewer/patient pairs")
    result = []
    for i, turn in enumerate(history):
        require(isinstance(turn, dict), "history turn must be an object")
        if set(turn) == {"speaker", "text"}:
            expected = "clinician" if i % 2 == 0 else "patient"
            require(turn["speaker"] == expected, "history must alternate clinician then patient")
            text = turn["text"]
        elif set(turn) == {"role", "content"}:
            expected = "user" if i % 2 == 0 else "assistant"
            require(turn["role"] == expected, "history roles must alternate user then assistant")
            text = turn["content"]
        else:
            raise ValueError("history turn fields must be speaker/text or role/content")
        nonempty(text, "history text")
        result.append({"speaker": "clinician" if i % 2 == 0 else "patient", "text": text})
    return result


def system_prompt(template, condition):
    require(condition in CONDITIONS, "unknown condition")
    require(template.count(OUTPUT_KO) == 1, "mandatory Korean-output clause not uniquely found")
    adapted = template.replace(OUTPUT_KO, OUTPUT_EN)
    if condition == "development_v02":
        return adapted, []
    selected = []
    for prefix in BASELINE_PREFIXES:
        matches = [line for line in template.splitlines() if line.startswith(prefix)]
        require(len(matches) == 1, "baseline source line not uniquely found")
        selected.append(matches[0])
    baseline = "\n\n".join(selected) + "\n"
    require(baseline.count(OUTPUT_KO) == 1, "baseline output clause not uniquely found")
    return baseline.replace(OUTPUT_KO, OUTPUT_EN), [sha(line.encode("utf-8")) for line in selected]


def render(source_root, case, history, current_question, condition, trace):
    """Return a deterministic packet; never call a model or alter supplied facts.

    case is exactly {patient, communication}; history is canonical DTO turns or
    user/assistant messages. English authorship is an input contract, not detected
    or translated. trace is excluded from all model messages and the DTO hash.
    """
    provenance, template = verify_source(source_root)
    validate_case(case)
    nonempty(current_question, "current_question")
    history = normalize_history(history)
    require(isinstance(trace, dict), "trace must be a JSON object")
    canonical(trace)
    for key, value in {"case_id": case["patient"]["case_id"], "condition": condition,
                       "turn_index": len(history) // 2 + 1}.items():
        if key in trace:
            require(trace[key] == value and type(trace[key]) is type(value), "trace mismatch: " + key)
    data = {**deepcopy(case), "history": history, "current_question": current_question}
    system, baseline_lines = system_prompt(template, condition)
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": canonical(data).decode("utf-8")}]
    return {"status": "prepared_only_no_inference", "condition": condition,
            "module_version": MODULE_VERSION, "input": data, "messages": messages,
            "input_sha256": sha(canonical(data)), "messages_sha256": sha(canonical(messages)),
            "system_sha256": sha(system.encode("utf-8")), "trace": deepcopy(trace),
            "trace_sha256": sha(canonical(trace)),
            "provenance": {**provenance,
                "builder_version": "english-output-minimal-adapter-v1",
                "adaptation": "Replace only the unique mandatory Korean-output clause with English-output wording; all other retained system instructions remain Korean.",
                "adaptation_source_clause_sha256": sha(OUTPUT_KO.encode("utf-8")),
                "adaptation_replacement_clause_sha256": sha(OUTPUT_EN.encode("utf-8")),
                "baseline_selected_source_line_sha256": baseline_lines,
                "baseline_identity": "role-only scaffold ablation of selected module; not original PSYCHE",
                "language_contract": "English-authored case values, interviewer question and verbatim prior replies; not language-detected or automatically translated.",
                "validation_scope": "Input/schema/provenance calibration; clinical fidelity not established.",
                "source_redistribution_permission": "not established by this builder; keep source instructions and generated packets local"}}


def write_exclusive(path, packet):
    with Path(path).open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(packet, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def self_check(source_root):
    # Nonclinical authored toy; no historical cases, patient outputs or fixtures.
    case = {"patient": {"case_id": "TOY", "partition": "development",
            "provenance": "authored_nonclinical_offline_toy", "self_understanding": "I am describing a library visit.",
            "facts": [{"id": "visit", "kind": "background", "content": "I returned a book at a library.",
                       "patient_knows": True, "disclosure": "on_topic"}]},
            "communication": {"organization": "Follow a clear sequence.", "spontaneity": "Answer naturally.",
                              "guardedness": "No special reservation.", "expression": "Use ordinary spoken English."}}
    before = canonical(case)
    history = [{"role": "user", "content": "Where did you go?"},
               {"role": "assistant", "content": "I went to a library."}]
    question = "What did you do there?"
    arms = [render(source_root, case, history, question, c, {"condition": c, "case_id": "TOY", "turn_index": 2})
            for c in CONDITIONS]
    require(arms[0]["input"] == arms[1]["input"] and arms[0]["input_sha256"] == arms[1]["input_sha256"], "arm inputs differ")
    require(arms[0]["messages"][1] == arms[1]["messages"][1], "user messages differ")
    require(all([m["role"] for m in arm["messages"]] == ["system", "user"] for arm in arms), "role layout differs")
    require(all("한국어 텍스트만 출력한다" not in arm["messages"][0]["content"]
                and arm["messages"][0]["content"].count(OUTPUT_EN) == 1 for arm in arms), "output adapter failed")
    require(all("trace" not in json.loads(arm["messages"][1]["content"]) for arm in arms), "trace leaked to model")
    require(canonical(case) == before, "input mutated")
    require(render(source_root, case, history, question, CONDITIONS[0], arms[0]["trace"]) == arms[0], "nondeterministic rendering")
    checks = ["same_DTO_and_user_message", "same_role_layout", "minimal_English_output_adapter",
              "trace_excluded", "no_input_mutation", "deterministic_render"]
    bad = deepcopy(case)
    bad["patient"]["partition"] = "heldout_confirmation"
    for name, callback in [
        ("reject_partition", lambda: validate_case(bad)),
        ("reject_incomplete_history", lambda: normalize_history(history[:1])),
        ("reject_bad_condition", lambda: system_prompt("", "unknown")),
        ("reject_changed_template", lambda: system_prompt("missing clause", CONDITIONS[0])),
        ("reject_trace_mismatch", lambda: render(source_root, case, history, question, CONDITIONS[0], {"turn_index": 1})),
    ]:
        try:
            callback()
        except ValueError:
            checks.append(name)
        else:
            raise AssertionError(name)
    with tempfile.TemporaryDirectory(prefix="generation-builder-check-") as folder:
        target = Path(folder) / "toy.json"
        write_exclusive(target, {"toy": True})
        try:
            write_exclusive(target, {"toy": False})
        except FileExistsError:
            require(json.loads(target.read_text()) == {"toy": True}, "existing output modified")
            checks.append("reject_overwrite")
        else:
            raise AssertionError("overwrite accepted")
        changed = Path(folder) / "changed-source"
        (changed / "speech_module").mkdir(parents=True)
        (changed / "speech_module/patient_v02.txt").write_text("Changed nonclinical toy text.", encoding="utf-8")
        try:
            verify_source(changed)
        except ValueError:
            checks.append("reject_changed_source_hash")
        else:
            raise AssertionError("changed source hash accepted")
        escaped = Path(folder) / "escaped-source"
        (escaped / "speech_module").mkdir(parents=True)
        (escaped / "speech_module/patient_v02.txt").symlink_to(changed / "speech_module/patient_v02.txt")
        try:
            verify_source(escaped)
        except ValueError:
            checks.append("reject_source_path_escape")
        else:
            raise AssertionError("source path escape accepted")
    return {"status": "passed", "checks": checks, "check_count": len(checks), "actual_model_calls": 0,
            "scope": "nonclinical toy input construction only; no clinical case or research output generated"}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("verify-source", "self-check", "render"):
        command = sub.add_parser(name)
        command.add_argument("--source-root", type=Path, required=True)
        if name == "render":
            command.add_argument("--case", type=Path, required=True)
            command.add_argument("--history", type=Path)
            question = command.add_mutually_exclusive_group(required=True)
            question.add_argument("--question")
            question.add_argument("--question-file", type=Path)
            command.add_argument("--condition", choices=CONDITIONS, required=True)
            command.add_argument("--trace", type=Path, required=True)
            command.add_argument("--out", type=Path, help="Exclusive creation; otherwise print packet to stdout")
    args = parser.parse_args()
    if args.command == "verify-source":
        output = verify_source(args.source_root)[0]
    elif args.command == "self-check":
        output = self_check(args.source_root)
    else:
        current = args.question if args.question is not None else args.question_file.read_text(encoding="utf-8")
        output = render(args.source_root, read_json(args.case), read_json(args.history) if args.history else [],
                        current, args.condition, read_json(args.trace))
        if args.out:
            write_exclusive(args.out, output)
            output = {"status": "prepared_only_no_inference", "messages_sha256": output["messages_sha256"]}
    print(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
