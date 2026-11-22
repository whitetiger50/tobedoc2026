"""Apply the original item validator and prespecified gate after response collection."""
import hashlib
import json

from collect import MODEL, OUTPUT, READER_FILE, TRANSPORT, load_reader, write_json


def main():
    mod = load_reader()
    forms = OUTPUT / "forms"
    comparison = {}
    for case, (dialogue, key) in mod.EXAMPLES.items():
        raw = mod.read_json(forms / (case + ".json"))
        validated = mod.validate(dialogue, raw)
        comparison[case] = {
            "validation": validated,
            "expected": key,
            "disagreements": {
                feature: {"expected": key[feature], "observed": row["status"]}
                for feature, row in validated["items"].items() if row["status"] != key[feature]
            },
        }
    write_json(OUTPUT / "validation.json", comparison)
    aggregate = mod.calibrate(forms)
    write_json(OUTPUT / "calibration.json", aggregate)
    meta = [mod.read_json(OUTPUT / "meta" / (case + ".json")) for case in mod.EXAMPLES]
    def sha256(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    audit = {
        "requested_model": MODEL,
        "cli_models": sorted({row["cli_model"] for row in meta}),
        "separate_service_models_captured": sorted({model for row in meta for model in row["service_response_models"]}),
        "model_identity_evidence": "The Codex session header reports the model selected for each call. A separate server-side model or dated snapshot was not exposed in the captured metadata.",
        "authentication": "Existing ChatGPT login, with forced_login_method=chatgpt; no API key supplied",
        "cli_version": "codex-cli 0.171.0-alpha.13",
        "transport_instruction": TRANSPORT,
        "original_reader_sha256": sha256(READER_FILE),
        "unique_successful_cli_sessions": len({row["cli_session_id"] for row in meta}),
        "visible_cli_tool_events": sum(len(row["tool_events_cli"]) for row in meta),
        "cli_reported_tokens": sum(row["token_count_cli"] for row in meta),
        "response_free_transport_failures": len(list((OUTPUT / "meta").glob("*.transport-failure-*.json"))),
        "all_form_bytes_equal_raw_bytes": all(sha256(forms / (case + ".json")) == sha256(OUTPUT / "raw" / (case + ".txt")) for case in mod.EXAMPLES),
        "all_saved_packets_match_reader_packet": all(mod.read_json(OUTPUT / "packets" / (case + ".json")) == mod.packet(dialogue)
                                                       for case, (dialogue, _) in mod.EXAMPLES.items()),
        "all_packet_hashes_match_transmitted_stdin": all(row["packet_sha256"] == sha256(OUTPUT / "packets" / (row["case"] + ".json")) for row in meta),
        "complete": aggregate["complete"], "primary_gate_passed": aggregate["passed"],
        "exact_four_state_agreements": sum(
            row["expected"][feature] == result["status"]
            for row in comparison.values() for feature, result in row["validation"]["items"].items()
        ),
        "total_expected_item_judgments": len(mod.FEATURES) * len(mod.EXAMPLES),
    }
    write_json(OUTPUT / "run_summary.json", audit)
    print("Original reader SHA-256", hashlib.sha256(READER_FILE.read_bytes()).hexdigest())
    print("Complete", aggregate["complete"], "of", aggregate["form_count"], "passed", aggregate["passed"])
    for feature, row in aggregate["items"].items():
        print(feature, row["present_correct"], "/", row["expected_present"], "present,",
              row["absent_correct"], "/", row["expected_absent"], "absent")
    print("Disagreements", json.dumps({case: row["disagreements"] for case, row in comparison.items()
                                       if row["disagreements"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
