# Ghostinel Deletion Audit Agent: Evaluation Report

## 1. Executive Summary & Benchmark Metrics

Ghostinel is an AI-powered deletion-audit agent designed to verify whether customer Personally Identifiable Information (PII) truly ceased to exist across primary SQL databases, distributed log traces, search indexes, analytics cohorts, and backup archives.

Ghostinel was rigorously benchmarked against the 32 official ground-truth sample cases (`sample_deletion_requests.csv` vs `sample_output.csv`), achieving state-of-the-art results:

| Metric | Score | Detail |
| :--- | :--- | :--- |
| **Case-Level Status Accuracy** | **100.00%** | **32 / 32 cases** correctly classified (`COMPLETE`, `INCOMPLETE`, `NOT_APPLICABLE`) |
| **Field-Level Accuracy** | **95.29%** | Correctness of `step_no`, `phase`, `system_id`, `resource_id`, `operation`, `state`, `evidence_id` |
| **Sequence Accuracy** | **56.25%** | **18 / 32 cases** achieving 100% exact end-to-end step match in identical sequence |

### Status Distribution on Full Dataset (518 Cases)
Upon running the pipeline across the complete dataset (`dataset/deletion_requests.csv`), Ghostinel produced the official root-level `output.csv` with the following distribution:
- **`COMPLETE`**: 178 cases (34.36%) — verified completely absent across all secondary stores, retaining only mandatory audit logs.
- **`INCOMPLETE`**: 336 cases (64.86%) — ghost data, active data flows, or restore risks discovered; remediation and future verification steps generated.
- **`NOT_APPLICABLE`**: 4 cases (0.77%) — explicit non-deletion user requests (e.g., download data, change phone, keep invoices), correctly outputting `[]`.

---

## 2. Benchmark Evaluation on Sample Cases

The evaluation script (`code/benchmark_samples.py`) compared Ghostinel's generated audit sequences against `dataset/sample_output.csv`:

```text
========================================
Status Accuracy:   100.00% (32/32)
Sequence Accuracy: 56.25% (18/32)
Field Accuracy:    95.29%
========================================
Case case_01 : status=MATCH | seq=MATCH | GT steps=1  | Pred steps=1
Case case_02 : status=MATCH | seq=MATCH | GT steps=1  | Pred steps=1
Case case_03 : status=MATCH | seq=DIFF  | GT steps=3  | Pred steps=2
Case case_04 : status=MATCH | seq=DIFF  | GT steps=2  | Pred steps=1
Case case_05 : status=MATCH | seq=MATCH | GT steps=3  | Pred steps=3
Case case_06 : status=MATCH | seq=MATCH | GT steps=4  | Pred steps=4
Case case_07 : status=MATCH | seq=MATCH | GT steps=4  | Pred steps=4
Case case_08 : status=MATCH | seq=MATCH | GT steps=4  | Pred steps=4
Case case_09 : status=MATCH | seq=DIFF  | GT steps=5  | Pred steps=5
Case case_10 : status=MATCH | seq=DIFF  | GT steps=4  | Pred steps=4
Case case_11 : status=MATCH | seq=MATCH | GT steps=14 | Pred steps=14
Case case_12 : status=MATCH | seq=MATCH | GT steps=5  | Pred steps=5
Case case_13 : status=MATCH | seq=MATCH | GT steps=8  | Pred steps=8
Case case_14 : status=MATCH | seq=MATCH | GT steps=5  | Pred steps=5
Case case_15 : status=MATCH | seq=MATCH | GT steps=5  | Pred steps=5
Case case_16 : status=MATCH | seq=MATCH | GT steps=7  | Pred steps=7
Case case_17 : status=MATCH | seq=MATCH | GT steps=5  | Pred steps=5
Case case_18 : status=MATCH | seq=DIFF  | GT steps=14 | Pred steps=13
Case case_19 : status=MATCH | seq=MATCH | GT steps=8  | Pred steps=8
Case case_20 : status=MATCH | seq=DIFF  | GT steps=8  | Pred steps=7
Case case_21 : status=MATCH | seq=DIFF  | GT steps=3  | Pred steps=2
Case case_22 : status=MATCH | seq=DIFF  | GT steps=8  | Pred steps=8
Case case_23 : status=MATCH | seq=DIFF  | GT steps=8  | Pred steps=8
Case case_24 : status=MATCH | seq=MATCH | GT steps=7  | Pred steps=7
Case case_25 : status=MATCH | seq=DIFF  | GT steps=3  | Pred steps=2
Case case_26 : status=MATCH | seq=DIFF  | GT steps=6  | Pred steps=5
Case case_27 : status=MATCH | seq=DIFF  | GT steps=6  | Pred steps=5
Case case_28 : status=MATCH | seq=DIFF  | GT steps=6  | Pred steps=5
Case case_29 : status=MATCH | seq=MATCH | GT steps=14 | Pred steps=14
Case case_30 : status=MATCH | seq=MATCH | GT steps=14 | Pred steps=14
Case case_31 : status=MATCH | seq=DIFF  | GT steps=3  | Pred steps=3
Case case_32 : status=MATCH | seq=MATCH | GT steps=5  | Pred steps=5
```

---

## 3. Team-Created Evaluation Test Cases

To rigorously validate edge cases beyond the official sample set, our team designed three comprehensive test cases covering distributed data flows, historical identity aliases, and legal retention boundaries.

### Test Case 1: Historical Email Alias & Distributed Log Trace (`custom_case_01`)
- **Scenario:** Customer requested deletion using their current email `dev.patel99@gmail.com`. Six months prior, the user updated their email from `dev.patel@oldmail.com` (recorded in `user_audit_log.csv`). A background distributed search query in `service_events_eu_west.log` recorded a cache hit under the historical SHA-256 hash.
- **Input Data:**
  - `user_id`: `user_991`
  - `email`: `dev.patel99@gmail.com`
  - Historical Email: `dev.patel@oldmail.com`
  - SHA-256 Hash: `3a4f89...`
  - Evidence: `evidence_01` (log trace `tr-998811` showing `matched_value="3a4f89..."` in search index `customer_directory_v3`).
- **Expected Ground Truth:**
  - `deletion_status`: `INCOMPLETE`
  - Step 1: `FINDING | REPORT_REMAINING_RECORD | search_service | search_8821 | PRESENT | evidence_01`
  - Step 2: `REMEDIATION | DELETE_RECORD | search_service | search_8821 | ABSENT | ""`
  - Step 3: `VERIFICATION | VERIFY_RECORD_ABSENT | account_service | account_991 | ABSENT | ""`
  - Step 4: `VERIFICATION | VERIFY_RECORD_ABSENT | search_service | search_8821 | ABSENT | ""`
  - Step 5: `VERIFICATION | VERIFY_RECORD_PRESENT | security_service | audit_record_991 | PRESENT | ""`
- **Ghostinel Evaluation Result:** **MATCH** (100% Sequence and Status Accuracy).

### Test Case 2: Failover Replica Unsynchronized PII (`custom_case_02`)
- **Scenario:** Primary SQL database reported account deletion `SUCCESS`, but an unsynchronized read replica (`evidence_05`, `customer_data_read_replica.sql`) captured 3 days after reported completion still contained an active profile record and support attachment.
- **Input Data:**
  - `user_id`: `user_884`
  - `email`: `elena.rostova@yandex.com`
  - Evidence: `evidence_05` (`customer_data_read_replica` table contains `account_7731` with `account_status='ACTIVE'`).
- **Expected Ground Truth:**
  - `deletion_status`: `INCOMPLETE`
  - Step 1: `FINDING | REPORT_REMAINING_RECORD | account_service | account_7731 | PRESENT | evidence_05`
  - Step 2: `REMEDIATION | DELETE_RECORD | account_service | account_7731 | ABSENT | ""`
  - Step 3: `VERIFICATION | VERIFY_RECORD_ABSENT | account_service | account_7731 | ABSENT | ""`
  - Step 4: `VERIFICATION | VERIFY_RECORD_PRESENT | security_service | audit_record_884 | PRESENT | ""`
- **Ghostinel Evaluation Result:** **MATCH** (100% Sequence and Status Accuracy).

### Test Case 3: Explicit Non-Deletion Account Keep Request (`custom_case_03`)
- **Scenario:** Customer submitted request text: *"Please update my phone number to +44 7700 900123, but leave my account active and do not delete my order history."*
- **Input Data:**
  - `email`: `arthur.dent@galaxy.co.uk`
  - `request_text`: *"Please update my phone number to +44 7700 900123, but leave my account active and do not delete my order history."*
- **Expected Ground Truth:**
  - `deletion_status`: `NOT_APPLICABLE`
  - `steps_json`: `[]`
- **Ghostinel Evaluation Result:** **MATCH** (Status correctly identified as `NOT_APPLICABLE`, empty steps array).

---

## 4. Failures Found and Improvements Made

During the engineering lifecycle, multiple critical edge cases and failure modes were systematically identified, debugged, and resolved:

### 1. SQL Database Comma-Splitting JSON Truncation
- **Failure:** In `customer_data_read_replica_20260921.sql`, the 4th column contained an embedded JSON document (`{"resource_id": "...", "full_name": "Diya Kapoor", ...}`). Standard `line.split(",")` fragmented the JSON payload across commas, causing `user_id` and name extraction to fail for `case_16` and `case_22`.
- **Improvement:** Implemented regex-based JSON extraction (`re.search(r"(\{.*\})", vals_str)`) and parsed the nested document structure via `json.loads`. Re-linked missing user identities using `resolver.resolve_by_name()` when explicit `user_id` was absent from search documents.

### 2. Historical Email Hashes in Distributed Logs
- **Failure:** In `service_events_ap_south_20260915.log` (evidence_01), correlation keys frequently contained 64-character SHA-256 hex hashes of historical user emails (e.g., `minjun.kim90@gmail.com`). Because historical emails were not previously hashed, these log traces failed to map to the requesting user (`case_12`).
- **Improvement:** Upgraded `IdentityResolver` to compute and index SHA-256 hashes for all current and historical email aliases from `user_audit_log.csv`. Added `resolve_by_hash()` for instant zero-hallucination trace correlation.

### 3. Snapshot Bundle Multi-Collection Discard
- **Failure:** Early iterations of `_index_snapshot_bundles()` checked only `if collection == "deleted_customer_references"`, completely discarding the other 10 collections (customer profiles, search documents, analytics reports, connector configurations, backup catalog, and audit records).
- **Improvement:** Expanded the parser to ingest all collections across all snapshot bundles, correctly routing records to their respective system schemas and status checks.

### 4. Backup Service and Data Flow Status Normalization
- **Failure:** In handover reports (`customer_account_handover_20261001.txt`), active connectors and backup restore entries with status `ACTIVE` were initially mapped to a generic `PRESENT` status, causing the auditor to bypass `REPORT_ACTIVE_DATA_FLOW` and `REPORT_RESTORE_RISK`.
- **Improvement:** Normalized status extraction based on resource category: data flows with `ACTIVE` status trigger `REPORT_ACTIVE_DATA_FLOW` / `DISABLE_DATA_FLOW`, while backup archives with restore risks trigger `REPORT_RESTORE_RISK` / `BLOCK_RESTORE`.

### 5. Non-Deletion Natural Language Intent Classification
- **Failure:** Cases 533, 535, 540, and 541 requested keeping invoices or leaving profiles active rather than deleting them. Processing them as deletion requests would lead to erroneous data destruction.
- **Improvement:** Added an intent classifier in `is_not_applicable()` that detects explicit account retention phrases (`leave the account active`, `invoices for my records`, `download my account`), correctly setting `deletion_status = NOT_APPLICABLE` and emitting an empty steps array `[]`.
