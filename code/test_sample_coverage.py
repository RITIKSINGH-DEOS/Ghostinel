import sys
sys.path.insert(0, '.')
import csv
import json
from code.evidence_indexer import EvidenceIndexer
from code.identity_resolver import IdentityResolver

indexer = EvidenceIndexer()
resolver = IdentityResolver()

with open('dataset/sample_deletion_requests.csv', mode='r', encoding='utf-8') as f:
    sample_reqs = list(csv.DictReader(f))

with open('dataset/sample_output.csv', mode='r', encoding='utf-8') as f:
    sample_outs = {r['case_id']: json.loads(r['steps_json']) for r in csv.DictReader(f)}

matches = 0
for req in sample_reqs:
    cid = req['case_id']
    email = req['email']
    user = resolver.resolve_by_email(email)
    uid = user.user_id if user else None
    
    # Lookup observations
    obs_list = []
    if email.lower() in indexer.obs_by_email:
        obs_list.extend(indexer.obs_by_email[email.lower()])
    if uid and uid in indexer.obs_by_user_id:
        obs_list.extend(indexer.obs_by_user_id[uid])
        
    obs_res_ids = {o.resource_id for o in obs_list}
    gt_steps = sample_outs[cid]
    gt_res_ids = {s['resource_id'] for s in gt_steps}
    
    overlap = obs_res_ids.intersection(gt_res_ids)
    print(f"{cid} | user={uid} | GT res: {gt_res_ids} | Found res: {obs_res_ids} | Overlap: {overlap}")
    if overlap == gt_res_ids:
        matches += 1

print(f"\nExact resource coverage: {matches}/{len(sample_reqs)}")
