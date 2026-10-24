import csv

with open('dataset/deletion_requests.csv', mode='r', encoding='utf-8') as f:
    requests = list(csv.DictReader(f))

suspicious_words = [
    'leave the account', 'keep the account', 'continue using',
    'leave my profile', 'download my account', 'update my',
    'change my', 'portable format', 'invoices for my records',
    'rectification', 'access request'
]

for r in requests:
    text_lower = r['request_text'].lower()
    for w in suspicious_words:
        if w in text_lower:
            print(f"Case: {r['case_id']} | Reported: {r['reported_status']} | Text: {r['request_text']}")
            break
