import csv
import json

with open('dataset/sample_deletion_requests.csv', mode='r', encoding='utf-8') as f:
    sample_requests = list(csv.DictReader(f))

with open('dataset/sample_output.csv', mode='r', encoding='utf-8') as f:
    sample_outputs = {r['case_id']: json.loads(r['steps_json']) for r in csv.DictReader(f)}

with open('dataset/system_activity.csv', mode='r', encoding='utf-8') as f:
    activities = list(csv.DictReader(f))

for req in sample_requests[:5]:
    cid = req['case_id']
    steps = sample_outputs[cid]
    res_ids = {s['resource_id'] for s in steps}
    print(f"\n--- {cid} (reported_at={req['reported_at']}, res_ids={res_ids}) ---")
    matched_acts = [a for a in activities if a['resource_id'] in res_ids]
    for a in matched_acts:
        print(f"  Activity: {a['activity_id']} | {a['event_time']} | {a['event_type']} | {a['source_system']} -> {a['target_system']} | res={a['resource_id']} | {a['details']}")
