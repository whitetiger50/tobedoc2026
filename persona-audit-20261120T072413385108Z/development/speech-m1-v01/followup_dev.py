"""Three targeted v0.2 functional outputs, not a repeated review or effect comparison."""
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
from speech_module.core import MissingCaseDetail, TEMPLATE, VERSION, build_packet, generate

HERE = Path(__file__).resolve().parent


def freeze():
    targets = []
    for ident, turn, required in [("DEV-M0-01", 2, ("voice",)),
                                  ("DEV-M0-02", 1, ("sleep_voice_relation",)),
                                  ("DEV-M0-03", 3, ("today_activity",))]:
        original = json.loads((HERE / "runs-v01" / ident / f"turn{turn:02d}/packet.json").read_text())["input"]
        data = deepcopy(original)
        blocked = False
        try:
            build_packet(original, required_fact_ids=required)
        except MissingCaseDetail:
            blocked = True
        additions = []
        if ident.endswith("02"):
            additions = [{"id": "sleep_voice_relation", "kind": "background", "patient_knows": True,
                          "disclosure": "on_topic", "content": "밤에 자주 깨는 이유는 본인도 확실히 모른다. 소리 경험이 잠에서 깨는 원인인지도 본인은 확실히 모른다."}]
        elif ident.endswith("03"):
            additions = [{"id": "today_activity", "kind": "background", "patient_knows": True,
                          "disclosure": "on_topic", "content": "오늘 오후에는 집 근처를 걸었다."}]
        data["patient"]["facts"].extend(additions)
        targets.append({"case_id": ident, "target_turn_in_v01": turn, "required_fact_ids": list(required),
                        "original_input_blocked_before_model_call": blocked, "new_author_defined_synthetic_facts": additions,
                        "addition_provenance": "Codex authored hypothetical development facts before v02 generation; not recovered patient data or model observations",
                        "input": data})
    plan = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "module_version": VERSION,
            "template_sha256": hashlib.sha256(TEMPLATE.read_bytes()).hexdigest(), "targets": targets,
            "scope": "functional_followup_only_unrated; profile enrichment in two cases confounds any before_after_prompt_effect",
            "additional_review_calls": 0}
    dump(HERE / "followup-plan-v02.json", plan)
    return plan


def run_target(target):
    directory = HERE / "runs-v02-functional" / target["case_id"]
    def backend(messages):
        return call_once("codex", messages[1]["content"], messages[0]["content"], directory / "transport")
    answer = generate(target["input"], backend, directory, required_fact_ids=tuple(target["required_fact_ids"]))
    print(target["case_id"] + " functional response recorded, not rescored", flush=True)
    return {"case_id": target["case_id"], "text": answer, "rating": None}


def main():
    plan = freeze()
    with ThreadPoolExecutor(max_workers=3) as pool:
        outputs = list(pool.map(run_target, plan["targets"]))
    dump(HERE / "followup-outputs-v02.json", {"outputs": outputs, "scope": plan["scope"], "additional_review_calls": 0})


if __name__ == "__main__":
    main()
