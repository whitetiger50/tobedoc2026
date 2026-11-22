"""Verify packet hashes and score the first readings without making model calls."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

import collect

HERE = Path(__file__).resolve().parent
GROUPS = {"affirm_or_deny": ("S17", "S64", "S79"),
          "unsure": ("S41", "S85", "S38"),
          "clarification": ("S26", "S52", "S93")}


def read_json(path):
    return json.loads(path.read_text())


def check_receipt(engine, folder, case, expected_packet):
    if engine == "opus":
        rec = read_json(folder / "receipts" / (case + ".json"))
        assert rec["assistant_models"] == ["claude-opus-5-5"] and rec["turns"] == 1
        assert not any(rec[k] for k in ("tools", "plugins", "mcp_servers", "tool_blocks", "hook_events"))
        assert not any(rec["server_tool_use"].values()) and not rec["is_error"]
        assert collect.digest(folder / "raw" / (case + ".jsonl")) == rec["raw_sha256"]
        session = rec["session_id"]
    else:
        rec = read_json(folder / "meta" / (case + ".json"))
        assert rec["cli_model"] == "gpt-6.1-sol" and not rec["tool_events_cli"]
        assert read_json(folder / "packets" / (case + ".json")) == expected_packet
        assert collect.digest(folder / "raw" / (case + ".txt")) == rec["raw_sha256"]
        session = rec["cli_session_id"]
    body = json.dumps(expected_packet, indent=2, ensure_ascii=False) + "\n"
    assert rec["exit_code"] == 0 and rec["packet_sha256"] == hashlib.sha256(body.encode()).hexdigest()
    assert session
    return session


def validated_type(rules, row, answer):
    if not isinstance(row, dict) or set(row) != set(rules.TYPE_FORM["properties"]):
        raise ValueError("Unexpected response-type fields")
    if (row["type"] not in rules.TYPES + ["ambiguous"] or
        not isinstance(row["also_requests_clarification"], bool) or
        not isinstance(row["alternatives"], list) or any(i not in rules.TYPES for i in row["alternatives"]) or
        not isinstance(row["reason"], str) or not isinstance(row["evidence"], list)):
        raise ValueError("Invalid response-type fields")
    return rules.check_type(row, answer)


def main():
    assert (HERE / "frozen-inputs.json").read_text() == collect.freeze()
    clinical = collect.module("form_v1", collect.READER)
    response = collect.module("interaction", collect.TYPE_READER)
    sources = collect.inputs()
    models = {}
    for engine in ("opus", "gpt"):
        cases, sessions, fences = {}, set(), []
        for group, ids in GROUPS.items():
            for case in ids:
                entry = {"group": group, "expected_type": "clarification" if group == "clarification" else "direct"}
                for task, source in sources.items():
                    data = source.EXAMPLES[case][0]
                    folder = HERE / engine / task
                    sid = check_receipt(engine, folder, case, source.packet(data))
                    assert sid not in sessions
                    sessions.add(sid)
                    original = (folder / "raw" / (case + ".txt")).read_text()
                    fence = re.fullmatch(r"\s*```(?:json)?\s*\n(.*?)\n```\s*", original, re.DOTALL | re.IGNORECASE)
                    if fence:
                        fences.append(case + "/" + task)
                    try:
                        form = read_json(folder / "forms" / (case + ".json"))
                        assert json.loads(fence[1] if fence else original) == form
                        if task == "clinical":
                            result = clinical.validate(data, form)
                            entry[task] = {k: v["status"] for k, v in result["items"].items()}
                            if result["errors"]:
                                entry["clinical_errors"] = result["errors"]
                        else:
                            entry[task] = validated_type(response, form, data["answer"])["type"]
                    except (ValueError, KeyError, TypeError) as err:
                        entry[task + "_errors"] = [str(err)]
                cases[case] = entry
        grouped = {}
        for group, ids in GROUPS.items():
            summaries = {}
            for feature in clinical.FEATURES:
                summaries[feature] = dict(Counter(cases[c].get("clinical", {}).get(feature, "invalid") for c in ids))
            grouped[group] = summaries
        models[engine] = {"unique_sessions": len(sessions), "outer_fences": len(fences),
                          "types_correct": sum(v.get("type") == v["expected_type"] for v in cases.values()),
                          "error_count": sum(k.endswith("_errors") for v in cases.values() for k in v),
                          "cases": cases, "clinical_by_group": grouped}
    (HERE / "results.json").write_text(json.dumps(models, ensure_ascii=False, indent=2) + "\n")
    for model, result in models.items():
        print(model, "types correct", result["types_correct"], "errors", result["error_count"],
              "unique sessions", result["unique_sessions"], "outer fences", result["outer_fences"])
        for case, row in result["cases"].items():
            print(case, row.get("type"), *row.get("clinical", {}).values())


if __name__ == "__main__":
    main()
