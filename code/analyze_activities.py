import csv
from collections import Counter

with open('dataset/system_activity.csv', mode='r', encoding='utf-8') as f:
    activities = list(csv.DictReader(f))

print(f"Total system activities: {len(activities)}")

event_types = Counter(a['event_type'] for a in activities)
print("Event types:", event_types)

sources = Counter(a['source_system'] for a in activities)
print("Source systems:", sources)

targets = Counter(a['target_system'] for a in activities)
print("Target systems:", targets)

results = Counter(a['reported_result'] for a in activities)
print("Reported results:", results)
