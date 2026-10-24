import glob
import re

sql_account_map = {}
for path in glob.glob('dataset/evidence/databases/*read_replica*.sql'):
    with open(path, mode='r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        inserts = re.findall(r"INSERT\s+INTO\s+[\"'\w]+\s+VALUES\s*\((.*?)\);", content, re.IGNORECASE)
        for vals_str in inserts:
            vals = [v.strip().strip("\"'") for v in vals_str.split(",")]
            if vals and vals[0].startswith('account_'):
                rid = vals[0]
                uid = next((v for v in vals if v.startswith('user_')), None)
                em = next((v for v in vals if '@' in v), None)
                sql_account_map[rid] = (uid, em)

print('Total accounts in read replicas:', len(sql_account_map))
for a, (u, e) in list(sql_account_map.items())[:5]:
    print(' ', a, '->', u, e)
