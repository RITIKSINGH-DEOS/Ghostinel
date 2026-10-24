import os
import glob
import json
import csv

with open('dataset/evidence_files.csv', mode='r', encoding='utf-8') as f:
    ev_files = {r['file_id']: r for r in csv.DictReader(f)}
    path_to_id = {r['file_path']: r['file_id'] for r in ev_files.values()}

# Test 1: service_resource_export_*.json
exports = glob.glob('dataset/evidence/records/service_resource_export_*.json')
print(f"Found {len(exports)} service_resource_exports.")

# Test 2: customer_data_snapshot_bundle_*.json
bundles = glob.glob('dataset/evidence/records/customer_data_snapshot_bundle_*.json')
print(f"Found {len(bundles)} snapshot bundles.")

# Test 3: customer_account_handover_20261001.txt
handover = 'dataset/evidence/records/customer_account_handover_20261001.txt'
print(f"Handover exists: {os.path.exists(handover)}")

# Test 4: resource_lookup_trace_*.log
traces = glob.glob('dataset/evidence/logs/resource_lookup_trace_*.log')
print(f"Found {len(traces)} resource lookup trace logs.")

# Test 5: customer_data_inventory_*.sql
inv_sqls = glob.glob('dataset/evidence/databases/customer_data_inventory_*.sql')
print(f"Found {len(inv_sqls)} inventory SQLs.")
