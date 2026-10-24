import csv
import json
import os

with open('dataset/sample_deletion_requests.csv', mode='r', encoding='utf-8') as f:
    sample_reqs = {r['case_id']: r for r in csv.DictReader(f)}

with open('dataset/sample_output.csv', mode='r', encoding='utf-8') as f:
    sample_outs = {r['case_id']: json.loads(r['steps_json']) for r in csv.DictReader(f)}

with open('dataset/evidence_files.csv', mode='r', encoding='utf-8') as f:
    ev_files = {r['file_id']: r for r in csv.DictReader(f)}

# Let's inspect where each resource in sample_output is mentioned in the evidence files!
for cid, steps in list(sample_outs.items())[:15]:
    req = sample_reqs[cid]
    cited_ev = {s['evidence_id'] for s in steps if s.get('evidence_id')}
    print(f"\n{cid} ({req['email']}) -> Cited: {cited_ev}")
    for eid in cited_ev:
        info = ev_files.get(eid)
        if info:
            print(f"   {eid}: {info['file_path']} (origin: {info['origin']}, captured_at: {info['captured_at']})")
