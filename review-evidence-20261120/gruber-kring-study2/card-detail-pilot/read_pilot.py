"""Read 72 masked question/answer pairs with the unchanged Study 2 reader."""
import argparse
from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys


HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE.parent / "main"))
import read_blind as reader


N = 72
reader.HERE = HERE
reader.BLIND = HERE / "blind.json"
reader.ROOT = HERE / "readers"
reader.FROZEN = reader.ROOT / "freeze.json"
reader.SEED = "GK-card-detail-pilot-reader-v1"


def masked_inputs():
    rows = reader.read(reader.BLIND)
    if not isinstance(rows, list) or len(rows) != N:
        raise ValueError("Expected 72 masked dialogues.")
    out = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"uid", "question", "answer"}:
            raise ValueError("Unexpected keys in a masked dialogue.")
        if not all(isinstance(v, str) and v.strip() for v in row.values()):
            raise ValueError("Dialogue and identifier must be nonempty strings.")
        uid = row["uid"]
        if not re.fullmatch(r"[A-Za-z0-9_-]+", uid) or uid in out:
            raise ValueError("Invalid or duplicate opaque identifier.")
        out[uid] = {"question": row["question"], "answer": row["answer"]}
    return out


reader.open_inputs = masked_inputs
original_manifest = reader.inputs_manifest


def manifest(cases):
    result = original_manifest(cases)
    if result["orders"]["gpt"] == result["orders"]["opus"]:
        raise ValueError("Reader orders coincide.")
    result["pilot_runner_sha256"] = reader.digest(Path(__file__).resolve())
    result["original_reader_runner_sha256"] = reader.digest(Path(reader.__file__))
    return result


reader.inputs_manifest = manifest


def snapshot(engine, cases, frozen):
    """Verify the provider evidence and score only the accepted first output."""
    rows, receipts, sessions = [], {}, set()
    counts, failures = Counter(), Counter()
    order = frozen["spec"]["orders"][engine]
    for uid in order:
        job = reader.ROOT / engine / uid
        attempt = job / reader.read(job / "accepted.json")["attempt"]
        payload = reader.packet_bytes(cases[uid])
        assert sha256(payload).hexdigest() == frozen["spec"]["payload_sha256"][uid]
        content, session, service = reader.verified_response(
            engine, attempt, uid, payload, frozen["frozen_utc"]
        )
        if session in sessions:
            raise ValueError("Reader session used more than once.")
        sessions.add(session)
        row = reader.first_score(uid, engine, content)
        rows.append(row)
        counts[row["status"]] += 1
        counts["server_model_ids_available"] += bool(service)
        provider_folder = "receipts" if engine == "opus" else "meta"
        receipts[uid] = reader.digest(attempt / provider_folder / (uid + ".json"))
        failures.update(reader.read(p)["kind"] for p in job.glob("attempt-*/failure.json"))
    assert len(rows) == len(sessions) == len(cases) == N
    encoded = json.dumps(rows, ensure_ascii=False, sort_keys=True).encode()
    audit = {"counts": dict(counts), "transport_failures": dict(failures),
             "receipt_hashes": receipts, "score_rows_sha256": sha256(encoded).hexdigest(),
             "reader_freeze_sha256": reader.digest(reader.FROZEN)}
    return rows, sessions, audit


def collect_and_lock(engine, workers):
    cases, frozen = reader.load_frozen()
    target = reader.ROOT / engine
    lock = target / "sealed.json"
    if not lock.is_file():
        for uid in cases:
            job = target / uid
            if (job / "accepted.json").exists():
                continue
            for attempt in job.glob("attempt-*"):
                if (attempt / "forms" / (uid + ".json")).is_file():
                    continue    # Re-verify and retain a completed first form.
                evidence = attempt / "failure.json"
                if not evidence.is_file() or reader.read(evidence)["kind"] != "subscription_limit":
                    raise RuntimeError("Unresolved first attempt; inspect before resuming " + uid)
        reader.collect(engine, workers)
    _, _, audit = snapshot(engine, cases, frozen)
    reader.save(lock, audit)
    print(f"{engine}: {N} first readings verified and sealed.", flush=True)


def export():
    cases, frozen = reader.load_frozen()
    seals = {engine: reader.read(reader.ROOT / engine / "sealed.json") for engine in reader.ENGINES}
    scores, sessions = [], set()
    for engine in reader.ENGINES:
        rows, observed_sessions, audit = snapshot(engine, cases, frozen)
        if audit != seals[engine] or sessions & observed_sessions:
            raise ValueError("Sealed readings changed, or a session was reused.")
        scores.extend(rows)
        sessions.update(observed_sessions)
    assert len(scores) == len(sessions) == 2 * N
    score_path = HERE / "scores.json"
    reader.save(score_path, scores)
    reader.save(HERE / "reader-verification.json", {
        "n_cases": N, "first_outputs": len(scores), "unique_sessions": len(sessions),
        "blind_sha256": reader.digest(reader.BLIND), "reader_freeze_sha256": reader.digest(reader.FROZEN),
        "scores_sha256": reader.digest(score_path), "reader_results": seals,
        "same_item_payload_each_reader": True, "tools_used": 0, "first_outputs_replaced": 0,
        "model_identity": "Claude assistant service ID; GPT official CLI selection, separate service ID when exposed."
    })
    print(f"Exported {len(scores)} sealed, blinded readings.", flush=True)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("freeze", "opus", "gpt", "export"))
    parser.add_argument("--workers", type=int, choices=range(1, 7), default=5)
    args = parser.parse_args()
    if args.action == "freeze":
        reader.ROOT.mkdir(exist_ok=True)
        if reader.FROZEN.exists():
            reader.load_frozen()
        else:
            reader.save(reader.FROZEN, {"frozen_utc": reader.now(), "spec": manifest(masked_inputs())})
    elif args.action == "export":
        export()
    else:
        collect_and_lock(args.action, args.workers)


if __name__ == "__main__":
    main()
