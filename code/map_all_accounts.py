import os
import glob
import re
import json

account_map = {}

# 1. Check all SQL files
for path in glob.glob('dataset/evidence/databases/*.sql'):
    with open(path, mode='r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        inserts = re.findall(r"INSERT\s+INTO\s+[\"'\w]+\s+VALUES\s*\((.*?)\);", content, re.IGNORECASE)
        for vals_str in inserts:
            vals = [v.strip().strip("\"'") for v in vals_str.split(",")]
            for v in vals:
                if v.startswith("account_"):
                    acc = v
                    uid = next((x for x in vals if x.startswith("user_")), None)
                    em = next((x for x in vals if "@" in x), None)
                    if em and 'email' in em: # clean up json if needed
                        m = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", em)
                        em = m.group(0) if m else em
                    account_map[acc] = (uid, em)

# 2. Check all JSON files
for path in glob.glob('dataset/evidence/records/*.json'):
    with open(path, mode='r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        # Find json objects with account_
        accs = re.findall(r"\"account_[0-9]+\"", content)
        for a_raw in set(accs):
            acc = a_raw.strip('"')
            # find enclosing object
            idx = content.find(a_raw)
            start = content.rfind("{", 0, idx)
            end = content.find("}", idx)
            if start != -1 and end != -1:
                obj_str = content[start:end+1]
                em_m = re.search(r"\"email\":\s*\"([^\"]+)\"", obj_str)
                uid_m = re.search(r"\"(?:customer_reference|subject_reference|user_id)\":\s*\"([^\"]+)\"", obj_str)
                em = em_m.group(1) if em_m else None
                uid = uid_m.group(1) if uid_m else None
                if em or uid:
                    account_map[acc] = (uid, em)

# 3. Check customer_account_handover_20261001.txt
with open('dataset/evidence/records/customer_account_handover_20261001.txt', mode='r', encoding='utf-8') as f:
    for line in f:
        m = re.search(r"(account_[0-9]+).*?([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", line)
        if m:
            account_map[m.group(1)] = (None, m.group(2))

# 4. Check all logs
for path in glob.glob('dataset/evidence/logs/*.log'):
    with open(path, mode='r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if "account_" in line and ("@" in line or "user_" in line):
                acc_m = re.search(r"(account_[0-9]+)", line)
                em_m = re.search(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", line)
                uid_m = re.search(r"(user_[0-9]+)", line)
                if acc_m:
                    acc = acc_m.group(1)
                    em = em_m.group(1) if em_m else None
                    uid = uid_m.group(1) if uid_m else None
                    if em or uid:
                        account_map[acc] = (uid, em)

print(f"Total mapped accounts: {len(account_map)}")
print("Sample accounts:", list(account_map.items())[:10])
