import csv
import json
from datetime import datetime

with open('dataset/sample_deletion_requests.csv', mode='r', encoding='utf-8') as f:
    sample_reqs = list(csv.DictReader(f))

with open('dataset/sample_output.csv', mode='r', encoding='utf-8') as f:
    sample_outs = {r['case_id']: json.loads(r['steps_json']) for r in csv.DictReader(f)}

with open('dataset/system_activity.csv', mode='r', encoding='utf-8') as f:
    activities = list(csv.DictReader(f))

worker_acts = [a for a in activities if a['source_system'] == 'deletion_worker']

# Group worker activities by date/hour cluster
print(f"Total worker activities: {len(worker_acts)}")

# Let's see: for each sample case, how closely do the GT resources match worker activities?
for req in sample_reqs:
    cid = req['case_id']
    gt_res = {s['resource_id'] for s in sample_outs[cid]}
    rep_dt = datetime.fromisoformat(req['reported_at'].replace('Z', ''))
    
    # Check all worker activities within 3 hours
    matched_acts = []
    for a in worker_acts:
        adt = datetime.fromisoformat(a['event_time'].replace('Z', ''))
        if abs((adt - rep_dt).total_seconds()) <= 3600 * 2:
            matched_acts.append(a)
            
    act_res = {a['resource_id'] for a in matched_acts}
    overlap = gt_res.intersection(act_res)
    print(f"{cid} | GT: {len(gt_res)} | In worker window (+/- 2h): {len(overlap)}/{len(gt_res)} (overlap: {overlap})")
