"""
Evaluation Framework.

Compares system predictions against expected outputs in sample_claims.csv.
"""

import csv
import sys
import os
from typing import Dict, Any, List


FIELD_NAMES = [
    "claim_status", "issue_type", "object_part", "severity",
    "evidence_standard_met",
]


def load_csv(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def evaluate(predictions_path: str, expected_path: str):
    """Evaluate predictions against expected outputs."""
    predictions = load_csv(predictions_path)
    expected = load_csv(expected_path)

    if len(predictions) != len(expected):
        print(f"ERROR: {len(predictions)} predictions vs {len(expected)} expected")
        return

    print(f"Evaluating {len(predictions)} samples\n")

    metrics = {}
    for field in FIELD_NAMES:
        metrics[field] = {"correct": 0, "total": len(predictions), "failures": []}

    for i, (pred, exp) in enumerate(zip(predictions, expected)):
        user_id = pred.get("user_id", f"row_{i}")

        for field in FIELD_NAMES:
            pred_val = str(pred.get(field, "")).strip().lower()
            exp_val = str(exp.get(field, "")).strip().lower()

            if field == "evidence_standard_met":
                pred_val = pred_val == "true"
                exp_val = exp_val == "true"

            if pred_val == exp_val:
                metrics[field]["correct"] += 1
            else:
                metrics[field]["failures"].append({
                    "user_id": user_id,
                    "expected": exp.get(field, ""),
                    "got": pred.get(field, ""),
                })

    print("=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)

    for field in FIELD_NAMES:
        m = metrics[field]
        acc = (m["correct"] / m["total"]) * 100 if m["total"] > 0 else 0
        print(f"\n{field}: {m['correct']}/{m['total']} = {acc:.1f}%")

        if m["failures"]:
            for f in m["failures"]:
                print(f"  FAIL: {f['user_id']}")
                print(f"    Expected: {f['expected']}")
                print(f"    Got:      {f['got']}")

    overall_correct = 0
    overall_total = 0
    for field in FIELD_NAMES:
        overall_correct += metrics[field]["correct"]
        overall_total += metrics[field]["total"]

    overall_acc = (overall_correct / overall_total) * 100 if overall_total > 0 else 0
    print(f"\n{'=' * 60}")
    print(f"OVERALL: {overall_correct}/{overall_total} = {overall_acc:.1f}%")
    print(f"{'=' * 60}")


def main():
    predictions_path = "output_sample.csv"
    expected_path = "dataset/sample_claims.csv"

    if len(sys.argv) > 1:
        predictions_path = sys.argv[1]
    if len(sys.argv) > 2:
        expected_path = sys.argv[2]

    if not os.path.exists(predictions_path):
        print(f"Predictions file not found: {predictions_path}")
        print("Run the system first: python main.py")
        return

    evaluate(predictions_path, expected_path)


if __name__ == "__main__":
    main()
