"""Bounded official subscription CLI calls. No API client, credentials, or retries."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

CODEX_MODEL = "gpt-6.1-sol"
CLAUDE_MODEL = "claude-opus-5-5"
BLOCKED = ["OPENAI_API_KEY", "OPENAI_BASE_URL", "CODEX_API_KEY", "AZURE_OPENAI_API_KEY",
           "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL",
           "ANTHROPIC_PROFILE", "ANTHROPIC_FEDERATION_RULE_ID", "ANTHROPIC_ORGANIZATION_ID",
           "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY"]


def dump(path, value):
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")


def preflight(provider):
    present = [name for name in BLOCKED if os.environ.get(name)]
    if present:
        raise RuntimeError("Alternate billing environment present: " + ", ".join(present))
    executable = shutil.which("codex" if provider == "codex" else "claude")
    if not executable and provider == "claude":
        executable = str(Path.home() / ".local/bin/claude")
    if not executable or not Path(executable).is_file():
        raise RuntimeError("Official CLI not found")
    version = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=30)
    if version.returncode:
        raise RuntimeError("CLI version unavailable")
    auth_cmd = [executable, "login", "status"] if provider == "codex" else [executable, "auth", "status"]
    auth = subprocess.run(auth_cmd, capture_output=True, text=True, timeout=30)
    if provider == "codex":
        valid = auth.returncode == 0 and "Logged in using ChatGPT" in auth.stdout + auth.stderr
        method = "ChatGPT_subscription"
    else:
        try:
            status = json.loads(auth.stdout)
        except json.JSONDecodeError:
            status = {}
        valid = (auth.returncode == 0 and status.get("loggedIn") is True
                 and status.get("authMethod") == "claude.ai"
                 and status.get("subscriptionType") == "pro"
                 and status.get("apiProvider") == "firstParty")
        method = "claude.ai_Pro_firstParty"
    if not valid:
        raise RuntimeError("Existing subscription authentication not verified; no model call")
    return executable, version.stdout.strip(), method


def call_once(provider, body, instructions, directory):
    """One process, no retries. Return exact final text plus recorded selection metadata."""
    if provider not in {"codex", "claude"}:
        raise ValueError("Unknown provider")
    executable, version, method = preflight(provider)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "input.txt").write_text(body, encoding="utf-8")
    (directory / "instructions.txt").write_text(instructions, encoding="utf-8")
    model = CODEX_MODEL if provider == "codex" else CLAUDE_MODEL
    settings = {"reasoning_effort": "high" if provider == "codex" else "medium",
                "temperature": "not_exposed_by_subscription_cli", "tools": "disabled",
                "context": "only_supplied_packet_isolated_cwd_no_session_persistence"}
    metadata = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "provider": provider,
                "requested_model": model, "reported_server_snapshot": None,
                "model_selection_evidence": "explicit_official_CLI_model_argument",
                "cli_version": version, "auth_method": method, "settings": settings,
                "input_sha256": hashlib.sha256(body.encode()).hexdigest(),
                "instructions_sha256": hashlib.sha256(instructions.encode()).hexdigest(),
                "automatic_retries": 0, "status": "started"}
    dump(directory / "started.json", metadata)
    with tempfile.TemporaryDirectory(prefix="speech-subscription-") as temporary:
        if provider == "codex":
            cmd = [executable, "--no-daemon", "exec", "--ignore-user-config", "--ephemeral",
                   "--skip-git-repo-check", "--sandbox", "read-only", "--json", "--color", "never",
                   "--cd", temporary, "--model", model,
                   "-c", 'model_provider="openai"', "-c", 'model_reasoning_effort="high"',
                   "-c", "model_instructions_file=" + json.dumps(str((directory / "instructions.txt").resolve())),
                   "-c", "sqlite_home=" + json.dumps(str(Path(temporary) / "state")),
                   "-c", 'web_search="disabled"', "-c", "features.shell_tool=false",
                   "-c", "features.apps=false", "-c", "features.plugins=false", "-c", "features.memories=false",
                   "-c", "features.hooks=false", "-c", "skills.bundled.enabled=false",
                   "-c", "skills.include_instructions=false", "-c", "mcp_servers={}", "-"]
        else:
            cmd = [executable, "--safe-mode", "-p", "Follow the supplied role. Process only stdin; do not use tools.",
                   "--system-prompt", instructions, "--model", model, "--effort", "medium",
                   "--max-turns", "1", "--tools", "", "--disallowedTools", "mcp__*",
                   "--output-format", "json", "--no-session-persistence"]
        # Record CLI arguments excluding inline role text (already saved separately), no auth values.
        dump(directory / "command.json", {"argv": cmd, "cwd": "isolated_temporary_directory"})
        try:
            result = subprocess.run(cmd, input=body, capture_output=True, text=True, cwd=temporary, timeout=420)
        except subprocess.TimeoutExpired as exc:
            (directory / "stdout.partial").write_bytes(exc.stdout or b"")
            (directory / "stderr.partial").write_bytes(exc.stderr or b"")
            dump(directory / "metadata.json", dict(metadata, status="timeout_no_retry"))
            raise RuntimeError("CLI timed out; no retry") from None
    (directory / "stdout.raw").write_text(result.stdout, encoding="utf-8")
    (directory / "stderr.raw").write_text(result.stderr, encoding="utf-8")
    metadata["returncode"] = result.returncode
    try:
        if result.returncode:
            raise ValueError("CLI failed")
        if provider == "codex":
            events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
            items = [e.get("item", {}) for e in events if e.get("type") == "item.completed"]
            if any(i.get("type") not in {"agent_message", "reasoning"} for i in items):
                raise ValueError("Unexpected tool item; inspect raw evidence")
            answers = [i["text"] for i in items if i.get("type") == "agent_message"]
            if not any(e.get("type") == "turn.completed" for e in events) or len(answers) != 1:
                raise ValueError("Expected exactly one final answer")
            answer = answers[0]
            metadata["usage"] = [e.get("usage") for e in events if e.get("type") == "turn.completed"]
        else:
            response = json.loads(result.stdout)
            if response.get("is_error") or not isinstance(response.get("result"), str):
                raise ValueError("Claude returned error/no result")
            usage = response.get("modelUsage", {})
            if set(usage) != {CLAUDE_MODEL}:
                raise ValueError("Unexpected reported Claude model")
            metadata["reported_model_usage"] = usage
            answer = response["result"]
        if not answer.strip():
            raise ValueError("Empty final answer")
    except (ValueError, KeyError, TypeError) as exc:
        dump(directory / "metadata.json", dict(metadata, status="failed_no_retry", error=str(exc)))
        raise
    (directory / "response.txt").write_text(answer, encoding="utf-8")
    dump(directory / "metadata.json", dict(metadata, status="response_received",
         response_sha256=hashlib.sha256(answer.encode()).hexdigest()))
    return {"text": answer, "model_id": model,
            "model_version": "alias_selected_by_" + version + "; immutable_server_snapshot_not_exposed",
            "settings": settings, "execution_mode": "injected_backend",
            "provenance": str(directory.resolve() / "metadata.json")}
