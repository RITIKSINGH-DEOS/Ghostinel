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
    sample_outs = {r['case_id']: json.loads(r['steps_json']) for r in csv.DictReader(f)}

with open('dataset/system_activity.csv', mode='r', encoding='utf-8') as f:
    activities = list(csv.DictReader(f))

worker_acts = [a for a in activities if a['source_system'] == 'deletion_worker']

matches = 0
for req in sample_reqs:
    cid = req['case_id']
    email = req['email']
    user = resolver.resolve_by_email(email)
    uid = user.user_id if user else None
    
    rep_time_str = req['reported_at']
    rep_dt = datetime.fromisoformat(rep_time_str.replace('Z', ''))
    req_dt = datetime.fromisoformat(req['requested_at'].replace('Z', ''))
    
    # 1. Collect from EvidenceIndexer
    obs_res_ids = set()
    if email.lower() in indexer.obs_by_email:
        obs_res_ids.update(o.resource_id for o in indexer.obs_by_email[email.lower()])
    if uid and uid in indexer.obs_by_user_id:
        obs_res_ids.update(o.resource_id for o in indexer.obs_by_user_id[uid])
        
    # 2. Collect from deletion_worker activities around reported_at
    # Time window: between requested_at and reported_at + 2 hours
    candidate_acts = []
    for a in worker_acts:
        adt = datetime.fromisoformat(a['event_time'].replace('Z', ''))
        # Within window of reported_at: +/- 3 hours
        diff_hours = abs((adt - rep_dt).total_seconds()) / 3600.0
        if diff_hours <= 2.5:
            candidate_acts.append(a)
            
    # Check GT resources
    gt_steps = sample_outs[cid]
    gt_res_ids = {s['resource_id'] for s in gt_steps}
    
    # How many GT resources are in candidate_acts?
    worker_res_ids = {a['resource_id'] for a in candidate_acts}
    total_found = obs_res_ids.union(worker_res_ids)
    
    overlap = total_found.intersection(gt_res_ids)
    if overlap == gt_res_ids:
        matches += 1
    else:
        missing = gt_res_ids - total_found
        print(f"Missing in {cid}: {missing} (GT: {gt_res_ids})")

print(f"\nResource coverage with worker acts: {matches}/{len(sample_reqs)}")
