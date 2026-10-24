import sys
import os
sys.path.insert(0, os.path.abspath("."))
import csv
import json
from datetime import datetime
from code.evidence_indexer import EvidenceIndexer
from code.identity_resolver import IdentityResolver
from code.refined_auditor import RefinedAuditor

indexer = EvidenceIndexer()
resolver = IdentityResolver()
auditor = RefinedAuditor(indexer, resolver)

gt = {r['case_id']: (r['deletion_status'], json.loads(r['steps_json'])) for r in csv.DictReader(open('dataset/sample_output.csv', encoding='utf-8'))}
sample_reqs = {r['case_id']: r for r in csv.DictReader(open('dataset/sample_deletion_requests.csv', encoding='utf-8'))}

diff_cids = ['case_12', 'case_14', 'case_15', 'case_16', 'case_17', 'case_19', 'case_22']
for cid in diff_cids:
    req = sample_reqs[cid]
    email = req['email']
    gt_stat, gt_steps = gt[cid]
    gt_eids = list(set(s.get('evidence_id') for s in gt_steps if s.get('evidence_id')))
    u = resolver.resolve_by_email(email)
    uid = u.user_id if u else None
    
    pred_stat, pred_steps = auditor.audit_case(cid, email, req['requested_at'], req['reported_status'], req['reported_at'], req['audit_at'], req['request_text'])
    found_eids = auditor.find_evidence_for_case(email, uid, req['audit_at'])
    print(f"=== {cid} ===")
    print(f"  email: {email}, audit_at: {req['audit_at']}")
    print(f"  GT Status: {gt_stat}, GT Eids: {gt_eids}")
    print(f"  Found Eids by find_evidence_for_case: {found_eids}")
    print(f"  Pred Status: {pred_stat}")
    
    all_user_obs = [o for o in indexer.all_observations if (o.email and o.email.lower() == email.lower()) or (uid and o.user_id == uid)]
    by_ev = {}
    for o in all_user_obs:
        by_ev.setdefault(o.evidence_id, []).append((o.system_id, o.resource_id, o.status))
    print(f"  All evidence containing user: {list(by_ev.keys())}")
    for e in gt_eids:
        print(f"    GT eid {e} has {len(by_ev.get(e, []))} obs: {by_ev.get(e, [])}")
    print("  GT steps:")
    for s in gt_steps:
        print(f"    {s}")
    print("  Pred steps:")
    for s in pred_steps:
        print(f"    {s}")
