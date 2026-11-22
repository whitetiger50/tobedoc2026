"""Separate high-effort Claude mentoring context; never an utterance-rating session."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import uuid

from collaboration.subscription_call import CLAUDE_MODEL,preflight,dump


def call_mentor(body,role,directory):
    executable,version,method=preflight('claude')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    (directory/'input.txt').write_text(body)
    (directory/'instructions.txt').write_text(role)
    session_id=str(uuid.uuid4())
    metadata={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'purpose':'development_direction_mentor_not_utterance_judge',
        'requested_model':CLAUDE_MODEL,'cli_version':version,'auth_method':method,'effort':'high',
        'transport_session_id':session_id,'conversation_policy':'fresh mentor transport; explicit bounded prior mentor exchange in followup packet; no rater session resume',
        'tools':'disabled','reported_server_snapshot':None,'temperature':'not_exposed',
        'input_sha256':hashlib.sha256(body.encode()).hexdigest(),'instructions_sha256':hashlib.sha256(role.encode()).hexdigest(),
        'automatic_retries':0,'status':'started'}
    dump(directory/'started.json',metadata)
    cmd=[executable,'--safe-mode','-p','Follow the supplied strategy-mentor role. Process stdin only; do not use tools.',
         '--system-prompt',role,'--model',CLAUDE_MODEL,'--effort','high','--session-id',session_id,
         '--max-turns','1','--tools','','--disallowedTools','mcp__*','--output-format','json','--no-session-persistence']
    dump(directory/'command.json',{'argv':cmd,'cwd':'new_isolated_temporary_directory'})
    with tempfile.TemporaryDirectory(prefix='speech-strategy-mentor-') as cwd:
        try:r=subprocess.run(cmd,input=body,text=True,capture_output=True,cwd=cwd,timeout=420)
        except subprocess.TimeoutExpired as exc:
            (directory/'stdout.partial').write_bytes(exc.stdout or b'');(directory/'stderr.partial').write_bytes(exc.stderr or b'')
            dump(directory/'metadata.json',dict(metadata,status='timeout_no_retry'));raise RuntimeError('Mentor timeout; no retry') from None
    (directory/'stdout.raw').write_text(r.stdout);(directory/'stderr.raw').write_text(r.stderr)
    try:
        if r.returncode:raise ValueError('Mentor CLI failed')
        response=json.loads(r.stdout)
        if response.get('is_error') or not isinstance(response.get('result'),str) or not response['result'].strip():raise ValueError('No actual mentor response')
        if set(response.get('modelUsage',{}))!={CLAUDE_MODEL}:raise ValueError('Unexpected reported mentor model')
    except (ValueError,TypeError) as exc:
        dump(directory/'metadata.json',dict(metadata,status='failed_no_retry',returncode=r.returncode,error=str(exc)));raise
    answer=response['result'];(directory/'response.txt').write_text(answer)
    dump(directory/'metadata.json',dict(metadata,status='response_received',returncode=r.returncode,
        reported_model_usage=response['modelUsage'],response_sha256=hashlib.sha256(answer.encode()).hexdigest()))
    return answer
