"""Print the frozen input inventory. Reads local files only, without a model client."""
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import random


STUDY = Path(__file__).resolve().parent.parent
MAIN = STUDY / "main"
SEED = "GK-card-detail-pilot-v1"
TOPICS = {
    "positive": ["happy", "compassion", "proud"],
    "negative": ["sad", "afraid", "embarrassed", "disgusted"],
    "neutral": ["directions", "morning", "meal"],
}
ARMS = ["developed", "base", "short"]


def load(path):
    return json.loads(path.read_bytes())


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def select(profiles):
    rng = random.Random(SEED)
    groups = sorted(set(profiles.values()))
    extra = list(TOPICS)
    rng.shuffle(extra)
    by_valence = defaultdict(list)
    for group, repeated_valence in zip(groups, extra):
        ids = sorted(case for case, profile in profiles.items() if profile == group)
        assert len(ids) == 4
        rng.shuffle(ids)
        for case, valence in zip(ids, [*TOPICS, repeated_valence]):
            by_valence[valence].append(case)
    result = []
    for valence, topics in TOPICS.items():
        four = topics.copy()
        if len(four) == 3:
            four.append(rng.choice(topics))
        rng.shuffle(four)
        result.extend(zip(by_valence[valence], four, [valence] * 4))
    assert len({case for case, _, _ in result}) == 12
    assert len({topic for _, topic, _ in result}) == 10
    assert Counter(v for _, _, v in result) == dict.fromkeys(TOPICS, 4)
    return sorted(result)


def build():
    freeze = load(MAIN / "generation-freeze.json")["sha256"]
    for rel, expected in freeze.items():
        assert digest(STUDY.parent.parent / rel) == expected, rel
    audit = load(STUDY / "cards/audit.json")
    archive = {(r["case"], r["topic"], r["arm"]): r for r in
               load(MAIN / "private/generation-schedule.json")}
    entries = {(r["id"], r["topic"]): r for r in audit["entries"]}
    cards = {c["id"]: c for c in load(STUDY / "cards/cards.json")}
    items = []
    for case, topic, valence in select(audit["profile_cases"]):
        meta = entries[case, topic]
        item = {"case": case, "topic": topic, "valence": valence, "profile": meta["profile"],
                "packets_sha256": {}}
        user_hashes = set()
        for arm in ARMS:
            record = archive[case, topic, arm]
            path = MAIN / "private/messages" / (record["job"] + ".json")
            assert record["packet_sha256"] == digest(path)
            packet = load(path)
            full = [{"role": role, "content": packet[role]} for role in ("system", "user")]
            full_hash = sha256(canonical(full)).hexdigest()
            assert full_hash == meta["messages_sha256"][arm]
            body = json.loads(packet["user"])
            assert canonical(body).decode() == packet["user"]
            facts = body["patient"]["facts"]
            central, *details = cards[case]["items"][topic]
            assert [f["id"] for f in facts] == ["F1", "F2", "F3"]
            assert facts[0]["content"] == central
            assert sorted(f["content"] for f in facts[1:]) == sorted(details)
            assert body["history"] == [] and body["patient"]["case_id"] == case
            assert body["patient"]["self_understanding"] == cards[case]["anchor"]
            body["patient"]["facts"] = facts[:1]
            core_body = canonical(body).decode()
            restored = json.loads(core_body)
            restored["patient"]["facts"].extend(facts[1:])
            assert canonical(restored).decode() == packet["user"]
            core = [full[0], {"role": "user", "content": core_body}]
            core_hash = sha256(canonical(core)).hexdigest()
            assert full_hash != core_hash
            user_hashes.add((sha256(packet["user"].encode()).hexdigest(),
                             sha256(core_body.encode()).hexdigest()))
            item["packets_sha256"][arm] = {"original_job": record["job"], "full": full_hash,
                                           "core": core_hash}
        assert len(user_hashes) == 1
        items.append(item)
    source_files = ["DESIGN.ko.md", "cards/cards.json", "cards/audit.json",
                    "boundary/calibrate.py", "main/generation-freeze.json", "main/read_blind.py",
                    "main/scores.json", "main/analysis.json", "main/release-check.json"]
    source_hashes = {p: digest(STUDY / p) for p in source_files}
    assert source_hashes["main/analysis.json"] == load(MAIN / "release-check.json")["analysis_sha256"]
    return {"selection_seed": SEED, "planned_pairs": len(items) * len(ARMS),
            "planned_utterances": len(items) * len(ARMS) * 2,
            "planned_ratings": len(items) * len(ARMS) * 2 * 2, "items": items,
            "source_sha256": source_hashes}


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, ensure_ascii=False))
