"""Submit the final already-scheduled Opus forms one at a time while included use is available."""
import fcntl
from pathlib import Path
import time
import random
import semantic as s

def run():
    study=s.study
    study.verify_design();study.check_blind();s.freeze()
    s.assess.SYSTEM=s.SYSTEM
    cases=study.inputs()
    opportunities={r["id"]:cases[r["case"]]["opportunities"] for r in study.key()}
    order=sorted(opportunities)
    random.Random("semantic-independent-read-v1-opus").shuffle(order)
    pending=[u for u in order if not (s.OUT/"opus"/u/"accepted.json").exists()]
    if len(pending)>3:
        raise RuntimeError("Serial tail is limited to the last three prescheduled forms")
    for uid in pending:
        study.quota_check("semantic-opus-serial",len(pending))
        s.assess.verify_overage_lock()
        paths=sorted((s.OUT/"opus").rglob("provider.json"),key=lambda p:p.stat().st_mtime_ns)
        latest=s.read(paths[-1])["rate_events"][-1]
        if not s.assess.org_blocks_overage(latest):raise RuntimeError("No organization overage lock")
        for name,max_used in (("seven_day",.66),("five_hour",.99)):
            window=latest["unifiedWindows"][name]
            if window["resetsAt"]>time.time() and (window["status"] not in ("allowed","allowed_warning") or window["utilization"]>=max_used):
                raise RuntimeError("Wait for subscription window reset: "+str(window["resetsAt"]))
        s.collect("opus",uid,opportunities[uid])
        print("First form verified",flush=True)
if __name__=="__main__":
    with (s.study.PRIVATE/"judge-opus.lock").open("a") as guard:
        fcntl.flock(guard,fcntl.LOCK_EX)
        run()
