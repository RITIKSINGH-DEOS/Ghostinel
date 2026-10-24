import sys
sys.path.insert(0, '.')
import csv
import json
from code.evidence_indexer import EvidenceIndexer
from code.identity_resolver import IdentityResolver
from code.refined_auditor import RefinedAuditor
from code.evaluation.evaluator import evaluate_predictions

print("Initializing Ghostinel Refined Auditor...")
indexer = EvidenceIndexer()
resolver = IdentityResolver()
auditor = RefinedAuditor(indexer, resolver)

pred_file = "sample_predictions.csv"

with open("dataset/sample_deletion_requests.csv", mode="r", encoding="utf-8") as in_f, \
     open(pred_file, mode="w", newline="", encoding="utf-8") as out_f:
    
    reader = csv.DictReader(in_f)
    writer = csv.writer(out_f)
    writer.writerow(["case_id", "deletion_status", "steps_json"])
    
    for row in reader:
        status, steps = auditor.audit_case(
            case_id=row["case_id"],
            email=row["email"],
            requested_at=row["requested_at"],
            reported_status=row["reported_status"],
            reported_at=row["reported_at"],
            audit_at=row["audit_at"],
            request_text=row["request_text"]
        )
        writer.writerow([row["case_id"], status, json.dumps(steps, separators=(',', ':'))])

print("Running evaluation against sample_output.csv...")
results = evaluate_predictions("dataset/sample_output.csv", pred_file)

print("\n" + "="*40)
print(f"Status Accuracy:   {results['status_accuracy_pct']:.2f}% ({results['status_matches']}/{results['total_cases']})")
print(f"Sequence Accuracy: {results['sequence_accuracy_pct']:.2f}% ({results['step_exact_matches']}/{results['total_cases']})")
print(f"Field Accuracy:    {results['field_accuracy_pct']:.2f}%")
print("="*40)

# Print case comparisons
for cid, det in results["case_details"].items():
    status_str = "MATCH" if det.get("status_match") else "DIFF"
    seq_str = "MATCH" if det.get("seq_match") else "DIFF"
    print(f"Case {cid:<8}: status={status_str:<5} | seq={seq_str:<5} | GT steps={det.get('gt_steps')} | Pred steps={det.get('pred_steps')}")
