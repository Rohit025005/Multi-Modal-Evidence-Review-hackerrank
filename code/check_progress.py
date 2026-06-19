import csv
with open('../output_sample.csv', 'r', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))
print(f'Claims in output: {len(rows)}/20')
for r in rows:
    print(f"  {r['user_id']}: status={r['claim_status']}, issue={r['issue_type']}, part={r['object_part']}, severity={r['severity']}")
