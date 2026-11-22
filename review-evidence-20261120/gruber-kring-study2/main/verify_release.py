"""Cross-check the released summaries against original generation receipts and first scores."""
from collections import Counter, defaultdict
from hashlib import sha256
import json
from math import isclose
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
GROUPS = (("happy", "compassion", "proud"), ("sad", "afraid", "embarrassed", "disgusted"),
          ("directions", "morning", "meal"))


def load(name):
    return json.loads((HERE / name).read_text())


def digest(name):
    return sha256((HERE / name).read_bytes()).hexdigest()


def main():
    scores = load("scores.json")
    key = {r["uid"]: r for r in load("private/key.json")}
    masked = {r["uid"]: r for r in load("blind.json")}
    stats = load("analysis.json")
    gen = load("generation-verification.json")
    read = load("reader-verification.json")
    assert gen["blind_sha256"] == read["blind_sha256"] == digest("blind.json")
    assert read["scores_sha256"] == digest("scores.json")
    assert set(key) == set(masked) and len(key) == 360
    sessions = set()
    for job in load("private/generation-schedule.json"):
        uid = job["uid"]
        receipt = load("private/generated/" + job["job"] + ".json")
        assert receipt["session"] not in sessions
        sessions.add(receipt["session"])
        assert receipt["raw"] == masked[uid]["answer"]
        assert set(masked[uid]) == {"uid","question","answer"}
        assert all(key[uid][k] == job[k] for k in ("case","arm","topic"))
        for engine, field, folder in (("opus","session_id","receipts"),("gpt","cli_session_id","meta")):
            root = Path("readers") / engine / uid
            attempt = load(root / "accepted.json")["attempt"]
            meta = load(root / attempt / folder / (uid + ".json"))
            session = meta[field]
            assert session and session not in sessions
            sessions.add(session)
    assert len(sessions) == 1080
    forms = {(r["reader"], r["uid"]): r for r in scores}
    assert len(forms) == len(scores) == 720
    for reader in ("opus", "gpt"):
        for arm in ("developed", "base", "short"):
            eligible = [r for uid, r in key.items() if r["arm"] == arm and forms[reader,uid]["status"] == "rated"]
            for scale in ("elaboration","meaning_clarity"):
                reference = stats["reference"]["patient"][scale]
                means = []
                for topics in GROUPS:
                    by_case = defaultdict(list)
                    for row in eligible:
                        if row["topic"] in topics:
                            events = forms[reader,row["uid"]]["events"]
                            by_case[row["case"]].append(mean(e[scale] for e in events))
                    means.append(mean(map(mean, by_case.values())))
                item = stats["full"][reader][scale][arm]
                assert all(isclose(a,b, abs_tol=1e-10) for a,b in zip(means,item["means"]))
                errors = [v-target for v,target in zip(means, reference)]
                assert isclose(mean(map(abs,errors)), item["patient"]["D"], abs_tol=1e-10)
                assert isclose(mean(abs(e-mean(errors)) for e in errors), item["patient"]["S"], abs_tol=1e-10)
    sizes = {(r["case"], r["topic"], r["arm"]): r["words"] for r in key.values()}
    for arm in ("base","short"):
        coverage = Counter()
        for (case,topic,source), count in sizes.items():
            if source == "developed" and count > 0:
                other = sizes[case,topic,arm]
                coverage[topic] += int(min(count,other) / max(count,other) >= .80)
        assert dict(coverage) == stats["length_pairs"][arm]["counts"]
    result = {"distinct_sessions_generation_and_readers":len(sessions), "raw_answers_equal_blind_corpus":360,
              "rating_rows":720, "independently_recomputed_patient_distances":24,
              "independently_recomputed_length_counts":20, "analysis_sha256":digest("analysis.json")}
    (HERE / "release-check.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
