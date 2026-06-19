"""Test single claim (user_001) end-to-end through the full pipeline."""

import sys
import os
import csv
import json

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gemini_client import GeminiClient
from claim_extractor import extract_claim
from image_analyzer import analyze_image
from decision_engine import (
    decide_claim_status,
    collect_risk_flags,
    determine_severity,
    determine_supporting_images,
    determine_valid_image,
    build_justification,
)
from evidence_validator import EvidenceValidator
from history_scorer import HistoryScorer

SAMPLE_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dataset", "sample_claims.csv")


def find_image_path(img_ref):
    """Resolve image path from CSV reference."""
    candidates = [
        img_ref,
        os.path.join("dataset", img_ref),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dataset", img_ref),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def run_test(user_id_filter="user_001"):
    # Load expected
    with open(SAMPLE_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)

    row = None
    for r in all_rows:
        if r["user_id"] == user_id_filter:
            row = r
            break

    if not row:
        print(f"ERROR: {user_id_filter} not found in sample_claims.csv")
        return

    print(f"=== Testing {user_id_filter} ===\n")
    print(f"Claim object: {row['claim_object']}")
    print(f"Claim text: {row['user_claim'][:120]}...")
    print(f"Image paths: {row['image_paths']}")
    print()

    # Expected values
    expected = {
        "claim_status": row["claim_status"],
        "issue_type": row["issue_type"],
        "object_part": row["object_part"],
        "severity": row["severity"],
        "evidence_standard_met": row["evidence_standard_met"],
        "risk_flags": row["risk_flags"],
        "supporting_image_ids": row["supporting_image_ids"],
        "valid_image": row["valid_image"],
        "claim_status_justification": row["claim_status_justification"],
    }

    # Init
    client = GeminiClient(model_name="gemini-2.5-flash")
    evidence_validator = EvidenceValidator()
    history_scorer = HistoryScorer()

    # Step 1: Extract claim
    print("--- Step 1: Claim Extraction ---")
    extracted = extract_claim(client, row["user_claim"], row["claim_object"])
    print(json.dumps(extracted, indent=2))
    print()

    # Step 2: Analyze images
    print("--- Step 2: Image Analysis ---")
    image_paths = [p.strip() for p in row["image_paths"].split(";") if p.strip()]
    observations = []
    for img_ref in image_paths:
        full_path = find_image_path(img_ref)
        if not full_path:
            print(f"  WARNING: Image not found: {img_ref}")
            continue
        print(f"  Analyzing: {img_ref} ({os.path.getsize(full_path)} bytes)")
        obs = analyze_image(
            client, full_path,
            extracted.get("claim_object", row["claim_object"]),
            extracted.get("claim_description", ""),
            extracted.get("claimed_object_part", "unknown"),
            extracted.get("claimed_issue_type", "none"),
        )
        image_id = os.path.splitext(os.path.basename(img_ref))[0]
        obs["image_id"] = image_id
        obs["image_path"] = img_ref
        observations.append(obs)
        print(f"    Object: {obs.get('visible_object')}")
        print(f"    Parts: {obs.get('visible_parts')}")
        for d in obs.get("visible_damage", []):
            print(f"    Damage: {d.get('issue_type')} on {d.get('part')} ({d.get('estimated_severity')})")
        print(f"    Quality: blur={obs.get('image_quality',{}).get('is_blurry')} "
              f"angle={obs.get('image_quality',{}).get('is_wrong_angle')} "
              f"relevant={obs.get('image_quality',{}).get('is_relevant_to_claim')}")
        print(f"    Summary: {obs.get('observation_summary','')[:120]}")
        print()

    # Step 3: Evidence validation
    print("--- Step 3: Evidence Validation ---")
    evidence_met, evidence_reason = evidence_validator.validate(
        row["claim_object"], extracted.get("claimed_issue_type", "none"), observations
    )
    print(f"  Met: {evidence_met}")
    print(f"  Reason: {evidence_reason}")
    print()

    # Step 4: History
    print("--- Step 4: History Scoring ---")
    history_flags, history_summary = history_scorer.score(row["user_id"])
    print(f"  Flags: {history_flags}")
    print(f"  Summary: {history_summary}")
    print()

    # Step 5: Decision
    print("--- Step 5: Decision Engine ---")
    claim_status, justification = decide_claim_status(extracted, observations, evidence_met)
    risk_flags = collect_risk_flags(observations, extracted, history_flags)
    severity = determine_severity(
        observations,
        claimed_severity=extracted.get("claimed_severity", "unknown"),
        claim_status=claim_status,
        claimed_issue_type=extracted.get("claimed_issue_type", "unknown"),
    )
    supporting = determine_supporting_images(observations, extracted, claim_status)
    valid = determine_valid_image(observations)
    final_justification = build_justification(claim_status, extracted, observations)

    # Build result
    result = {
        "claim_status": claim_status,
        "issue_type": extracted.get("claimed_issue_type", "none"),
        "object_part": extracted.get("claimed_object_part", "unknown"),
        "severity": severity,
        "evidence_standard_met": str(evidence_met).lower(),
        "risk_flags": ";".join(risk_flags) if risk_flags else "none",
        "supporting_image_ids": supporting,
        "valid_image": str(valid).lower(),
        "claim_status_justification": final_justification,
    }

    print(f"  claim_status: {result['claim_status']}")
    print(f"  issue_type: {result['issue_type']}")
    print(f"  object_part: {result['object_part']}")
    print(f"  severity: {result['severity']}")
    print(f"  evidence_standard_met: {result['evidence_standard_met']}")
    print(f"  risk_flags: {result['risk_flags']}")
    print(f"  supporting_image_ids: {result['supporting_image_ids']}")
    print(f"  valid_image: {result['valid_image']}")
    print(f"  justification: {final_justification[:150]}")
    print()

    # Step 6: Compare
    print("=== COMPARISON WITH EXPECTED ===")
    print(f"{'Field':<30} {'Expected':<25} {'Got':<25} {'Match'}")
    print("-" * 105)
    compare_fields = ["claim_status", "issue_type", "object_part", "severity", "evidence_standard_met", "valid_image"]
    for field in compare_fields:
        exp_val = expected[field]
        got_val = result[field]
        # Special handling for evidence_standard_met
        if field == "evidence_standard_met":
            exp_val = exp_val.lower()
            got_val = got_val.lower()
        match = "YES" if exp_val == got_val else "NO"
        print(f"  {field:<28} {exp_val:<25} {got_val:<25} {match}")

    # Justification comparison (fuzzy)
    exp_just = expected["claim_status_justification"].lower()[:50]
    got_just = result["claim_status_justification"].lower()[:50]
    print(f"\n  Justification (first 50 chars):")
    print(f"    Expected: {exp_just}")
    print(f"    Got:      {got_just}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "user_001"
    run_test(target)
