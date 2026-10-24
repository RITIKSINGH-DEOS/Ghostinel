import csv
import json

with open('dataset/deletion_requests.csv', mode='r', encoding='utf-8') as f:
    requests = list(csv.DictReader(f))

# Look for texts that don't match typical deletion keywords
keywords = [
    'delet', 'eras', 'clos', 'remov', 'cancel', 'elimin', 'suppr', 'exclu', 'apag',
    'lösch', 'entfern', 'cancell', 'rimuov', 'chiud', 'scaric',
    '削除', '解約', '退会', '消去',
    '삭제', '탈퇴', '제거', '폐쇄',
    'forget', 'purge', 'wipe'
]

potential_non_deletions = []
for r in requests:
    text_lower = r['request_text'].lower()
    if not any(k in text_lower for k in keywords):
        potential_non_deletions.append(r)

print(f"Total requests: {len(requests)}")
print(f"Potential non-deletion requests: {len(potential_non_deletions)}")
for r in potential_non_deletions[:10]:
    print(f"\nCase: {r['case_id']} | Reported: {r['reported_status']}")
    print(f"Text: {r['request_text']}")
