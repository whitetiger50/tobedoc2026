"""Run a methods consultation in a fresh tools-disabled Claude Pro session."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("transport", HERE.parents[1]/"boundary-calibration-20261121/opus/run.py")
opus = importlib.util.module_from_spec(spec)
spec.loader.exec_module(opus)
name = sys.argv[1]
source = HERE / (name + ".txt")
outfile = HERE / (name + "-receipt.json")
if outfile.exists():
    raise SystemExit("Consultation already recorded")
cli, env, account, version = opus.runtime()
flags = opus.FLAGS.copy()
flags[flags.index("--system-prompt")+1] = "You are an independent research methods reviewer. Respond concisely in English. Do not use tools."
with tempfile.TemporaryDirectory() as cwd:
    response = subprocess.run([cli, *flags, "--effort", "medium"], input=source.read_text(), cwd=cwd, env=env,
                              capture_output=True, text=True, timeout=240)
events = [json.loads(l) for l in response.stdout.splitlines() if l.startswith("{")]
last = next((e for e in reversed(events) if e.get("type")=="result"),{})
init = next((e for e in events if e.get("subtype")=="init"),{})
rate = [e["rate_limit_info"] for e in events if e.get("type")=="rate_limit_event"]
models = {e["message"].get("model") for e in events if e.get("type")=="assistant"}
if response.returncode or last.get("is_error") or not last.get("result") or models!={opus.MODEL} or init.get("tools") or any(r.get("isUsingOverage") for r in rate):
    raise SystemExit("Review transport invalid: "+str((response.returncode,models,last.get("subtype"),response.stderr[-150:])))
outfile.write_text(json.dumps(dict(model=opus.MODEL,version=version,account=account,session=init["session_id"],
                                  tools=init.get("tools"),usage=last.get("usage"),rate=rate,result=last["result"]),indent=2)+"\n")
print(last["result"])
