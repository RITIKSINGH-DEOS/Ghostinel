import re
import json

with open('dataset/evidence/databases/customer_data_read_replica_20260921.sql', encoding='utf-8') as f:
    content = f.read()

inserts = re.findall(r"INSERT\s+INTO\s+[\"']?([a-zA-Z0-9_]+)[\"']?\s+VALUES\s*\((.*?)\);", content, re.DOTALL)
print(f"Total inserts found: {len(inserts)}")

for tname, val in inserts:
    # Extract JSON if present
    j_match = re.search(r"(\{.*\})", val)
    if j_match:
        try:
            payload = json.loads(j_match.group(1))
            res_id = payload.get("resource_id")
            uid = payload.get("user_id") or payload.get("customer_reference")
            em = payload.get("email") or payload.get("customer_email")
            doc = payload.get("document", {})
            name = payload.get("full_name") or (doc.get("display_name") if isinstance(doc, dict) else None)
            if not uid and isinstance(doc, dict):
                uid = doc.get("user_id") or doc.get("customer_reference")
            if not em and isinstance(doc, dict):
                em = doc.get("email") or doc.get("customer_email")
            print(f"Table {tname}: res={res_id} uid={uid} em={em} name={name}")
        except Exception as e:
            print(f"Table {tname}: error {e}")
