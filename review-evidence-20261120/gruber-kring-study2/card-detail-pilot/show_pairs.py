"""Write the 36 source comparisons only after both blind readings have been sealed."""
from pathlib import Path

import analyze_pilot as stats

HERE = Path(__file__).resolve().parent
ARM_KO = stats.LABEL


def main():
    _, _, blind, _, hashes = stats.load_locked_inputs(HERE)
    analysis = stats.load(HERE / "analysis.json")
    assert analysis["sources_sha256"] == hashes
    by_uid = {r["uid"]: r for r in blind}
    cards = {r["id"]: r for r in stats.load(HERE.parent / "cards/cards.json")}
    lines = ["# 36쌍의 영어 원문과 두 판독자의 최초 근거", "",
             "각 문항에서 두 조건이 공유한 중심 사실·인물 배경과 원래 카드에만 제공한 세부를 함께 표시했다. "
             "답변은 최초 생성물이고, 사건별 두 숫자는 구체적 전개와 의미 명료도 순서다.", ""]
    for pair in analysis["pairs"]:
        case, topic, arm = [pair[k] for k in ("case","topic","arm")]
        card = cards[case]
        core, *details = card["items"][topic]
        if arm == "base":  # Alphabetically first in the stored pairs.
            lines.extend([f"## {case} · {topic}", "", by_uid[pair["core"]["uid"]]["question"], "",
                          f"- 중심 사실 · {core}", f"- 인물 배경 · {card['anchor']}",
                          f"- 삭제한 세부 · {' / '.join(details)}", ""])
        lines += [f"### {ARM_KO[arm]}", ""]
        for version, label in (("full","원래 카드"),("core","중심 사실 카드")):
            item = pair[version]
            lines += [f"**{label} · {item['words']}단어**", ""]
            lines += ["> " + line for line in by_uid[item["uid"]]["answer"].strip().splitlines()]
            lines.append("")
            for reader in ("opus","gpt"):
                row = item["scores"][reader]
                if not row["events"]:
                    lines.append(f"- {reader.upper()} · {row['status']}")
                for i,evt in enumerate(row["events"], 1):
                    lines += [f"- {reader.upper()} · 사건 {i} · 전개 {evt['elaboration']}, "
                              f"명료도 {evt['meaning_clarity']} · {evt['elaboration_reason']} "
                              f"{evt['meaning_clarity_reason']}"]
            lines.append("")
    stats.store(HERE / "pairs.md", ("\n".join(lines)+"\n").encode())


if __name__ == "__main__":
    main()
