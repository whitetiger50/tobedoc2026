"""Prepare six nonclinical practice items, a key and blank forms. No model calls."""
import argparse
import csv
import random
import unicodedata
from pathlib import Path


# Editorial fixtures; no participant data or simulated patient utterances.
FIXTURES = [
    ("직원은 접수 번호를 종이에 적고 영수증을 챙겼다.", "", "자연스러운 서술"),
    ("가게는 오늘 쉬었다. 이야기를 바꾸자면 동생은 수영을 좋아한다.", "", "명시적 화제 전환"),
    ("따뜻한 차를 마시니 마음이 풀렸다.", "", "통상적으로 허용되는 비유"),
    ("역무원은 도착 시각을 달력에 튀겼다.", "튀겼다", "시각을 달력에 기록하는 문맥과 서술어가 맞지 않음"),
    ("사서가 반납 도장을 다리미로 읽었다.", "다리미로", "문자 판독에 쓰는 도구로 해석하기 어려움"),
    ("작업자는 자로 선반의 가로 길이를 빗질했다.", "빗질했다", "길이 측정 대상과 행위가 맞지 않음"),
]
ITEM_FIELDS = ("blind_id", "text", "characters", "status", "definite_count",
               "uncertain_count", "topic_shift", "background_explanation",
               "added_psychosis_content", "clear_grammar_count", "suspected_arm_leak")
SPAN_FIELDS = ("blind_id", "start", "end", "quote", "certainty", "reason")


def scoring_text(raw):
    # Use this exact string for both denominators and zero-based [start, end) offsets.
    return unicodedata.normalize("NFC", raw).strip().replace("\r", "").replace("\n", "")


def write_csv(path, fields, rows):
    with path.open("x", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def prepare(folder):
    folder.mkdir(exist_ok=False)
    items, key = [], []
    shuffled = list(FIXTURES)
    random.Random(20261123).shuffle(shuffled)
    for number, (raw, target, reason) in enumerate(shuffled, 1):
        text = scoring_text(raw)
        item_id = f"K{number:02}"
        items.append(dict(blind_id=item_id, text=text, characters=len(text)))
        start = text.index(target) if target else None
        end = start + len(target) if target else None
        key.append(dict(blind_id=item_id, target=target, start=start, end=end, reason=reason))
    write_csv(folder / "practice-blind.csv", ITEM_FIELDS, items)
    write_csv(folder / "operator-key.csv", tuple(key[0]), key)
    write_csv(folder / "blank-spans.csv", SPAN_FIELDS, [])
    write_csv(folder / "blank-items.csv", ITEM_FIELDS, [])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("new_directory", type=Path)
    prepare(parser.parse_args().new_directory)
