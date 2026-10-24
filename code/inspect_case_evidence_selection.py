import csv
import json
from datetime import datetime

with open('dataset/sample_deletion_requests.csv', mode='r', encoding='utf-8') as f:
    sample_reqs = {r['case_id']: r for r in csv.DictReader(f)}

with open('dataset/sample_output.csv', mode='r', encoding='utf-8') as f:
    sample_outs = {r['case_id']: (r['deletion_status'], json.loads(r['steps_json'])) for r in csv.DictReader(f)}

with open('dataset/evidence_files.csv', mode='r', encoding='utf-8') as f:
    evidence_files = {r['file_id']: r for r in csv.DictReader(f)}

print(f"{'Case':<8} | {'Status':<11} | {'Audit At':<20} | {'Evidence Cited'}")
print("-" * 75)

for cid, (status, steps) in sample_outs.items():
    req = sample_reqs[cid]
    ev_ids = {s['evidence_id'] for s in steps if s.get('evidence_id')}
    ev_str = ", ".join(f"{eid} ({evidence_files[eid]['file_path']})" for eid in ev_ids if eid in evidence_files)
    print(f"{cid:<8} | {status:<11} | {req['audit_at']:<20} | {ev_str}")
