"""python3 -m speech_module: offline prepare or explicit manual import only."""
import argparse
import json
from pathlib import Path

from .core import TEMPLATES, VERSION, import_response, prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("prepare", help="assemble input and prompt; no model call")
    build.add_argument("--input", type=Path, required=True)
    build.add_argument("--out", type=Path, required=True)
    build.add_argument("--partition", default="development", choices=["development", "reliability_pilot", "heldout_confirmation"])
    build.add_argument("--require-fact", action="append", default=[], help="author-annotated dependency of this question; repeatable")
    build.add_argument("--module-version", choices=list(TEMPLATES), default=VERSION)
    build.add_argument("--question-reviewed", action="store_true", help="author attests question/facts were checked; required before live v0.3+ use/import")
    build.add_argument("--experimental-examples", action="store_true", help="explicitly enable optional author-checked synthetic examples")
    build.add_argument("--style-reference-examples", type=Path, help="v0.6 only: JSON list of separate miniature reference examples")
    ingest = commands.add_parser("import", help="record actual response JSON from an authorized subscription session")
    ingest.add_argument("--run-dir", type=Path, required=True)
    ingest.add_argument("--response", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        packet = prepare(json.loads(args.input.read_text(encoding="utf-8")), args.out, expected_partition=args.partition,
                         required_fact_ids=tuple(args.require_fact), module_version=args.module_version,
                         question_reviewed=args.question_reviewed, allow_experimental_examples=args.experimental_examples,
                         style_reference_examples=json.loads(args.style_reference_examples.read_text()) if args.style_reference_examples else None)
        result = {"status": "prepared_only_no_inference", "messages_sha256": packet["messages_sha256"]}
    else:
        result = import_response(args.run_dir, json.loads(args.response.read_text(encoding="utf-8")))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
