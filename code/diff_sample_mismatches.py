import csv
import json

gt = {r['case_id']: (r['deletion_status'], json.loads(r['steps_json'])) for r in csv.DictReader(open('dataset/sample_output.csv'))}
pred = {r['case_id']: (r['deletion_status'], json.loads(r['steps_json'])) for r in csv.DictReader(open('sample_predictions.csv'))}

for cid in sorted(gt.keys()):
    gt_stat, gt_steps = gt[cid]
    pr_stat, pr_steps = pred[cid]
    if gt_stat != pr_stat or gt_steps != pr_steps:
        print(f"\n==================== {cid} ====================")
        print(f"Status: GT={gt_stat} vs Pred={pr_stat}")
        print("GT Steps:")
        for s in gt_steps:
            print(f"   {s['step_no']}: {s['phase']} | {s['operation']} | {s['system_id']} | {s['resource_id']} | {s['state']} | ev={s.get('evidence_id')}")
        print("Pred Steps:")
        for s in pr_steps:
            print(f"   {s['step_no']}: {s['phase']} | {s['operation']} | {s['system_id']} | {s['resource_id']} | {s['state']} | ev={s.get('evidence_id')}")
