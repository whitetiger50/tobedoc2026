"""Collect blinded first readings of the nine synthetic examples only."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parent
PREVIOUS = EVIDENCE / "boundary-calibration-20261121"
READER = EVIDENCE.parent / "tobedoc2026/docs/2026-11-20-english-clinical-profile/reader.py"
TYPE_READER = EVIDENCE / "dais-first-reply-v1/read_local.py"


def module(name, source):
    spec = importlib.util.spec_from_file_location(name, source)
    required = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(required)
    return required


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs():
    clinical = module("clinical_rubric", READER)
    response = module("locked_response_form", TYPE_READER)
    examples = json.loads((HERE / "examples.json").read_text())
    assert len(examples) == 9
    assert all(set(d) == {"question", "answer"} and 2 <= len(d["answer"].split()) <= 3
               for d in examples.values())
    data = {name: ({"history": [], **d},) for name, d in examples.items()}
    def type_packet(d):
        return {"instructions": response.TYPE_PROMPT, "dialogue": d, "form": response.TYPE_FORM}
    return {
        "clinical": SimpleNamespace(EXAMPLES=data, RUBRIC=clinical.RUBRIC, packet=clinical.packet,
                                    blank_form=clinical.blank_form),
        "type": SimpleNamespace(EXAMPLES=data, RUBRIC=response.TYPE_PROMPT, packet=type_packet,
                                blank_form=lambda: response.TYPE_FORM),
    }


def freeze():
    stamps = {str(p.relative_to(EVIDENCE.parent)): digest(p) for p in
              [HERE / "design.ko.md", HERE / "examples.json", READER, TYPE_READER,
               PREVIOUS / "gpt/collect.py", PREVIOUS / "opus/run.py", Path(__file__).resolve()]}
    return json.dumps(stamps, indent=2) + "\n"


def collect(engine, task):
    packets = inputs()[task]
    target = HERE / engine / task
    target.mkdir(parents=True, exist_ok=True)
    if engine == "gpt":
        transport = module("codex_transport", PREVIOUS / "gpt/collect.py")
        transport.OUTPUT = target
        for folder in ("forms", "raw", "meta", "packets"):
            (target / folder).mkdir(exist_ok=True)
        def rate(case):
            transport.rate(packets, case)
    else:
        transport = module("claude_transport", PREVIOUS / "opus/run.py")
        transport.HERE = target
        os.environ["PATH"] = str(Path.home() / ".local/bin") + os.pathsep + os.environ["PATH"]
        cli, env, _, _ = transport.runtime()
        def rate(case):
            transport.record(case, packets, cli, env)
    # Existing first outputs, successful or malformed, are always retained.
    todo = [c for c in packets.EXAMPLES if not (target / "forms" / (c + ".json")).exists()
            and not (target / "raw" / (c + ".txt")).exists()]
    with ThreadPoolExecutor(max_workers=3) as workers:
        list(workers.map(rate, todo))


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    args = sys.argv[1:]
    signature = HERE / "frozen-inputs.json"
    if args == ["freeze"]:
        inputs()
        with signature.open("x") as handle:
            handle.write(freeze())
    elif len(args) == 2 and args[0] in {"gpt", "opus"} and args[1] in {"clinical", "type"}:
        assert signature.read_text() == freeze(), "A frozen input or transport has changed"
        collect(*args)
    else:
        raise SystemExit("Specify freeze or {gpt,opus} {clinical,type}.")
