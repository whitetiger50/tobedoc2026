"""Deterministic packet assembly and explicit generation/import boundary (stdlib only)."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Callable

LEGACY_VERSION = "schizophrenia-speech-m0-v0.1"
V02_VERSION = "schizophrenia-speech-m1-v0.2"
V03_VERSION = "schizophrenia-speech-m2-v0.3"
VERSION = "schizophrenia-speech-m4-v0.4"
MODERN_VERSIONS = frozenset({V03_VERSION, VERSION})
TEMPLATES = {LEGACY_VERSION: Path(__file__).with_name("patient_v01.txt"),
             V02_VERSION: Path(__file__).with_name("patient_v02.txt"),
             V03_VERSION: Path(__file__).with_name("patient_v03.txt"),
             VERSION: Path(__file__).with_name("patient_v04.txt")}
TEMPLATE = TEMPLATES[VERSION]
PARTITIONS = {"development", "reliability_pilot", "heldout_confirmation"}


class MissingCaseDetail(ValueError):
    """A planned question lacks required author-supplied, patient-known facts."""


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def exact(value: object, keys: set[str], where: str) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{where}: expected exactly {sorted(keys)}")
    return value


def nonempty(value: object, where: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where}: nonempty text required")


def validate(data: dict, *, allow_examples: bool = False) -> None:
    keys = {"patient", "communication", "history", "current_question"}
    if allow_examples and isinstance(data, dict) and "speech_examples" in data:
        keys.add("speech_examples")
    exact(data, keys, "input")
    patient = exact(data["patient"], {"case_id", "partition", "provenance", "facts", "self_understanding"}, "patient")
    for key in ("case_id", "provenance", "self_understanding"):
        nonempty(patient[key], f"patient.{key}")
    if patient["partition"] not in PARTITIONS:
        raise ValueError("patient.partition: unknown partition")
    if not isinstance(patient["facts"], list) or not patient["facts"]:
        raise ValueError("patient.facts: nonempty list required")
    ids = set()
    for fact in patient["facts"]:
        exact(fact, {"id", "kind", "content", "patient_knows", "disclosure"}, "fact")
        nonempty(fact["id"], "fact.id")
        nonempty(fact["content"], "fact.content")
        if fact["id"] in ids:
            raise ValueError("duplicate fact id")
        ids.add(fact["id"])
        if fact["kind"] not in {"background", "treatment", "subjective_experience", "subjective_belief"}:
            raise ValueError("unknown fact kind")
        if type(fact["patient_knows"]) is not bool:
            raise ValueError("patient_knows must be bool")
        if fact["disclosure"] not in {"on_topic", "sensitive"}:
            raise ValueError("unknown disclosure policy")
    comm = exact(data["communication"], {"organization", "spontaneity", "guardedness", "expression"}, "communication")
    for key, value in comm.items():
        nonempty(value, f"communication.{key}")
    nonempty(data["current_question"], "current_question")
    history = data["history"]
    if not isinstance(history, list) or len(history) % 2:
        raise ValueError("history must contain complete clinician/patient pairs")
    for i, turn in enumerate(history):
        exact(turn, {"speaker", "text"}, f"history[{i}]")
        if turn["speaker"] != ("clinician" if i % 2 == 0 else "patient"):
            raise ValueError("history must alternate clinician then patient")
        nonempty(turn["text"], f"history[{i}].text")
    if "speech_examples" in data:
        examples = data["speech_examples"]
        if not isinstance(examples, list) or not 1 <= len(examples) <= 3:
            raise ValueError("speech_examples: supply 1..3 optional case-bound examples")
        known = {f["id"] for f in patient["facts"] if f["patient_knows"]}
        for example in examples:
            exact(example, {"context", "utterance", "fact_ids", "provenance", "target_feature", "author_checked"}, "speech_example")
            nonempty(example["context"], "speech_example.context")
            nonempty(example["utterance"], "speech_example.utterance")
            if example["provenance"] != "synthetic_author_example_not_patient_data":
                raise ValueError("Example must be explicitly labeled as synthetic author example")
            if example["target_feature"] not in {"organization", "spontaneity", "guardedness", "expression"}:
                raise ValueError("Example target_feature must name a communication field")
            if example["author_checked"] is not True:
                raise ValueError("Example content must be reviewed by its author; not a clinical validation")
            refs = example["fact_ids"]
            if (not isinstance(refs, list) or not refs or any(not isinstance(r, str) for r in refs)
                    or len(set(refs)) != len(refs) or not set(refs).issubset(known)):
                raise ValueError("Example fact_ids must reference known facts of this case")


def build_packet(data: dict, *, expected_partition: str = "development", module_version: str | None = None,
                 required_fact_ids: tuple[str, ...] = (), question_reviewed: bool = False,
                 allow_experimental_examples: bool = False) -> dict:
    """Never infer trust, summarize history, retrieve cases, or truncate input."""
    version = module_version or VERSION
    if version not in TEMPLATES:
        raise ValueError("Unknown module version")
    if type(question_reviewed) is not bool or type(allow_experimental_examples) is not bool:
        raise ValueError("Author review and experimental option flags must be bool")
    validate(data, allow_examples=version in MODERN_VERSIONS and allow_experimental_examples)
    if data["patient"]["partition"] != expected_partition or expected_partition not in PARTITIONS:
        raise ValueError("partition mismatch: explicitly select the intended research phase")
    if any(not isinstance(ident, str) or not ident for ident in required_fact_ids) or len(set(required_fact_ids)) != len(required_fact_ids):
        raise ValueError("Required fact ids must be unique nonempty strings")
    known = {f["id"] for f in data["patient"]["facts"] if f["patient_knows"]}
    missing = set(required_fact_ids) - known
    if missing:
        raise MissingCaseDetail("needs_case_detail: " + ", ".join(sorted(missing)))
    source = deepcopy(data)
    template_raw = TEMPLATES[version].read_bytes()
    messages = [
        {"role": "system", "content": template_raw.decode("utf-8")},
        {"role": "user", "content": canonical(source).decode("utf-8")},
    ]
    packet = {"module_version": version, "template_sha256": sha(template_raw),
            "input_sha256": sha(canonical(source)), "messages_sha256": sha(canonical(messages)),
            "case_id": source["patient"]["case_id"], "partition": expected_partition,
            "input": source, "messages": messages}
    if required_fact_ids:
        packet["required_fact_ids"] = list(required_fact_ids)
    if version in MODERN_VERSIONS:
        packet["prompt_source_map_sha256"] = sha(TEMPLATES[version].with_suffix(".sources.json").read_bytes())
        packet["question_reviewed"] = question_reviewed
        packet["experimental_examples_enabled"] = allow_experimental_examples
    return packet


def write_json(path: Path, value: object) -> None:
    rendered = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    with path.open("x", encoding="utf-8") as handle:
        handle.write(rendered)


def prepare(data: dict, directory: Path, *, expected_partition: str = "development", module_version: str | None = None,
            required_fact_ids: tuple[str, ...] = (), question_reviewed: bool = False,
            allow_experimental_examples: bool = False) -> dict:
    packet = build_packet(data, expected_partition=expected_partition, module_version=module_version,
                          required_fact_ids=required_fact_ids, question_reviewed=question_reviewed,
                          allow_experimental_examples=allow_experimental_examples)
    directory.mkdir(parents=True, exist_ok=False)
    write_json(directory / "packet.json", packet)
    return packet


def verify_packet(packet: dict) -> None:
    # Verify against the original template/version, including legacy saved runs.
    rebuilt = build_packet(packet["input"], expected_partition=packet["partition"],
                           module_version=packet["module_version"],
                           required_fact_ids=tuple(packet.get("required_fact_ids", [])),
                           question_reviewed=packet.get("question_reviewed", False),
                           allow_experimental_examples=packet.get("experimental_examples_enabled", False))
    if canonical(rebuilt) != canonical(packet):
        raise ValueError("packet/hash/template mismatch; prepare a new versioned run")


def validate_response(response: dict) -> None:
    exact(response, {"text", "model_id", "model_version", "settings", "execution_mode", "provenance"}, "response")
    for key in ("text", "model_id", "model_version", "provenance"):
        nonempty(response[key], key)
    if not isinstance(response["settings"], dict):
        raise ValueError("settings must be a dict; record unavailable controls explicitly")
    if response["execution_mode"] not in {"injected_backend", "manual_subscription", "test_fixture"}:
        raise ValueError("unknown execution_mode")
    canonical(response)  # Reject non-JSON settings, NaN, etc. before writing.


def save_response(directory: Path, packet: dict, raw: object, *, source: str) -> dict:
    # Preserve the returned object even if it fails structural checks. No automatic retry.
    try:
        write_json(directory / "raw_response.json", raw)
    except (TypeError, ValueError) as exc:
        write_json(directory / "result.json", {"status": "unserializable_response_no_retry",
                   "error_type": type(exc).__name__, "raw_json_preserved": False})
        raise
    try:
        validate_response(raw)
    except (ValueError, TypeError) as exc:
        write_json(directory / "result.json", {"status": "invalid_response_no_retry", "error": str(exc)})
        raise
    result = {"status": "fixture_only" if raw["execution_mode"] == "test_fixture" else "response_recorded_unrated",
              "source": source, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "module_version": packet["module_version"], "case_id": packet["case_id"],
              "partition": packet["partition"], "messages_sha256": packet["messages_sha256"],
              "response_sha256": sha(canonical(raw)), "clinical_validation": "not_performed"}
    write_json(directory / "result.json", result)
    # Preserve whitespace and exact text; no role-label stripping or silent editing.
    with (directory / "patient.txt").open("x", encoding="utf-8") as handle:
        handle.write(raw["text"])
    return result


def generate(data: dict, backend: Callable[[list[dict]], dict], directory: Path, *,
             expected_partition: str = "development", module_version: str | None = None,
             required_fact_ids: tuple[str, ...] = (), question_reviewed: bool = False,
             allow_experimental_examples: bool = False) -> str:
    """Call the explicitly supplied backend once; return only patient text.

    Backend receives complete messages and returns text + actual inference metadata.
    No provider is selected and no API client is bundled. The caller owns billing/auth.
    """
    if (module_version or VERSION) in MODERN_VERSIONS and question_reviewed is not True:
        raise MissingCaseDetail("question_not_reviewed: author must check required facts before v0.3+ inference")
    packet = prepare(data, directory, expected_partition=expected_partition, module_version=module_version,
                     required_fact_ids=required_fact_ids, question_reviewed=question_reviewed,
                     allow_experimental_examples=allow_experimental_examples)
    try:
        raw = backend(deepcopy(packet["messages"]))
    except Exception as exc:
        # Exception strings may contain provider secrets; keep only class name.
        write_json(directory / "result.json", {"status": "backend_failed_no_retry", "error_type": type(exc).__name__})
        raise
    save_response(directory, packet, raw, source="backend_return")
    return raw["text"]


def import_response(directory: Path, response: dict) -> dict:
    """Import an actual manually obtained output; never supply invented model metadata."""
    packet = json.loads((directory / "packet.json").read_text(encoding="utf-8"))
    verify_packet(packet)
    if packet["module_version"] in MODERN_VERSIONS and packet.get("question_reviewed") is not True:
        raise MissingCaseDetail("question_not_reviewed: do not import output for an unreviewed v0.3+ question")
    for name in ("raw_response.json", "result.json", "patient.txt"):
        if (directory / name).exists():
            raise FileExistsError("run already has output; use a new run, never overwrite")
    return save_response(directory, packet, response, source="manual_import_unverified")
