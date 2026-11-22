"""Allow successful official WebSocket reconnects that need no HTTPS fallback.

Preserves all input, original transport traces, session hashes and first answers.
"""
import fcntl
import json
import os
import re
import runner

original=runner.gen.fallback_notices
retry=re.compile(r"Reconnecting\.\.\. ([2-5])/5 \(unexpected status 403 Forbidden: Unknown error, url: wss://chatgpt\.com/backend-api/codex/responses, cf-ray: [0-9a-f]{16}-[A-Z]{3}\)")
def validate(events, turn_start):
    indices=[i for i,e in enumerate(events) if e.get("type")=="error"]
    if not indices or any(i>turn_start and e.get("item",{}).get("type")=="error" for i,e in enumerate(events)):
        return original(events,turn_start)
    seq=[retry.fullmatch(events[i].get("message","")) for i in indices]
    if not all(seq) or [int(v[1]) for v in seq]!=list(range(2,2+len(seq))):
        return original(events,turn_start)
    first_item=next((i for i,e in enumerate(events) if i>turn_start and e.get("type") in ("item.completed","item.started")),None)
    if not (first_item and turn_start<min(indices)<=max(indices)<first_item):
        return original(events,turn_start)
    original([e for i,e in enumerate(events) if i not in indices],turn_start)
    return [],len(indices)

if __name__=="__main__":
    os.umask(0o077)
    runner.gen.fallback_notices=validate
    with (runner.PRIVATE/"generate.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        runner.generate()
