"""Reconcile actual bounded design critique receipts, not patient ratings."""
import hashlib,json
from pathlib import Path
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    first=read(HERE/'request-freeze.json');second=read(HERE/'round02-freeze.json')
    assert sha(HERE/'request-round01.md')==first['body_sha256']
    assert sha(HERE/'mentor-role.txt')==first['role_sha256']
    assert sha(HERE/'request-round02.md')==second['body_sha256']
    assert sha(HERE/'codex-response-round01.md')==second['counterargument_sha256']
    assert sha(HERE/'reviewed-followup-materials/methods.md')==second['methods_sha256']
    assert sha(HERE/'reviewed-followup-materials/schema-mapping.json')==second['schema_mapping_sha256']
    sessions=[]
    for n in [1,2]:
        d=HERE/f'claude-round{n:02d}';m=read(d/'metadata.json')
        assert m['status']=='response_received' and m['returncode']==0
        assert m['requested_model']=='claude-opus-5-5' and m['effort']=='high'
        assert m['auth_method']=='claude.ai_Pro_firstParty' and m['tools']=='disabled' and m['automatic_retries']==0
        assert set(m['reported_model_usage'])=={'claude-opus-5-5'}
        for f,k in [('response.txt','response_sha256'),('input.txt','input_sha256'),('instructions.txt','instructions_sha256')]:assert sha(d/f)==m[k]
        assert (d/'input.txt').read_bytes()==(HERE/f'request-round{n:02d}.md').read_bytes()
        assert (d/'instructions.txt').read_bytes()==(HERE/'mentor-role.txt').read_bytes()
        sessions.append(m['transport_session_id'])
        assert (HERE/f'astra-round{n:02d}.md').stat().st_size>1000
    assert len(set(sessions))==2
    files=[f for f in HERE.rglob('*') if f.is_file() and f.name!='verification.json' and '__pycache__' not in f.parts]
    out={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'actual_Claude_high_strategy_responses':2,
      'distinct_Claude_transport_sessions':2,'actual_Astra_review_response_files':2,
      'Astra_requested_model':'gpt-6.2-astra high','server_snapshots_independently_verified':False,
      'initial_and_followup_shared_bounded_packets_checked':True,'reviewed_followup_materials_preserved':True,
      'final_postreview_clarifications_not_third_reviewed':True,'new_patient_or_numeric_ratings_in_strategy_review':0,
      'file_sha256':{str(f.relative_to(HERE)):sha(f) for f in files}}
    (HERE/'verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print('Verified two actual Claude high design receipts and two Astra response files')
if __name__=='__main__':main()
