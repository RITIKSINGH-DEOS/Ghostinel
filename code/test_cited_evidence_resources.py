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

print(f"{'Case':<8} | {'GT Resources':<55} | {'Found in Cited Evidence':<55}")
print("-" * 125)

for req in sample_reqs:
    cid = req['case_id']
    email = req['email']
    user = resolver.resolve_by_email(email)
    uid = user.user_id if user else None
    gt_steps = sample_outs[cid]
    gt_res = {s['resource_id'] for s in gt_steps}
    cited_ev = {s['evidence_id'] for s in gt_steps if s.get('evidence_id')}
    
    # Collect observations from cited_ev
    found_res = set()
    for eid in cited_ev:
        # Check all observations in this evidence file matching email or uid
        for o in indexer.all_observations:
            if o.evidence_id == eid:
                if (o.email and o.email.lower() == email.lower()) or (uid and o.user_id == uid):
                    found_res.add(o.resource_id)
                    
    print(f"{cid:<8} | {str(gt_res):<55} | {str(found_res):<55} | {'MATCH' if gt_res == found_res else 'DIFF'}")
