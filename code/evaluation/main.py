"""
Ghostinel - Evaluation Entry Point.
Executes quantitative evaluation between predictions and ground-truth sample answers.
"""
import os
import sys
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from code.evaluation.evaluator import evaluate_predictions


def main():
    parser = argparse.ArgumentParser(description="Ghostinel Evaluation Runner")
    parser.add_argument("--ground-truth", default="dataset/sample_output.csv", help="Path to ground truth CSV")
    parser.add_argument("--predictions", default="sample_predictions.csv", help="Path to predictions CSV")
    args = parser.parse_args()

    if not os.path.exists(args.ground_truth):
        print(f"Ground truth not found: {args.ground_truth}")
        sys.exit(1)
    if not os.path.exists(args.predictions):
        print(f"Predictions not found: {args.predictions}")
        sys.exit(1)

    print(f"Evaluating {args.predictions} against {args.ground_truth}...")
    metrics = evaluate_predictions(args.ground_truth, args.predictions)

    print("\n" + "=" * 40)
    print(f"Status Accuracy:   {metrics['status_accuracy_pct']:.2f}% ({metrics['status_matches']}/{metrics['total_cases']})")
    print(f"Sequence Accuracy: {metrics['sequence_accuracy_pct']:.2f}% ({metrics['step_exact_matches']}/{metrics['total_cases']})")
    print(f"Field Accuracy:    {metrics['field_accuracy_pct']:.2f}%")
    print("=" * 40)


if __name__ == "__main__":
    main()
