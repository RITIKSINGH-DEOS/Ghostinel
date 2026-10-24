import csv
from datetime import datetime

with open('dataset/system_activity.csv', mode='r', encoding='utf-8') as f:
    acts = [r for r in csv.DictReader(f) if r['source_system'] == 'deletion_worker']

# Group acts by time proximity (e.g. gaps > 30 minutes start a new cluster)
acts.sort(key=lambda x: x['event_time'])

clusters = []
curr = []
for a in acts:
    if not curr:
        curr.append(a)
    else:
        last_t = datetime.fromisoformat(curr[-1]['event_time'].replace('Z', ''))
        curr_t = datetime.fromisoformat(a['event_time'].replace('Z', ''))
        if (curr_t - last_t).total_seconds() > 3600 * 2: # 2 hours gap
            clusters.append(curr)
            curr = [a]
        else:
            curr.append(a)

if curr:
    clusters.append(curr)

print(f"Total clusters of deletion_worker activity: {len(clusters)}")
for i, c in enumerate(clusters[:10]):
    print(f"\nCluster {i}: count={len(c)}, start={c[0]['event_time']}, end={c[-1]['event_time']}")
    res_list = [f"{a['target_system']}:{a['resource_id']}" for a in c]
    print(f"  Resources: {res_list}")
