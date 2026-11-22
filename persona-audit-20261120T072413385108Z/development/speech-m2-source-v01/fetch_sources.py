"""Cache a small, explicit set of primary sources. No model/API/package execution."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
URLS = {
    "psyche-v1.html": "https://arxiv.org/html/2501.01594v1",
    "psyche-v1.pdf": "https://arxiv.org/pdf/2501.01594v1",
    "roleplay-doh.pdf": "https://aclanthology.org/2024.emnlp-main.591.pdf",
    "psychiatric-voice.html": "https://link.springer.com/article/10.1007/s40596-026-02422-9",
    "psychiatric-voice-table1.html": "https://link.springer.com/article/10.1007/s40596-026-02422-9/tables/1",
    "jmir-schizophrenia.html": "https://mededu.jmir.org/2026/1/e78161/",
    "nimh-schizophrenia.html": "https://www.nimh.nih.gov/health/publications/schizophrenia",
}


class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []; self.skip = 0; self.links = []
    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}: self.skip += 1
        if tag in {"p", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "section", "br"}: self.parts.append("\n")
        if tag == "a":
            a = dict(attrs)
            if a.get("href"): self.links.append(a["href"])
    def handle_endtag(self, tag):
        if tag in {"script", "style"}: self.skip -= 1
        if tag in {"p", "div", "tr", "li", "td", "th", "section"}: self.parts.append("\n")
    def handle_data(self, data):
        if not self.skip: self.parts.append(data)


def get(item):
    name, url = item
    path = HERE / "sources" / name
    if path.exists():
        raise FileExistsError("Preserve original download; do not overwrite")
    try:
        with urlopen(Request(url, headers={"User-Agent": "Research source verification"}), timeout=45) as response:
            raw = response.read(); final = response.url; content_type = response.headers.get("Content-Type")
        path.write_bytes(raw)
        record = {"id": name, "url": url, "final_url": final, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                  "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "content_type": content_type, "status": "ok"}
        if name.endswith(".html"):
            parser = Text(); parser.feed(raw.decode("utf-8"))
            lines = [" ".join(line.split()) for line in "".join(parser.parts).splitlines() if line.strip()]
            (HERE / "text" / (name + ".txt")).write_text("\n".join(lines) + "\n")
            (HERE / "text" / (name + ".links.json")).write_text(json.dumps(parser.links, indent=2))
        elif name.endswith(".pdf"):
            subprocess.run(["pdftotext", "-layout", str(path), str(HERE / "text" / (name + ".txt"))], check=True, capture_output=True)
        print(name + ": saved", flush=True)
        return record
    except Exception as exc:
        print(name + ": " + type(exc).__name__, flush=True)
        return {"id": name, "url": url, "status": "unavailable", "error_type": type(exc).__name__}


def main():
    (HERE / "sources").mkdir(parents=True, exist_ok=True)
    (HERE / "text").mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(get, URLS.items()))
    prior = json.loads((ROOT / "evidence/source-lock.json").read_text())
    for row in prior["sources"]:
        if row["id"] in {"psi_formatter", "psi_styles", "psi_runtime", "psi_paper"}:
            path = ROOT / row["local_text"]
            raw = path.read_bytes()
            assert hashlib.sha256(raw).hexdigest() == row["text_sha256"]
            records.append({"id": row["id"], "url": row["citation_url"], "path": row["local_text"],
                            "sha256": hashlib.sha256(raw).hexdigest(), "status": "verified_existing_snapshot"})
    with (HERE / "source-lock.json").open("x") as f:
        json.dump({"retrieval_date": "2026-11-18", "sources": records, "paid_api_calls": 0}, f, ensure_ascii=False, indent=2)


if __name__ == "__main__": main()
