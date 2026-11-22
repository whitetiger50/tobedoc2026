"""Freeze six authored boundary cases, then collect one isolated reading per case and provider."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parents[1] / "boundary-calibration-20261121"
TRANSPORTS = {"gpt": PREVIOUS / "gpt/collect.py", "opus": PREVIOUS / "opus/run.py"}
MANIFEST = HERE / "freeze.json"
RUBRIC = """Read the interview question and the speaker's answer. Score the speaker's text on two separate scales.
Elaboration: 1 = the account adds at least one detail beyond naming the event or activity and is self-contained. 2 = some detail is given, but information important for understanding the event or activity is missing. 3 = the answer only identifies the event or activity and adds no further information. Use the contribution of the details to the account, not a count of details or words. For an everyday task, a route or procedure itself is appropriate content.
Meaning clarity: 1 = the speaker's intended meaning can be followed. 2 = it is generally understandable, but some important connections or references are unclear. 3 = the central meaning is hard to follow because of such features as contradictions, unspecified referents, word substitutions or abrupt shifts.
Rate each distinct event or activity once. Steps of a single routine or details of the same event belong in one entry. A brief response that names an event or activity is eligible. Use status "no_narrative" with an empty events list if the speaker only asks for clarification or says they cannot remember. Do not treat a confusing narrative as missing. Otherwise set status to "rated". Give each event an integer from 1 to 3 on each scale, with a brief text-based reason for each score. Return only the completed JSON form."""


def form():
    return {"status": None, "events": [{"elaboration": None, "elaboration_reason": None,
                                       "meaning_clarity": None, "meaning_clarity_reason": None}]}


def read(path):
    return json.loads(path.read_text())


def packet(dialogue):
    return {"instructions": RUBRIC, "dialogue": dialogue, "form": form()}


def hashes():
    paths = [HERE.parent / "DESIGN.ko.md", HERE / "examples.json", HERE / "expectations.json",
             Path(__file__), *TRANSPORTS.values()]
    return {str(p.relative_to(HERE.parents[1])): sha256(p.read_bytes()).hexdigest() for p in paths}


def collect(engine, cases, order):
    reader = SimpleNamespace(EXAMPLES={k: (v,) for k, v in cases.items()}, RUBRIC=RUBRIC,
                             packet=packet, blank_form=form)
    target = HERE / engine
    target.mkdir(exist_ok=True)
    spec = importlib.util.spec_from_file_location(engine + "_transport", TRANSPORTS[engine])
    transport = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transport)
    if engine == "gpt":
        transport.OUTPUT = target
        for folder in ("forms", "raw", "meta", "packets"):
            (target / folder).mkdir(exist_ok=True)

        def rate(case):
            transport.rate(reader, case)
    else:
        transport.HERE = target
        cli, env, _, _ = transport.runtime()

        def rate(case):
            transport.record(case, reader, cli, env)

    pending = [case for case in order if not (target / "forms" / (case + ".json")).exists()]
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(rate, pending))


def main(action):
    cases = read(HERE / "examples.json")
    plan = read(HERE / "expectations.json")
    assert len(cases) == 6 and all(set(v) == {"question", "answer"} for v in cases.values())
    assert all(len(o) == 6 and set(o) == set(cases) for o in plan["order"].values())
    assert all(cases[p["before"]]["question"] == cases[p["after"]]["question"] for p in plan["comparisons"])
    if action == "freeze":
        assert not any((HERE / e).exists() for e in TRANSPORTS)
        with MANIFEST.open("x") as f:
            json.dump({"frozen_utc": datetime.now(timezone.utc).isoformat(), "sha256": hashes()},
                      f, indent=2)
            f.write("\n")
    else:
        assert read(MANIFEST)["sha256"] == hashes(), "Frozen inputs differ"
        collect(action, cases, plan["order"][action])


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    if sys.argv[1:] not in (["freeze"], ["opus"], ["gpt"]):
        raise SystemExit("Use freeze, opus or gpt.")
    main(sys.argv[1])
