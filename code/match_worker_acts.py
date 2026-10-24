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

print(f"Total deletion_worker activities: {len(worker_acts)}")

for req in sample_reqs[:10]:
    cid = req['case_id']
    req_time = req['requested_at']
    rep_time = req['reported_at']
    steps = sample_outs[cid]
    step_resources = {s['resource_id'] for s in steps}
    
    # Find worker activities between requested_at and reported_at + 1 hour
    matched = []
    for a in worker_acts:
        t = a['event_time']
        if req_time <= t <= rep_time or (rep_time <= t and abs((datetime.fromisoformat(t.replace('Z', '')) - datetime.fromisoformat(rep_time.replace('Z', ''))).total_seconds()) < 3600):
            # Check if this activity's resource is in step_resources
            if a['resource_id'] in step_resources:
                matched.append(a)
    
    print(f"\n{cid} (req={req_time}, rep={rep_time}) | step_res={step_resources}")
    print(f"Matched {len(matched)} worker activities with matching resources:")
    for m in matched:
        print(f"   {m['activity_id']} | {m['event_time']} | {m['event_type']} | {m['target_system']} | {m['resource_id']} | {m['reported_result']}")
