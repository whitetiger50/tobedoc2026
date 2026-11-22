"""Resume the authorized included-subscription work after the reported short window expires."""
from datetime import datetime,timezone
import os
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent.parent
reset=1795215600
def run(*args):
    print(datetime.now(timezone.utc).isoformat(), "starting",args,flush=True)
    subprocess.run([sys.executable,*args],cwd=HERE,check=True)
if __name__=="__main__":
    os.environ["PATH"]=str(Path.home()/".local/bin")+os.pathsep+os.environ["PATH"]
    while time.time()<reset+4:
        time.sleep(min(45,reset+4-time.time()))
    run("finish_reading.py")
    run("reconstruction/test.py","run","opus")
