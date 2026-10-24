"""
Ghostinel - Interactive Case Inspector CLI.
Allows user to inspect any deletion request case in detail.

Usage:
    python code/inspect_case.py [case_id]
Example:
    python code/inspect_case.py case_01
    python code/inspect_case.py case_11
    python code/inspect_case.py case_33
    python code/inspect_case.py case_533
"""
import sys
import os
import csv
import json

# Ensure clean UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from code.identity_resolver import IdentityResolver
from code.evidence_indexer import EvidenceIndexer
from code.refined_auditor import RefinedAuditor


def inspect(case_id_arg: str = None):
    dataset_dir = "dataset"
    print("=" * 60)
    print("         GHOSTINEL CASE AUDIT INSPECTOR         ")
    print("=" * 60)

    # Load requests from both sample and full datasets
    all_requests = {}
    sample_file = os.path.join(dataset_dir, "sample_deletion_requests.csv")
    full_file = os.path.join(dataset_dir, "deletion_requests.csv")

    if os.path.exists(sample_file):
        with open(sample_file, mode="r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                all_requests[r["case_id"]] = r

    if os.path.exists(full_file):
        with open(full_file, mode="r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                all_requests[r["case_id"]] = r

    if not case_id_arg:
        if len(sys.argv) > 1:
            case_id_arg = sys.argv[1].strip()
        else:
            case_id_arg = input("\nEnter case_id to inspect (e.g. case_01, case_11, case_33, case_533): ").strip()

    if not case_id_arg:
        case_id_arg = "case_01"

    if case_id_arg not in all_requests:
        print(f"\n[!] Error: '{case_id_arg}' not found in dataset!")
        print(f"Available cases: {len(all_requests)} total cases (case_01 to case_550).")
        return

    req = all_requests[case_id_arg]

    print(f"\n[*] Auditing {req['case_id']}...")
    resolver = IdentityResolver(
        identities_csv=os.path.join(dataset_dir, "user_identities.csv"),
        audit_log_csv=os.path.join(dataset_dir, "user_audit_log.csv")
    )
    indexer = EvidenceIndexer(dataset_dir=dataset_dir, resolver=resolver)
    auditor = RefinedAuditor(indexer=indexer, resolver=resolver, dataset_dir=dataset_dir)

    user = resolver.resolve_by_email(req["email"])
    status, steps = auditor.audit_case(
        case_id=req["case_id"],
        email=req["email"],
        requested_at=req["requested_at"],
        reported_status=req["reported_status"],
        reported_at=req["reported_at"],
        audit_at=req["audit_at"],
        request_text=req["request_text"]
    )

    print("\n" + "-" * 60)
    print(f"[CASE INFO] {req['case_id']}")
    print("-" * 60)
    print(f"  * Email:           {req['email']}")
    print(f"  * User ID:         {user.user_id if user else 'Unknown'}")
    print(f"  * User Name:       {user.name if user else 'Unknown'}")
    if user and user.historical_emails:
        print(f"  * Historical Emails: {list(user.historical_emails)}")
    if user and user.historical_phones:
        print(f"  * Historical Phones: {list(user.historical_phones)}")
    print(f"  * Requested At:    {req['requested_at']}")
    print(f"  * Reported Status: {req['reported_status']} at {req['reported_at']}")
    print(f"  * Audit At:        {req['audit_at']}")
    print(f"  * Request Text:    \"{req['request_text']}\"")

    print("\n" + "-" * 60)
    print(f"[AUDIT VERDICT] {status}")
    print("-" * 60)
    print(f"  Total Steps Generated: {len(steps)}")

    if not steps:
        print("  (Empty steps array - Non-deletion / NOT_APPLICABLE request)")
    else:
        print("\n  Step | Phase        | System             | Resource           | State      | Evidence")
        print("  " + "-" * 78)
        for s in steps:
            s_no = s.get("step_no", 0)
            phase = s.get("phase", "")
            sys_id = s.get("system_id", "")
            res_id = s.get("resource_id", "")
            state = s.get("state", "")
            ev = s.get("evidence_id", "") or "-"
            print(f"  {s_no:4d} | {phase:12s} | {sys_id:18s} | {res_id:18s} | {state:10s} | {ev}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else None
    inspect(cid)
