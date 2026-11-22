"""One bounded review through the unmodified official Claude Code CLI.

Default: prepare a small review packet and show local readiness, with no model call.
--run: require verified subscription authentication, then request one review.
No API keys, background polling, SDK dependency, file-edit tools, or auto-retry.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
MODEL = "claude-opus-5-5"
BLOCKED_ENV = ["ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL",
               "ANTHROPIC_PROFILE", "ANTHROPIC_FEDERATION_RULE_ID", "ANTHROPIC_ORGANIZATION_ID",
               "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY"]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--request", type=Path, default=HERE / "review_request.md")
    ap.add_argument("--milestone", default="M0-design")
    ap.add_argument("--round", type=int, choices=[1, 2], default=1)
    ap.add_argument("--run", action="store_true", help="consume one review under verified Claude subscription login")
    args = ap.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,50}", args.milestone):
        raise SystemExit("Use a short alphanumeric milestone ID.")
    request = args.request.resolve()
    if not request.is_relative_to(HERE):
        raise SystemExit("Keep the explicitly selected request inside collaboration/.")
    body = request.read_text()
    prompt = (HERE / "reviewer_prompt.txt").read_text()
    packet = prompt + "\n\n--- 이번 검토 자료 ---\n\n" + body
    encoded = packet.encode("utf-8")
    if len(encoded) > 24000:
        raise SystemExit("Review packet exceeds 24 KB. Narrow the request; do not silently truncate evidence.")
    exe = shutil.which("claude")
    if not exe:
        native = Path.home() / ".local" / "bin" / "claude"
        if native.is_file():
            exe = str(native)
    summary = {"requested_model": MODEL, "packet_bytes": len(encoded),
               "input_sha256": hashlib.sha256(encoded).hexdigest(),
               "claude_on_path": bool(exe), "model_called": False}
    if not args.run:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print("Dry run only; no model call made. Use --run only after verifying the recorded subscription connection.")
        return
    if not exe:
        raise SystemExit("Claude Code executable not found. No model call made.")
    present = [name for name in BLOCKED_ENV if os.environ.get(name)]
    if present:
        raise SystemExit("Alternate billing/provider environment detected; no model call made. Variable names: " + ", ".join(present))
    version = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=20)
    if version.returncode:
        raise SystemExit("Cannot check CLI version. No model call made.")
    auth = subprocess.run([exe, "auth", "status"], capture_output=True, text=True, timeout=30)
    try:
        status = json.loads(auth.stdout)
    except json.JSONDecodeError:
        raise SystemExit("Cannot verify CLI subscription authentication; no model call made.")
    if auth.returncode or status.get("authMethod") not in {"claude.ai", "oauth_token"}:
        raise SystemExit("Claude subscription login not verified. Use the official login flow and check /status. No model call made.")
    help_check = subprocess.run([exe, "--help"], capture_output=True, text=True, timeout=20)
    if help_check.returncode or "--safe-mode" not in help_check.stdout:
        raise SystemExit("This CLI does not expose the documented safe-mode flag; update/check it before using this wrapper.")
    out = HERE / "reviews" / f"{args.milestone}-round{args.round}"
    out.mkdir(parents=True, exist_ok=False)
    (out / "input.txt").write_text(packet)
    cmd = [exe, "--safe-mode", "-p", "Review only the supplied packet from stdin. Follow its reviewer role and output requirements.",
           "--model", MODEL, "--effort", "medium", "--max-turns", "1", "--tools", "",
           "--disallowedTools", "mcp__*", "--output-format", "json", "--no-session-persistence"]
    metadata = dict(summary, timestamp_utc=datetime.now(timezone.utc).isoformat(),
                    cli_version=version.stdout.strip(), auth_method=status.get("authMethod"),
                    model_called=True, status="started_not_completed")
    (out / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
    try:
        result = subprocess.run(cmd, input=packet, text=True, capture_output=True, cwd=HERE, timeout=600)
    except subprocess.TimeoutExpired:
        metadata["status"] = "timed_out_no_retry"
        (out / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
        raise SystemExit("Review timed out. No automatic retry; inspect CLI usage/status before requesting another review.")
    (out / "raw_response.json").write_text(result.stdout)
    (out / "stderr.txt").write_text(result.stderr)
    metadata["status"] = "cli_returned" if result.returncode == 0 else "cli_failed_no_retry"
    metadata["returncode"] = result.returncode
    try:
        response = json.loads(result.stdout)
        if response.get("is_error"):
            metadata["status"] = "model_reported_error_no_retry"
        elif result.returncode == 0 and isinstance(response.get("result"), str):
            (out / "feedback.md").write_text(response["result"])
            metadata["status"] = "review_received"
        metadata["reported_model_usage"] = response.get("modelUsage")
    except json.JSONDecodeError:
        metadata["status"] = "unparsed_response_preserved_no_retry"
    (out / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
    print(json.dumps({"status": metadata["status"], "output_directory": str(out)}, ensure_ascii=False))
    if metadata["status"] != "review_received":
        sys.exit(1)


if __name__ == "__main__":
    main()
