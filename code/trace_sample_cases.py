import csv
import json

with open('dataset/sample_deletion_requests.csv', mode='r', encoding='utf-8') as f:
    requests = {r['case_id']: r for r in csv.DictReader(f)}

with open('dataset/sample_output.csv', mode='r', encoding='utf-8') as f:
    outputs = {r['case_id']: r for r in csv.DictReader(f)}

with open('dataset/user_identities.csv', mode='r', encoding='utf-8') as f:
    users_by_email = {r['email'].lower(): r for r in csv.DictReader(f)}
    f.seek(0)
    users_by_id = {r['user_id']: r for r in csv.DictReader(f)}

for cid in ['case_01', 'case_02', 'case_03', 'case_04', 'case_05']:
    req = requests[cid]
    out = outputs[cid]
    user = users_by_email.get(req['email'].lower())
    print(f"\n=================== {cid} ===================")
    print(f"Email: {req['email']} (reported: {req['reported_status']}, audit_at: {req['audit_at']})")
    print(f"User: {user}")
    print(f"Status in output: {out['deletion_status']}")
    steps = json.loads(out['steps_json'])
    for s in steps:
        print(f"  -> {s}")
