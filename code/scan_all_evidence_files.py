import os
import csv

with open('dataset/evidence_files.csv', mode='r') as f:
    files = list(csv.DictReader(f))

print(f"Total evidence files: {len(files)}")
origins = set(f['origin'] for f in files)
print("Origins:", origins)

for f in files:
    path = os.path.join('dataset', f['file_path'])
    exists = os.path.exists(path)
    size = os.path.getsize(path) if exists else 0
    print(f"{f['file_id']} | {f['origin']} | {f['captured_at']} | {f['file_path']} | {size} bytes")
