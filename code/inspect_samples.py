import csv
import json

def main():
    with open('dataset/sample_output.csv', mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            steps = json.loads(row['steps_json'])
            print(f"{row['case_id']}: status={row['deletion_status']}, steps_count={len(steps)}")
            for s in steps:
                print(f"   step {s['step_no']}: phase={s['phase']}, op={s['operation']}, sys={s['system_id']}, res={s['resource_id']}, state={s['state']}, ev={s.get('evidence_id')}")
            if i >= 6:
                break

if __name__ == '__main__':
    main()
