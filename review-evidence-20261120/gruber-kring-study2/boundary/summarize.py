"""Verify the two readers' first responses, then evaluate the frozen paired comparisons offline."""
from datetime import datetime
from hashlib import sha256
import json
from operator import eq, gt, lt
from pathlib import Path
import re
from statistics import mean

from calibrate import HERE, MANIFEST, hashes, packet, read

SCALES = ("elaboration", "meaning_clarity")
RELATIONS = {"equal": eq, "decrease": lt, "increase": gt}


def load_scores(engine, case, dialogue, frozen):
    root = HERE / engine
    payload = json.dumps(packet(dialogue), ensure_ascii=False, indent=2) + "\n"
    if engine == "opus":
        receipt = read(root / "receipts" / (case + ".json"))
        raw = root / "raw" / (case + ".jsonl")
        trace = [json.loads(line) for line in raw.read_text().splitlines() if line.strip()]
        [end] = [ev for ev in trace if ev["type"] == "result"]
        assert end["subtype"] == "success" and receipt["turns"] == 1 and not receipt["is_error"]
        assert receipt["init_model"] == "claude-opus-5-5" and receipt["assistant_models"] == ["claude-opus-5-5"]
        assert not any(receipt[field] for field in ("tools", "mcp_servers", "skills", "plugins", "tool_blocks", "hook_events"))
        assert not any((receipt["server_tool_use"] or {}).values())
        original = end["result"]
        assert original == (root / "raw" / (case + ".txt")).read_text()
        session, service_models = receipt["session_id"], receipt["assistant_models"]
    else:
        receipt = read(root / "meta" / (case + ".json"))
        raw = root / "raw" / (case + ".txt")
        assert payload == (root / "packets" / (case + ".json")).read_text()
        assert receipt["cli_model"] == receipt["requested_model"] == "gpt-6.1-sol"
        assert receipt["provider"] == "openai" and not receipt["tool_events_cli"]
        assert all(model.startswith("gpt-6.1-sol") for model in receipt["service_response_models"])
        original = raw.read_text()
        session, service_models = receipt["cli_session_id"], receipt["service_response_models"]
    assert datetime.fromisoformat(frozen) < datetime.fromisoformat(receipt["started_utc"])
    assert session and receipt["exit_code"] == 0
    assert receipt["packet_sha256"] == sha256(payload.encode()).hexdigest()
    assert receipt["raw_sha256"] == sha256(raw.read_bytes()).hexdigest()
    ratings = read(root / "forms" / (case + ".json"))
    fence = re.fullmatch(r"\s*```(?:json)?\s*\n(.*?)\n```\s*", original, re.DOTALL | re.I)
    assert ratings == json.loads(fence.group(1) if fence else original)
    assert ratings["status"] in ("no_narrative", "rated")
    assert (ratings["status"] == "rated") == bool(ratings["events"])
    scores = {}
    for scale in SCALES:
        for event in ratings["events"]:
            assert type(event[scale]) is int and 1 <= event[scale] <= 3 and event[scale + "_reason"].strip()
        scores[scale] = mean(event[scale] for event in ratings["events"]) if ratings["events"] else None
    return {"scores": scores, "events": len(ratings["events"]), "session": session, "service_models": service_models}


def main():
    frozen = read(MANIFEST)
    assert hashes() == frozen["sha256"]
    cases = read(HERE / "examples.json")
    comparisons = read(HERE / "expectations.json")["comparisons"]
    readers = {}
    for engine in ("opus", "gpt"):
        examples = {k: load_scores(engine, k, v, frozen["frozen_utc"]) for k, v in cases.items()}
        assert len({v["session"] for v in examples.values()}) == len(cases)
        checks = {}
        for pair in comparisons:
            results = {}
            for scale in SCALES:
                if scale in pair:
                    before = examples[pair["before"]]["scores"][scale]
                    after = examples[pair["after"]]["scores"][scale]
                    results[scale] = None if None in (before, after) else RELATIONS[pair[scale]](after, before)
            checks[pair["pair"]] = results
        readers[engine] = {"examples": examples, "checks": checks}
    agreement = {}
    for scale in SCALES:
        matrix = [[0] * 3 for _ in range(3)]
        for k in cases:
            a, b = (readers[engine]["examples"][k] for engine in ("opus", "gpt"))
            # These six prompts were authored as single activities. Preserve event counts explicitly.
            if a["events"] == b["events"] == 1:
                matrix[a["scores"][scale] - 1][b["scores"][scale] - 1] += 1
        agreement[scale] = {"matrix_rows_opus_columns_gpt": matrix, "eligible": sum(map(sum, matrix)),
                            "exact": sum(matrix[i][i] for i in range(3))}
    counts = {k: len(re.findall(r"[A-Za-z]+(?:['’][A-Za-z]+)*", v["answer"])) for k, v in cases.items()}
    result = {"word_counts": counts, "readers": readers, "agreement": agreement}
    (HERE / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    for engine, data in readers.items():
        print(engine, data["checks"])
        print({k: (v["events"], list(v["scores"].values()), v["service_models"]) for k, v in data["examples"].items()})
    print("agreement", agreement)


if __name__ == "__main__":
    main()
