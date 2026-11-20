"""
Ghostinel - AI Deletion Audit Agent
Main Pipeline Entry Point.

Evaluates all deletion requests from dataset/deletion_requests.csv, audits multimodal evidence,
and produces the official root-level output.csv.
"""
import os
import sys
import csv
import json
import argparse
from typing import List, Dict, Any

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from code.identity_resolver import IdentityResolver
from code.evidence_indexer import EvidenceIndexer
from code.refined_auditor import RefinedAuditor
from code.models import DeletionStatus


def run_pipeline(dataset_dir: str = "dataset", output_path: str = "output.csv"):
    print(f"==================================================")
    print(f"Ghostinel Deletion Audit Pipeline Starting")
    print(f"Dataset Directory: {dataset_dir}")
    print(f"Output File:       {output_path}")
    print(f"==================================================")

    # 1. Initialize core components
    print("\n[1/4] Loading Identity Resolver (identities & historical audit log)...")
    resolver = IdentityResolver(
        identities_csv=os.path.join(dataset_dir, "user_identities.csv"),
        audit_log_csv=os.path.join(dataset_dir, "user_audit_log.csv")
    )
    print(f"  Loaded {len(resolver.users_by_id)} users and {len(resolver.hash_to_user_id)} email hashes.")

    print("\n[2/4] Initializing Master Evidence Indexer across all 94 evidence files...")
    indexer = EvidenceIndexer(dataset_dir=dataset_dir, resolver=resolver)
    print(f"  Indexed {len(indexer.all_observations)} total observations across evidence files.")

    print("\n[3/4] Initializing Refined Auditor and Loading Worker Activities...")
    auditor = RefinedAuditor(indexer=indexer, resolver=resolver, dataset_dir=dataset_dir)
    print(f"  Loaded {len(auditor.worker_activities)} deletion worker activities.")

    # 2. Read deletion requests
    requests_file = os.path.join(dataset_dir, "deletion_requests.csv")
    if not os.path.exists(requests_file):
        raise FileNotFoundError(f"Deletion requests file not found: {requests_file}")

    with open(requests_file, mode="r", encoding="utf-8") as f:
        cases = list(csv.DictReader(f))

    print(f"\n[4/4] Auditing {len(cases)} Deletion Requests...")
    results: List[Dict[str, str]] = []
    status_counts = {
        DeletionStatus.COMPLETE.value: 0,
        DeletionStatus.INCOMPLETE.value: 0,
        DeletionStatus.NOT_APPLICABLE.value: 0,
    }

    for idx, c in enumerate(cases):
        case_id = c["case_id"]
        email = c["email"]
        requested_at = c["requested_at"]
        reported_status = c["reported_status"]
        reported_at = c["reported_at"]
        audit_at = c["audit_at"]
        request_text = c["request_text"]

        status, steps = auditor.audit_case(
            case_id=case_id,
            email=email,
            requested_at=requested_at,
            reported_status=reported_status,
            reported_at=reported_at,
            audit_at=audit_at,
            request_text=request_text
        )

        status_counts[status] = status_counts.get(status, 0) + 1
        steps_json = json.dumps(steps, separators=(",", ":"))

        results.append({
            "case_id": case_id,
            "deletion_status": status,
            "steps_json": steps_json
        })

        if (idx + 1) % 50 == 0 or (idx + 1) == len(cases):
            print(f"  Processed {idx + 1}/{len(cases)} cases...")

    # 3. Sort results by case_id strictly ascending
    def case_sort_key(r: Dict[str, str]):
        cid = r["case_id"]
        if cid.startswith("case_"):
            try:
                return int(cid.split("_")[1])
            except ValueError:
                return cid
        return cid

    results.sort(key=case_sort_key)

    # 4. Write to output.csv
    with open(output_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["case_id", "deletion_status", "steps_json"])
        writer.writeheader()
        writer.writerows(results)

    print(f"\n==================================================")
    print(f"Pipeline Execution Completed Successfully!")
    print(f"Generated: {output_path}")
    print(f"Total Rows: {len(results)}")
    print(f"Status Distribution:")
    for stat, count in sorted(status_counts.items()):
        pct = (count / len(results)) * 100
        print(f"  {stat:16s}: {count:3d} ({pct:.2f}%)")
    print(f"==================================================")

    # 5. Output Verification
    verify_output(output_path, expected_count=len(cases))


def verify_output(output_path: str, expected_count: int = 518):
    print("\nVerifying Output Contract Compliance...")
    if not os.path.exists(output_path):
        raise FileNotFoundError(f"Output file does not exist: {output_path}")
    
    with open(output_path, mode="r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    if len(reader) != expected_count:
        raise ValueError(f"Expected {expected_count} rows, found {len(reader)}")
    if reader and set(reader[0].keys()) != {"case_id", "deletion_status", "steps_json"}:
        raise ValueError(f"Invalid columns: {list(reader[0].keys()) if reader else []}")

    seen_cids = set()
    violations: List[str] = []

    for idx, row in enumerate(reader):
        cid = row.get("case_id", f"row_{idx+1}")
        stat = row.get("deletion_status", "")
        s_json = row.get("steps_json", "")
        
        if cid in seen_cids:
            violations.append(f"Row {idx+1} [{cid}]: Duplicate case_id")
        seen_cids.add(cid)

        if stat not in ["COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"]:
            violations.append(f"Row {idx+1} [{cid}]: Invalid deletion_status '{stat}'")

        try:
            parsed_steps = json.loads(s_json)
        except Exception as e:
            violations.append(f"Row {idx+1} [{cid}]: steps_json is invalid JSON: {e}")
            continue

        if not isinstance(parsed_steps, list):
            violations.append(f"Row {idx+1} [{cid}]: steps_json is not a JSON list/array")
            continue

        if stat == "NOT_APPLICABLE":
            if len(parsed_steps) != 0:
                violations.append(f"Row {idx+1} [{cid}]: NOT_APPLICABLE case must have empty steps array, found {len(parsed_steps)} steps")
        else:
            if len(parsed_steps) == 0:
                violations.append(f"Row {idx+1} [{cid}]: {stat} case must have non-empty steps array (found 0 steps)")
            for step_idx, step in enumerate(parsed_steps):
                for req_fld in ["step_no", "phase", "system_id", "resource_id", "operation", "state"]:
                    if req_fld not in step:
                        violations.append(f"Row {idx+1} [{cid}, step #{step_idx+1}]: Missing required field '{req_fld}'")
                if stat == "COMPLETE":
                    if step.get("phase") != "VERIFICATION":
                        violations.append(f"Row {idx+1} [{cid}, step #{step_idx+1}]: COMPLETE case step phase must be VERIFICATION, found '{step.get('phase')}'")
                    if not step.get("evidence_id"):
                        violations.append(f"Row {idx+1} [{cid}, step #{step_idx+1}]: COMPLETE case step must cite a non-empty evidence_id")

    if violations:
        print(f"\n❌ [Contract Violations Found: {len(violations)}]")
        for v in violations[:25]:
            print(f"  - {v}")
        if len(violations) > 25:
            print(f"  ... and {len(violations) - 25} additional violations omitted.")
        raise AssertionError(f"Output verification failed: {len(violations)} contract violation(s) detected across output rows.")

    print("ALL CONTRACT CHECKS PASSED PERFECTLY!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ghostinel Deletion Audit Pipeline")
    parser.add_argument("--dataset", default="dataset", help="Path to dataset directory")
    parser.add_argument("--output", default="output.csv", help="Path to output CSV file")
    args = parser.parse_args()

    run_pipeline(dataset_dir=args.dataset, output_path=args.output)
