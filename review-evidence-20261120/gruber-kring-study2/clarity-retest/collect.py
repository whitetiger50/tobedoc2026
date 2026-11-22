"""Collect only the nine fixed, authored narratives, twice per reader. Never generate narratives."""
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
BOUNDARY = HERE.parent / "boundary"
sys.path.insert(0, str(BOUNDARY))
import calibrate as fixed


def signatures():
    paths = [HERE / "examples.json", HERE / "plan.json", Path(__file__), HERE.parent / "DESIGN.ko.md",
             Path(fixed.__file__), *fixed.TRANSPORTS.values()]
    return {str(p.relative_to(HERE.parents[1])): sha256(p.read_bytes()).hexdigest() for p in paths}


def validate(cases, plan):
    assert len(cases) == 9 and all(set(v) == {"question", "answer"} for v in cases.values())
    triplets = plan["triplets_in_expected_clarity_order"].values()
    assert sorted(k for tri in triplets for k in tri) == sorted(cases)
    for tri in triplets:
        assert len(tri) == 3 and len({cases[k]["question"] for k in tri}) == 1
    for first, second in plan["orders"].values():
        assert sorted(first) == sorted(second) == sorted(cases)
        assert all(x != y for x, y in zip(first, second))


def collect(engine, cases, orders):
    spec = importlib.util.spec_from_file_location(engine + "_transport", fixed.TRANSPORTS[engine])
    transport = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transport)
    reader = SimpleNamespace(EXAMPLES={k: (v,) for k, v in cases.items()}, RUBRIC=fixed.RUBRIC,
                             packet=fixed.packet, blank_form=fixed.form)
    if engine == "opus":
        cli, env, _, _ = transport.runtime()
    for round_number, order in enumerate(orders, start=1):
        target = HERE / f"round{round_number}" / engine
        target.mkdir(parents=True, exist_ok=True)
        if engine == "gpt":
            transport.OUTPUT = target
            for folder in ("forms", "raw", "meta", "packets"):
                (target / folder).mkdir(exist_ok=True)
        else:
            transport.HERE = target
        for k in order:
            if (target / "forms" / (k + ".json")).exists():
                continue
            if engine == "gpt":
                transport.rate(reader, k)
            else:
                transport.record(k, reader, cli, env)


def main(action):
    cases = fixed.read(HERE / "examples.json")
    plan = fixed.read(HERE / "plan.json")
    validate(cases, plan)
    assert fixed.hashes() == fixed.read(fixed.MANIFEST)["sha256"]
    manifest = HERE / "freeze.json"
    if action == "freeze":
        assert not any(HERE.glob("round*"))
        with manifest.open("x") as f:
            json.dump({"frozen_utc": datetime.now(timezone.utc).isoformat(), "sha256": signatures()}, f, indent=2)
            f.write("\n")
    else:
        assert fixed.read(manifest)["sha256"] == signatures()
        collect(action, cases, plan["orders"][action])


if __name__ == "__main__":
    if sys.argv[1:] not in (["freeze"], ["opus"], ["gpt"]):
        raise SystemExit("Use freeze, opus or gpt.")
    main(sys.argv[1])
