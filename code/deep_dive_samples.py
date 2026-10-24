import csv
import json

with open('dataset/sample_deletion_requests.csv', mode='r', encoding='utf-8') as f:
    sample_reqs = {r['case_id']: r for r in csv.DictReader(f)}

with open('dataset/sample_output.csv', mode='r', encoding='utf-8') as f:
    sample_outs = {r['case_id']: (r['deletion_status'], json.loads(r['steps_json'])) for r in csv.DictReader(f)}

with open('dataset/user_identities.csv', mode='r', encoding='utf-8') as f:
    users_by_email = {r['email'].lower(): r for r in csv.DictReader(f)}

with open('dataset/system_activity.csv', mode='r', encoding='utf-8') as f:
    activities = list(csv.DictReader(f))

with open('dataset/evidence_files.csv', mode='r', encoding='utf-8') as f:
    evidence_files = {r['file_id']: r for r in csv.DictReader(f)}

print(f"Loaded {len(sample_reqs)} sample cases.")

for cid, (status, steps) in list(sample_outs.items())[:12]:
    req = sample_reqs[cid]
    user = users_by_email.get(req['email'].lower())
    uid = user['user_id'] if user else "UNKNOWN"
    print(f"\n{'='*20} {cid} ({status}) | user={uid} | email={req['email']} {'='*20}")
    print(f"Requested: {req['requested_at']} | Reported: {req['reported_status']} at {req['reported_at']} | Audit: {req['audit_at']}")
    
    # Check what activities matched
    res_ids = {s['resource_id'] for s in steps}
    matched_acts = [a for a in activities if a['resource_id'] in res_ids or (uid and uid in a['details'])]
    print(f"Steps count: {len(steps)}")
    for s in steps:
        ev_info = evidence_files.get(s.get('evidence_id', ''), {})
        print(f"  Step {s['step_no']}: {s['phase']} | {s['operation']} | {s['system_id']} | {s['resource_id']} | {s['state']} | ev={s.get('evidence_id')} ({ev_info.get('file_path', '')})")
    
    print(f"Matched activities in system_activity.csv ({len(matched_acts)}):")
    for a in matched_acts:
        print(f"    act_id={a['activity_id']} | time={a['event_time']} | type={a['event_type']} | {a['source_system']}->{a['target_system']} | res={a['resource_id']} | res_result={a['reported_result']}")
