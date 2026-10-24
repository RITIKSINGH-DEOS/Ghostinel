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
    assert os.path.exists(output_path), f"Output file does not exist: {output_path}"
    
    with open(output_path, mode="r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    assert len(reader) == expected_count, f"Expected {expected_count} rows, found {len(reader)}"
    assert reader[0].keys() == {"case_id", "deletion_status", "steps_json"}, "Invalid columns"

    seen_cids = set()
    for row in reader:
        cid = row["case_id"]
        stat = row["deletion_status"]
        s_json = row["steps_json"]
        
        assert cid not in seen_cids, f"Duplicate case_id: {cid}"
        seen_cids.add(cid)
        assert stat in ["COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"], f"Invalid status: {stat}"

        parsed_steps = json.loads(s_json)
        assert isinstance(parsed_steps, list), f"steps_json is not an array for {cid}"

        if stat == "NOT_APPLICABLE":
            assert len(parsed_steps) == 0, f"NOT_APPLICABLE case {cid} must have empty steps array"
        else:
            assert len(parsed_steps) > 0, f"{stat} case {cid} must have non-empty steps array"
            for step in parsed_steps:
                assert "step_no" in step and "phase" in step and "system_id" in step and "resource_id" in step and "operation" in step and "state" in step, f"Missing fields in step {step}"
                if stat == "COMPLETE":
                    assert step["phase"] == "VERIFICATION", f"COMPLETE case {cid} must have only VERIFICATION steps"
                    assert step["evidence_id"] != "", f"COMPLETE case {cid} step must cite non-empty evidence_id"

    print("ALL CONTRACT CHECKS PASSED PERFECTLY!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ghostinel Deletion Audit Pipeline")
    parser.add_argument("--dataset", default="dataset", help="Path to dataset directory")
    parser.add_argument("--output", default="output.csv", help="Path to output CSV file")
    args = parser.parse_args()

    run_pipeline(dataset_dir=args.dataset, output_path=args.output)
