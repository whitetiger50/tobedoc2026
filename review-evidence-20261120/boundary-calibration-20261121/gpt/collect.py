"""Run only the twelve authored nonclinical reader packets, in fresh CLI contexts."""
import argparse
import concurrent.futures
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time


OUTPUT = Path(__file__).resolve().parent
READER_FILE = OUTPUT.parents[2] / "tobedoc2026/docs/2026-11-20-english-clinical-profile/reader.py"
MODEL = "gpt-6.1-sol"
DISABLED = (
    "apps", "plugins", "memories", "shell_tool", "unified_exec", "multi_agent",
    "multi_agent_v2", "browser_use", "browser_use_external", "computer_use",
    "view_image", "image_generation", "hooks", "goals", "skill_search",
    "tool_suggest", "workspace_dependencies", "shell_snapshot", "in_app_browser",
)
TRANSPORT = "Return the completed form as a single JSON object. Use no tools."


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def load_reader():
    spec = importlib.util.spec_from_file_location("authored_nonclinical_reader", READER_FILE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def rate(mod, sample_id):
    packet = mod.packet(mod.EXAMPLES[sample_id][0])
    case_file = OUTPUT / "forms" / f"{sample_id}.json"
    raw_file = OUTPUT / "raw" / f"{sample_id}.txt"
    if case_file.exists() or raw_file.exists():
        raise FileExistsError("A response has already been recorded for " + sample_id)
    body = json.dumps(packet, ensure_ascii=False, indent=2) + "\n"
    (OUTPUT / "packets" / f"{sample_id}.json").write_text(body, encoding="utf-8")
    with tempfile.TemporaryDirectory(dir="/private/tmp", prefix="reader-") as scratch:
        private = Path(scratch)
        workdir = private / "work"
        workdir.mkdir()
        isolated = private / "config"
        isolated.mkdir(mode=0o700)
        # Only the official CLI follows this private link to its existing ChatGPT login.
        # No credential is copied into a packet, log, or project file.
        (isolated / "auth.json").symlink_to(Path.home() / ".codex/auth.json")
        shutil.copyfile(Path.home() / ".codex/models_cache.json", isolated / "models_cache.json")
        environment = {
            k: os.environ[k] for k in ("PATH", "HOME", "USER", "LOGNAME", "TMPDIR", "LANG")
            if k in os.environ
        }
        environment["CODEX_HOME"] = str(isolated)
        # Capture only model identity from SDK response metadata, never raw transport traces.
        environment["RUST_LOG"] = "warn,codex_api::endpoint::responses_websocket=trace,codex_api::sse::responses=trace"
        base = private / "instructions.txt"
        base.write_text(TRANSPORT, encoding="utf-8")
        reply = private / "response.txt"
        cmd = [
            "codex", "--no-daemon", "-a", "never", "exec", "--ignore-user-config", "--ignore-rules",
            "--ephemeral", "--sandbox", "read-only", "--skip-git-repo-check", "--color", "never",
            "--model", MODEL, "--cd", str(workdir), "--output-last-message", str(reply),
            "--enable", "skip_host_skill_discovery", "--enable", "omit_skill_descriptions",
            "-c", 'web_search="disabled"', "-c", "mcp_servers={}", "-c", "project_doc_max_bytes=0",
            "-c", 'forced_login_method="chatgpt"', "-c", 'model_reasoning_effort="medium"',
            "-c", "model_instructions_file=" + json.dumps(str(base)),
        ]
        for feature in DISABLED:
            cmd.extend(["--disable", feature])
        started = now()
        tic = time.monotonic()
        call = subprocess.run(cmd + ["-"], cwd=workdir, env=environment, input=body,
                              capture_output=True, text=True, timeout=145)
        elapsed = round(time.monotonic() - tic, 2)
        log = call.stderr
        # The default CLI session header contains the model selected by this invocation.
        def header(field):
            match = re.search(r"^" + re.escape(field) + r":\s*(.*?)\s*$", log, re.MULTILINE)
            return match.group(1) if match else None

        service = set()
        for line in log.splitlines():
            if re.search(r'response\.(created|completed)', line):
                service.update(re.findall(r'"model"\s*:\s*"([^"]+)"', line))
        tools = [line for line in log.splitlines() if re.match(r"^(?:exec|tool [^ ]+|web search)$", line)]
        metadata = {
            "case": sample_id, "started_utc": started, "finished_utc": now(), "wall_seconds": elapsed,
            "exit_code": call.returncode, "requested_model": MODEL, "cli_model": header("model"),
            "service_response_models": sorted(service), "provider": header("provider"),
            "reasoning_effort": header("reasoning effort"), "cli_session_id": header("session id"),
            "sandbox": header("sandbox"), "token_count_cli": None, "tool_events_cli": tools,
            "packet_sha256": hashlib.sha256(body.encode()).hexdigest(), "process_id_isolation": "fresh process, empty cwd, private ephemeral CLI home",
        }
        token_match = re.search(r"^tokens used\s*\n([\d,]+)", log, re.MULTILINE)
        if token_match:
            metadata["token_count_cli"] = int(token_match.group(1).replace(",", ""))
        content = reply.read_bytes() if reply.exists() else b""
        if not content.strip():
            # Retain concise failure reasons, excluding all HTTP/SDK trace lines.
            metadata["errors"] = [line[:480] for line in log.splitlines()
                                  if len(line) < 900 and re.match(r"^(?:ERROR:|Error:|Reconnecting\.\.\.|Warning:)", line)]
            write_json(OUTPUT / "meta" / (sample_id + ".transport-failure-" + str(time.time_ns()) + ".json"), metadata)
            raise RuntimeError(f"{sample_id}: no answer (code {call.returncode}), " + repr(metadata["errors"][-3:]))
        raw_file.write_bytes(content)
        metadata["raw_sha256"] = hashlib.sha256(content).hexdigest()
        # Only a Markdown fence, if present, is removed. No change to any form field.
        original = content.decode()
        fenced = re.fullmatch(r"\s*```(?:json)?\s*\n(.*?)\n```\s*", original, re.DOTALL)
        form_text = fenced.group(1) if fenced else original
        metadata["markdown_fence_removed"] = bool(fenced)
        case_file.write_text(form_text, encoding="utf-8")
        write_json(OUTPUT / "meta" / (sample_id + ".json"), metadata)
        print(sample_id, "response received", metadata["cli_model"], metadata["service_response_models"], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", nargs="+")
    args = parser.parse_args()
    mod = load_reader()
    unknown = set(args.cases) - set(mod.EXAMPLES)
    if unknown or len(args.cases) != len(set(args.cases)):
        parser.error("Choose distinct authored case IDs")
    for directory in ("packets", "forms", "raw", "meta"):
        (OUTPUT / directory).mkdir(exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        pending = [pool.submit(rate, mod, sample_id) for sample_id in args.cases]
        for future in concurrent.futures.as_completed(pending):
            future.result()


if __name__ == "__main__":
    main()
