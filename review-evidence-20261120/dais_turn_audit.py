"""Inspect DAIS-C turn structure locally on macOS. Print aggregate counts only."""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
from statistics import median
import subprocess
import xml.etree.ElementTree as ET
import zipfile


QUESTIONS = {
    "Q1": "how was the experiment",
    "Q2": "do you feel like you do creative things with language",
    "Q3": "do you feel like you use language creatively",
}
WORD = re.compile(r"[a-z]+(?:'[a-z]+)*")
SOURCE_TAG = re.compile(r"<(Gr|WS|TC|DT)(?:\s|>)", re.I)
WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def document_text(path):
    if path.suffix.lower() == ".rtf":
        converted = subprocess.run(
            ["textutil", "-convert", "txt", "-format", "rtf", "-stdin", "-stdout"],
            input=path.read_bytes(), capture_output=True, check=True,
        )
        return converted.stdout.decode("utf-8-sig")
    with zipfile.ZipFile(path) as archive:
        document = ET.fromstring(archive.read("word/document.xml"))
    return "\n".join(
        "".join(node.text or "" for node in p.findall(".//w:t", WORD_NS))
        for p in document.findall(".//w:p", WORD_NS)
    )


def get_exchange(path):
    speaker = path.stem.removesuffix("-FULL").upper()
    roles = re.compile(
        rf"<({re.escape(speaker)}|INT|FAM|DOC)\s*>(.*?)</\1\s*>", re.I | re.S,
    )
    turns = []
    for match in roles.finditer(document_text(path)):
        tagged = match[2]
        clean = re.sub(r"<[^>]+>", " ", tagged).lower().replace("’", "'")
        turns.append((match[1].upper(), WORD.findall(clean), SOURCE_TAG.findall(tagged)))
    for index, (role, words, _) in enumerate(turns[:10]):
        if role != "INT":
            continue
        for question, prompt in QUESTIONS.items():
            if prompt not in " ".join(words):
                continue
            if question == "Q1":
                return question, None
            window = turns[index:index + 8]
            if [role for role, _, _ in window] != ["INT", speaker] * 4:
                raise ValueError("Verify the first four speaker pairs in this release.")
            return question, window
    raise ValueError("Opening prompt not identified.")


def enough(words, length, distinct):
    return len(words) >= length and len(set(words)) >= distinct


def count_by_turn(rows, length, distinct):
    result = {}
    for n in range(1, 5):
        found = Counter()
        for q, window in rows:
            if any(enough(words, length, distinct) for _, words, _ in window[1:2*n:2]):
                found[q] += 1
        result[n] = {q: found[q] for q in ("Q2", "Q3")}
    return result


def audit(corpus):
    folder = corpus / "DAI-C-CL" / "Interactional" / "Full tagged pass"
    files = sorted(p for p in folder.glob("*-FULL.*")
                   if p.suffix.lower() in {".rtf", ".docx"} and not p.name.startswith("~$"))
    if not files:
        raise ValueError("Set the argument to the unpacked DAIS-C-Annotated - Upload folder.")
    groups = [get_exchange(path) for path in files]
    rows = [(q, window) for q, window in groups if q != "Q1"]
    first_lengths = [len(window[1][1]) for _, window in rows]
    flags = Counter()
    overlap = Counter()
    prompts = Counter()
    second_alone = 0
    for q, window in rows:
        first = window[1]
        marked = bool(first[2])
        flags.update({tag.upper() for tag in first[2]})
        overlap[(enough(first[1], 30, 20), marked)] += 1
        second_alone += enough(window[3][1], 30, 20)
        words = window[2][1]
        text = " ".join(words)
        if QUESTIONS[q] in text:
            kind = "opening repeated"
        elif "define" in words and "creative language" in text:
            kind = "definition of creative language"
        elif "why" in words and "more" in words:
            kind = "explain reasoning further"
        else:
            kind = "other"
        prompts[kind] += 1
    return {
        "clinical_files_by_question": dict(Counter(q for q, _ in groups)),
        "first_word_counts_sorted": sorted(first_lengths),
        "first_word_count_median": median(first_lengths),
        "eligibility_by_turn_cumulative": {
            f"{length} words / {unique} distinct": count_by_turn(rows, length, unique)
            for length, unique in [(20, 12), (30, 20), (40, 20)]
        },
        "second_alone_30_words_20_distinct": second_alone,
        "first_turn_original_tag_speakers": {tag: flags[tag] for tag in ("GR", "WS", "TC", "DT")},
        "first_turn_screen_by_any_original_tag": {
            f"screen={screen} / tag={marked}": count
            for (screen, marked), count in sorted(overlap.items())
        },
        "speakers_with_any_original_tag_cumulative": [
            sum(any(tags for _, _, tags in window[1:2*n:2]) for _, window in rows)
            for n in range(1, 5)
        ],
        "first_followup_wording": dict(prompts),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path)
    print(json.dumps(audit(parser.parse_args().corpus), indent=2))
