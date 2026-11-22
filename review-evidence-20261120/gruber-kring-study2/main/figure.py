"""Plot observed elaboration means and the paired length-support check."""
from collections import defaultdict
import json
from pathlib import Path
from statistics import mean

from reportlab.lib.colors import HexColor
from reportlab.pdfgen.canvas import Canvas

HERE = Path(__file__).resolve().parent
TOPICS = ("happy", "compassion", "proud", "sad", "afraid", "embarrassed", "disgusted", "directions", "morning", "meal")
VALENCE = ("Positive", "Negative", "Neutral")
GROUP = dict(zip(TOPICS, ["Positive"] * 3 + ["Negative"] * 4 + ["Neutral"] * 3))
REFERENCE = dict(zip(VALENCE, [2.40, 2.08, 1.87]))
ARMS = ("developed", "base", "short")
SERIES = {"developed": ("Developed", "#08776F"), "base": ("Base", "#365DA4"),
          "short": ("Brief / vague", "#B45521"), "patient": ("Patient reference", "#222D38")}


def read(p):
    return json.loads((HERE / p).read_text())


def plot_values():
    key = read("private/key.json")
    key_by_uid = {r["uid"]: r for r in key}
    scores = read("scores.json")
    assert len(key) == 360 and len(scores) == 720
    values = defaultdict(lambda: defaultdict(list))
    for row in scores:
        if row["status"] != "rated":
            continue
        item = key_by_uid[row["uid"]]
        values[row["reader"], item["arm"], GROUP[item["topic"]]][item["case"]].append(row["elaboration"])
    vectors = {reader: {arm: [mean(mean(points) for points in values[reader, arm, g].values())
                              if values[reader, arm, g] else None for g in VALENCE] for arm in ARMS}
               for reader in ("opus", "gpt")}
    lengths = {(r["case"], r["topic"], r["arm"]): r["words"] for r in key}
    cases = sorted({r["case"] for r in key})
    overlaps = {}
    for arm in ("base", "short"):
        overlaps[arm] = []
        for topic in TOPICS:
            pairs = [(lengths[c, topic, "developed"], lengths[c, topic, arm]) for c in cases]
            overlaps[arm].append(sum(min(a, b) > 0 and 5*min(a, b) >= 4*max(a, b) for a, b in pairs))
    return vectors, overlaps


def main():
    means, overlaps = plot_values()
    c = Canvas(str(HERE / "comparison.pdf"), pagesize=(808, 516))
    c.setTitle("Narrative elaboration and length overlap in the Gruber-Kring task")
    ink = "#203646"
    gray = "#536876"

    def text(x, y, msg, size=10, color=ink, bold=False, align="left"):
        c.setFillColor(HexColor(color))
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        method = {"left": c.drawString, "right": c.drawRightString, "center": c.drawCentredString}[align]
        method(x, y, msg)

    def marker(x, y, label, rad=3.2):
        c.setFillColor(HexColor(SERIES[label][1]))
        if label == "developed":
            c.circle(x, y, rad, fill=1, stroke=0)
        elif label == "base":
            c.rect(x-rad, y-rad, rad*2, rad*2, fill=1, stroke=0)
        else:
            p = c.beginPath()
            p.moveTo(x, y+rad*1.4)
            p.lineTo(x+rad*1.35, y if label == "patient" else y-rad)
            if label == "patient":
                p.lineTo(x, y-rad*1.4)
            p.lineTo(x-rad*1.35, y if label == "patient" else y-rad)
            p.close()
            c.drawPath(p, fill=1, stroke=0)

    text(32, 478, "Narrative elaboration and paired length overlap", 23, bold=True)
    text(32, 456, "Gruber-Kring Study 2 task   /   12 fictional speakers, 10 questions, three generation conditions", 11, gray)
    text(32, 418, "Elaboration by question category", 15, bold=True)
    text(32, 400, "Mean score on a 1-3 scale. Higher values indicate less elaboration.", 10, gray)
    x = 349
    for key, (name, color) in SERIES.items():
        marker(x, 421, key, 3)
        text(x+9, 417, name, 10)
        x += c.stringWidth(name, "Helvetica", 10)+29
    for index, (reader, title) in enumerate((("opus", "Opus"), ("gpt", "GPT"))):
        l = 38 + 388*index
        start, end = l+80, l+336
        text(l, 369, title, 13, bold=True)
        for tick in (1, 1.5, 2, 2.5, 3):
            x = start + (tick-1)*(end-start)/2
            c.setStrokeColor(HexColor("#D8E3E7"))
            c.setLineWidth(0.65)
            c.line(x, 232, x, 350)
            text(x, 217, f"{tick:g}", 9, gray, align="center")
        for i, g in enumerate(VALENCE):
            y = 333 - 43*i
            text(l, y-3, g, 10)
            for label, dy in zip(SERIES, (12, 4, -4, -12)):
                v = REFERENCE[g] if label == "patient" else means[reader][label][i]
                if v is not None:
                    marker(start+(v-1)*(end-start)/2, y+dy, label)
    text(32, 179, "Length-matched pairs by question", 15, bold=True)
    text(32, 161, "Each cell is out of 12. The shorter reply must have at least 80% as many words as the longer one.", 10, gray)
    labels = ("Happy", "Compassion", "Proud", "Sad", "Afraid", "Embarrassed", "Disgusted", "Directions", "Morning", "Last meal")
    start, step = 169, 63
    for j, label in enumerate(labels):
        text(start+step*j, 136, label, 9, align="center")
    for i, (arm, lab) in enumerate((("base", "Developed vs. base"), ("short", "Developed vs. brief"))):
        y = 109-27*i
        text(32, y-3, lab, 10, bold=True)
        for j, n in enumerate(overlaps[arm]):
            mid = start+step*j
            c.setFillColor(HexColor("#D8EBE7" if n >= 6 else "#F1F3F3"))
            c.roundRect(mid-24, y-9, 48, 20, 3, stroke=0, fill=1)
            text(mid, y-3, str(n), 11, bold=True, align="center")
    text(32, 51, "A length-matched ranking requires at least 6 pairs in every question for the corresponding comparison.", 9.5)
    text(32, 31, "Patient reference: Gruber and Kring (2008), Study 2, Table 3. Published human ratings and model ratings use different raters.", 9, gray)
    c.showPage()
    c.save()


if __name__ == "__main__":
    main()
