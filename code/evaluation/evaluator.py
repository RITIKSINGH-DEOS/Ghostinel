"""
Evaluator for Ghostinel Deletion Audit Agent.
Evaluates predictions against sample_output.csv or canonical ground truth.
"""
import csv
import json
from typing import Dict, List, Tuple, Any


def evaluate_predictions(ground_truth_path: str, predictions_path: str) -> Dict[str, Any]:
    with open(ground_truth_path, mode="r", encoding="utf-8") as f:
        gt_rows = {r["case_id"]: r for r in csv.DictReader(f)}

    with open(predictions_path, mode="r", encoding="utf-8") as f:
        pred_rows = {r["case_id"]: r for r in csv.DictReader(f)}

    total_cases = len(gt_rows)
    status_matches = 0
    step_exact_matches = 0
    total_gt_steps = 0
    matched_steps = 0
    field_matches = 0
    total_fields = 0

    case_details = {}

    for cid, gt in gt_rows.items():
        if cid not in pred_rows:
            case_details[cid] = {"status_match": False, "error": "Missing prediction"}
            continue

        pred = pred_rows[cid]
        s_match = (gt["deletion_status"] == pred["deletion_status"])
        if s_match:
            status_matches += 1

        try:
            gt_steps = json.loads(gt["steps_json"])
            pred_steps = json.loads(pred["steps_json"])
        except Exception as e:
            case_details[cid] = {"status_match": s_match, "error": f"JSON decode error: {e}"}
            continue

        total_gt_steps += len(gt_steps)
        seq_match = True

        if len(gt_steps) == len(pred_steps):
            for i in range(len(gt_steps)):
                g = gt_steps[i]
                p = pred_steps[i]
                # Compare fields: phase, operation, system_id, resource_id, state, evidence_id
                fields = ["phase", "operation", "system_id", "resource_id", "state", "evidence_id"]
                step_match = True
                for fld in fields:
                    total_fields += 1
                    if g.get(fld, "") == p.get(fld, ""):
                        field_matches += 1
                    else:
                        step_match = False
                        seq_match = False

                if step_match:
                    matched_steps += 1
            if seq_match:
                step_exact_matches += 1
        else:
            seq_match = False
            # Still count partial field matches
            for i in range(min(len(gt_steps), len(pred_steps))):
                g = gt_steps[i]
                p = pred_steps[i]
                for fld in ["phase", "operation", "system_id", "resource_id", "state", "evidence_id"]:
                    total_fields += 1
                    if g.get(fld, "") == p.get(fld, ""):
                        field_matches += 1

        case_details[cid] = {
            "status_match": s_match,
            "seq_match": seq_match,
            "gt_steps": len(gt_steps),
            "pred_steps": len(pred_steps),
        }

    status_acc = (status_matches / total_cases) * 100 if total_cases else 0
    seq_acc = (step_exact_matches / total_cases) * 100 if total_cases else 0
    field_acc = (field_matches / total_fields) * 100 if total_fields else 0

    return {
        "total_cases": total_cases,
        "status_accuracy_pct": status_acc,
        "sequence_accuracy_pct": seq_acc,
        "field_accuracy_pct": field_acc,
        "status_matches": status_matches,
        "step_exact_matches": step_exact_matches,
        "case_details": case_details,
    }


if __name__ == "__main__":
    import sys
    gt = sys.argv[1] if len(sys.argv) > 1 else "dataset/sample_output.csv"
    pred = sys.argv[2] if len(sys.argv) > 2 else "dataset/sample_output.csv"
    res = evaluate_predictions(gt, pred)
    print(f"Status Accuracy: {res['status_accuracy_pct']:.2f}% ({res['status_matches']}/{res['total_cases']})")
    print(f"Sequence Accuracy: {res['sequence_accuracy_pct']:.2f}% ({res['step_exact_matches']}/{res['total_cases']})")
    print(f"Field Accuracy: {res['field_accuracy_pct']:.2f}%")
