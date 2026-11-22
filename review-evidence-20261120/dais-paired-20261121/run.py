"""Verify the public release locally or obtain isolated ratings of 14 first replies."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
SHORT = HERE.parent / "short-replies-20261121"
sys.path.insert(0, str(SHORT))
import collect as prior

REFERENCE = HERE.parent / "dais-first-reply-v1/private/manifest.json"
RELEASE = "2f8418a1d466cb41f8fb4deadd8aa12f1f4085766f5c811a69e52885fbe32721"
ENGINES = ("opus", "gpt")
TASKS = ("type", "clinical")
ROUNDS = (1, 2)


def load_cases():
    clinical = prior.module("clinical_form", prior.READER)
    response = prior.module("type_form", prior.TYPE_READER)
    frozen = json.loads(REFERENCE.read_text())["cases"]
    items, groups, filenames = {}, {}, {}
    records = response.collect()
    assert len(frozen) == len(records) == 14
    for i, (q, source, data) in enumerate(records):
        ref = frozen[i]
        assert (i+1, q, source, response.digest(response.dump(data))) == (
            ref["blind"], ref["group"], ref["source_digest"], ref["input_digest"])
        name = f"R{i+1:02}"
        groups[name], filenames[name] = q, source
        items[name] = ({"history": [], "question": data["question"], "answer": data["reply"]},)
    assert Counter(groups.values()) == {"Q2": 7, "Q3": 7} and len(set(filenames.values())) == 14
    def type_packet(d):
        return {"instructions": response.TYPE_PROMPT, "dialogue": d, "form": response.TYPE_FORM}
    sources = {
        "type": SimpleNamespace(EXAMPLES=items, RUBRIC=response.TYPE_PROMPT, packet=type_packet,
                                blank_form=lambda: response.TYPE_FORM),
        "clinical": SimpleNamespace(EXAMPLES=items, RUBRIC=clinical.RUBRIC, packet=clinical.packet,
                                    blank_form=clinical.blank_form),
    }
    return groups, filenames, sources


def verify_release(archive):
    assert prior.digest(archive) == RELEASE
    groups, files, _ = load_cases()
    prefix = "DAIS-C-Annotated - Upload/DAI-C-CL/Interactional/Full tagged pass/"
    members = subprocess.check_output(["bsdtar", "-tf", str(archive)], text=True).splitlines()
    local, = prior.EVIDENCE.parent.glob("DAIS_C_*/DAIS-C-Annotated - Upload")
    verified = {}
    for member in members:
        name = Path(member).name
        name_hash = hashlib.sha256(name.encode()).hexdigest()
        if not member.startswith(prefix) or name_hash not in files.values():
            continue
        original = subprocess.check_output(["bsdtar", "-xOf", str(archive), member])
        local_file = local / Path(member).relative_to("DAIS-C-Annotated - Upload")
        assert local_file.read_bytes() == original
        verified[name_hash] = hashlib.sha256(original).hexdigest()
    assert set(verified) == set(files.values())
    summary = {"archive_sha256": RELEASE, "verified_files": len(verified), "groups": dict(Counter(groups.values())),
               "source_sha256": verified, "manifest_sha256": prior.digest(REFERENCE),
               "frozen_rubrics": {p.name: prior.digest(p) for p in (prior.READER, prior.TYPE_READER)}}
    dest = HERE / "release-verification.json"
    if dest.exists():
        assert json.loads(dest.read_text()) == summary
    else:
        dest.write_text(json.dumps(summary, indent=2)+"\n")
    print("Public release file byte matches", len(verified), dict(Counter(groups.values())))


def read_model(engine, round_number):
    check = json.loads((HERE / "release-verification.json").read_text())
    assert check["archive_sha256"] == RELEASE and check["verified_files"] == 14
    assert prior.digest(REFERENCE) == check["manifest_sha256"]
    for path in (prior.READER, prior.TYPE_READER):
        assert prior.digest(path) == check["frozen_rubrics"][path.name]
    groups, _, packets = load_cases()
    if engine == "opus":
        transport = prior.module("opus_transport", prior.PREVIOUS / "opus/run.py")
        cli, env, _, _ = transport.runtime()
    else:
        transport = prior.module("gpt_transport", prior.PREVIOUS / "gpt/collect.py")
    for task in TASKS:
        target = HERE / "private" / f"pass{round_number}" / engine / task
        target.mkdir(parents=True, exist_ok=True, mode=0o700)
        for directory in ("raw", "forms", ("meta" if engine == "gpt" else "receipts")):
            (target / directory).mkdir(exist_ok=True)
        source = packets[task]
        if engine == "opus":
            transport.HERE = target
            def rate(case):
                transport.record(case, source, cli, env)
        else:
            transport.OUTPUT = target
            (target / "packets").mkdir(exist_ok=True)
            def rate(case):
                transport.rate(source, case)
        order = list(groups)
        random.Random(f"dais-read-{engine}-{round_number}-{task}").shuffle(order)
        todo = [k for k in order if not (target / "forms" / (k+".json")).is_file()]
        with ThreadPoolExecutor(max_workers=3) as pool:
            list(pool.map(rate, todo))


if __name__ == "__main__":
    os.umask(0o077)
    sys.dont_write_bytecode = True
    if len(sys.argv) == 3 and sys.argv[1] == "verify":
        verify_release(Path(sys.argv[2]))
    elif len(sys.argv) == 3 and sys.argv[1] in ENGINES and sys.argv[2] in ("1", "2"):
        os.environ["PATH"] = str(Path.home() / ".local/bin") + os.pathsep + os.environ["PATH"]
        read_model(sys.argv[1], int(sys.argv[2]))
    else:
        raise SystemExit("Specify verify ARCHIVE or ENGINE ROUND.")
