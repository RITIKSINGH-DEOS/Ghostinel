import csv
import json
from collections import Counter

with open('dataset/sample_output.csv', mode='r', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

print(f"Total sample cases: {len(rows)}")
status_counts = Counter(r['deletion_status'] for r in rows)
print("Status counts:", status_counts)

operations = Counter()
systems = Counter()
evidences = Counter()

for r in rows:
    steps = json.loads(r['steps_json'])
    for s in steps:
        operations[s['operation']] += 1
        systems[s['system_id']] += 1
        if s.get('evidence_id'):
            evidences[s['evidence_id']] += 1

print("\nOperations:", operations)
print("\nSystems:", systems)
print("\nEvidences cited:", len(evidences), "unique evidence IDs")
