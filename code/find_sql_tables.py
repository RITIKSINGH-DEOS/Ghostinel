import glob
import re

tables = set()
for p in glob.glob('dataset/evidence/databases/*.sql'):
    with open(p, mode='r', encoding='utf-8', errors='ignore') as f:
        matches = re.findall(r"CREATE\s+TABLE\s+[\"'\w]*?([a-zA-Z0-9_]+)[\"'\w]*?\s*\(", f.read(), re.IGNORECASE)
        tables.update(matches)

print("SQL tables:", sorted(tables))
