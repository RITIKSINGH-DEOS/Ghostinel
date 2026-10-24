import sys
sys.path.insert(0, '.')
import csv
import json
from datetime import datetime
from code.evidence_indexer import EvidenceIndexer
from code.identity_resolver import IdentityResolver

indexer = EvidenceIndexer()
resolver = IdentityResolver()

with open('dataset/sample_deletion_requests.csv', mode='r', encoding='utf-8') as f:
    sample_reqs = list(csv.DictReader(f))

with open('dataset/sample_output.csv', mode='r', encoding='utf-8') as f:
    sample_outs = {r['case_id']: (r['deletion_status'], json.loads(r['steps_json'])) for r in csv.DictReader(f)}

print(f"{'Case':<8} | {'GT Ev':<25} | {'Best Candidate Ev':<25}")
print("-" * 65)

matches = 0
for req in sample_reqs:
    cid = req['case_id']
    email = req['email']
    user = resolver.resolve_by_email(email)
    uid = user.user_id if user else None
    audit_dt = datetime.fromisoformat(req['audit_at'].replace('Z', ''))
    
    # Collect all observations for user
    user_obs = []
    if email.lower() in indexer.obs_by_email:
        user_obs.extend(indexer.obs_by_email[email.lower()])
    if uid and uid in indexer.obs_by_user_id:
        user_obs.extend(indexer.obs_by_user_id[uid])
        
    # Group by evidence_id
    ev_groups = {}
    for o in user_obs:
        if o.evidence_id:
            ev_groups.setdefault(o.evidence_id, []).append(o)
            
    # Find ev_id closest to audit_at (captured_at <= audit_at)
    best_ev = None
    min_diff = float('inf')
    
    for eid, obs_list in ev_groups.items():
        cap_str = indexer.evidence_files[eid]['captured_at']
        cap_dt = datetime.fromisoformat(cap_str.replace('Z', ''))
        diff = (audit_dt - cap_dt).total_seconds()
        # Captured before or at audit_at, or within 1 hour
        if -3600 <= diff and abs(diff) < min_diff:
            min_diff = abs(diff)
            best_ev = eid
            
    gt_evs = {s['evidence_id'] for s in sample_outs[cid][1] if s.get('evidence_id')}
    gt_ev_str = ", ".join(gt_evs) if gt_evs else "None"
    
    is_match = (best_ev in gt_evs) if gt_evs else (best_ev is None)
    if is_match:
        matches += 1
    print(f"{cid:<8} | {gt_ev_str:<25} | {str(best_ev):<25} | {'MATCH' if is_match else 'DIFF'}")

print(f"\nEvidence selection accuracy: {matches}/{len(sample_reqs)}")
