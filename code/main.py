"""
Damage Claim Verification System - Main Pipeline.

Architecture:
  - Gemini perception: conversation + images -> structured observations (1 call per claim)
  - Deterministic decisions: evidence, claim_status, risk_flags, severity, justification

Modes:
  - Batch: python main.py [--input CSV] [--output CSV]
  - Debug: python main.py --debug USER_ID [--input CSV]
"""

import csv
import os
import sys
import json
import time
import argparse
from typing import Dict, Any, List

from gemini_client import GeminiClient
from perception import unified_perceive
from decision_engine import (
    decide_claim_status,
    collect_risk_flags,
    determine_severity,
    determine_supporting_images,
    determine_valid_image,
    build_justification,
    resolve_output_fields,
)
from evidence_validator import EvidenceValidator
from history_scorer import HistoryScorer


FIELDNAMES = [
    "user_id", "image_paths", "user_claim", "claim_object",
    "evidence_standard_met", "evidence_standard_met_reason",
    "risk_flags", "issue_type", "object_part", "claim_status",
    "claim_status_justification", "supporting_image_ids", "valid_image",
    "severity",
]


class DamageClaimSystem:
    """Main damage claim verification pipeline.

    Uses unified perception (1 Gemini call per claim) + deterministic decisions.
    """

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        print(f"Initializing Gemini client with model: {model_name}")
        self.gemini = GeminiClient(model_name=model_name)
        self.evidence_validator = EvidenceValidator()
        self.history_scorer = HistoryScorer()
        self.claim_count = 0
        self.api_calls = 0
        self.rate_limited = False

    def process_claim(self, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single claim through the unified pipeline.

        One Gemini call (perception) + deterministic decisions.
        """
        self.claim_count += 1
        user_id = claim_data.get("user_id", "unknown")
        print(f"\n--- Processing claim {self.claim_count}: {user_id} ---")

        image_paths_raw = claim_data.get("image_paths", "")
        image_paths = [
            p.strip() for p in image_paths_raw.split(";") if p.strip()
        ]

        claim_text = claim_data.get("user_claim", "")
        claim_object = claim_data.get("claim_object", "unknown")

        # Step 1: Unified Gemini perception (1 call for all images + conversation)
        print("  [1/3] Gemini perception (conversation + images)...")
        extracted_claim, image_observations = unified_perceive(
            self.gemini, claim_text, image_paths, claim_object, user_id
        )
        self.api_calls += 1
        print(f"    Claimed issue: {extracted_claim.get('claimed_issue_type')}")
        print(f"    Claimed part:  {extracted_claim.get('claimed_object_part')}")
        for obs in image_observations:
            img_id = obs.get("image_id", "?")
            summary = obs.get("observation_summary", "no summary")[:80]
            print(f"    {img_id}: {summary}")

        # Step 2: Evidence validation
        print("  [2/3] Deterministic decisions...")
        evidence_met, evidence_reason = self.evidence_validator.validate(
            claim_object,
            extracted_claim.get("claimed_issue_type", "none"),
            image_observations,
        )
        print(f"    evidence_met: {evidence_met} - {evidence_reason}")

        history_flags, history_summary = self.history_scorer.score(user_id)

        claim_status, claim_justification = decide_claim_status(
            extracted_claim, image_observations, evidence_met
        )

        risk_flags = collect_risk_flags(
            image_observations, extracted_claim, history_flags
        )

        severity = determine_severity(
            image_observations,
            claimed_severity=extracted_claim.get("claimed_severity", "unknown"),
            claim_status=claim_status,
            claimed_issue_type=extracted_claim.get("claimed_issue_type", "unknown"),
        )

        issue_type, object_part, severity = resolve_output_fields(
            claim_status, extracted_claim, image_observations, severity
        )

        supporting_images = determine_supporting_images(
            image_observations, extracted_claim, claim_status,
            resolved_issue_type=issue_type,
            resolved_object_part=object_part,
        )

        valid_image = determine_valid_image(image_observations)

        final_justification = build_justification(
            claim_status, extracted_claim, image_observations
        )

        result = {
            "user_id": user_id,
            "image_paths": image_paths_raw,
            "user_claim": claim_text,
            "claim_object": claim_object,
            "evidence_standard_met": evidence_met,
            "evidence_standard_met_reason": evidence_reason,
            "risk_flags": ";".join(risk_flags) if risk_flags else "none",
            "issue_type": issue_type,
            "object_part": object_part,
            "claim_status": claim_status,
            "claim_status_justification": final_justification,
            "supporting_image_ids": supporting_images,
            "valid_image": valid_image,
            "severity": severity,
        }

        print(f"    -> claim_status: {claim_status}")
        print(f"    -> severity: {severity}")
        print(f"    -> supporting: {supporting_images}")

        return result


def load_existing_results(output_path: str) -> int:
    """Return number of rows already processed (output is append-only, preserves input order)."""
    if not os.path.exists(output_path):
        return 0
    with open(output_path, "r", encoding="utf-8-sig") as f:
        lines = sum(1 for _ in f)
    return max(0, lines - 1)  # subtract header


def append_result(output_path: str, result: Dict[str, Any]):
    """Append a single result to output CSV (create with header if needed)."""
    file_exists = os.path.exists(output_path) and os.path.getsize(output_path) > 0
    mode = "a" if file_exists else "w"
    with open(output_path, mode, newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(result)


def find_claim_by_id(claims_path: str, user_id: str) -> Dict[str, Any]:
    """Find a specific claim by user_id from CSV."""
    with open(claims_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("user_id") == user_id:
                return row
    return {}


def run_debug(system: DamageClaimSystem, claims_path: str, user_id: str):
    """Debug mode: process one claim and show detailed output."""
    row = find_claim_by_id(claims_path, user_id)
    if not row:
        print(f"ERROR: user_id '{user_id}' not found in {claims_path}")
        sys.exit(1)

    # Load expected if available (sample_claims.csv has expected outputs)
    expected = {}
    has_expected = False
    try:
        with open(claims_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r.get("user_id") == user_id:
                    expected = r
                    has_expected = "claim_status" in expected and expected.get("claim_status", "") != ""
                    break
    except Exception:
        pass

    result = system.process_claim(row)

    print(f"\n{'='*60}")
    print(f"DEBUG OUTPUT for {user_id}")
    print(f"{'='*60}")
    print(f"\nINPUT:")
    print(f"  Conversation: {row.get('user_claim', '')[:120]}...")
    print(f"  Images: {row.get('image_paths', '')}")
    print(f"  Claim object: {row.get('claim_object', '')}")

    print(f"\nDETERMINISTIC DECISIONS:")
    print(f"  evidence_standard_met: {result['evidence_standard_met']}")
    print(f"  evidence_standard_met_reason: {result['evidence_standard_met_reason']}")
    print(f"  claim_status: {result['claim_status']}")
    print(f"  issue_type: {result['issue_type']}")
    print(f"  object_part: {result['object_part']}")
    print(f"  severity: {result['severity']}")
    print(f"  supporting_image_ids: {result['supporting_image_ids']}")
    print(f"  valid_image: {result['valid_image']}")
    print(f"  risk_flags: {result['risk_flags']}")
    print(f"  justification: {result['claim_status_justification']}")

    if has_expected:
        print(f"\nEXPECTED (from CSV):")
        print(f"  claim_status: {expected.get('claim_status', '')}")
        print(f"  issue_type: {expected.get('issue_type', '')}")
        print(f"  object_part: {expected.get('object_part', '')}")
        print(f"  severity: {expected.get('severity', '')}")
        print(f"  evidence_standard_met: {expected.get('evidence_standard_met', '')}")
        print(f"  risk_flags: {expected.get('risk_flags', '')}")

        print(f"\nCOMPARISON:")
        compare_fields = ["claim_status", "issue_type", "object_part", "severity", "evidence_standard_met"]
        for field in compare_fields:
            exp_val = expected.get(field, "").strip().lower()
            got_val = str(result.get(field, "")).strip().lower()
            if field == "evidence_standard_met":
                got_val = str(result.get("evidence_standard_met", "")).lower()
            match = "OK" if exp_val == got_val else "MISMATCH"
            print(f"  {field:25s} expected={exp_val:20s} got={got_val:20s} [{match}]")
    else:
        print(f"\n(No expected values in CSV for comparison)")

    return result


def run_batch(system: DamageClaimSystem, claims_path: str, output_path: str):
    """Batch mode: process all claims, resumable."""
    print(f"Claims file: {claims_path}")
    print(f"Output file: {output_path}")

    existing_count = load_existing_results(output_path)
    print(f"Already processed: {existing_count} claims")

    with open(claims_path, "r", encoding="utf-8-sig") as f:
        all_claims = list(csv.DictReader(f))

    remaining = all_claims[existing_count:]
    print(f"Remaining to process: {len(remaining)} claims")

    if not remaining:
        print("All claims already processed!")
        return

    start_time = time.time()
    processed_this_run = 0

    for row in remaining:
        try:
            result = system.process_claim(row)
            append_result(output_path, result)
            processed_this_run += 1
            print(f"  [saved] {result['user_id']} -> {output_path}")
        except Exception as e:
            is_rate_limit = "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e)
            if is_rate_limit:
                print(f"\n  [RATE LIMIT] Quota exhausted. Processed {processed_this_run} claims this run.")
                print(f"  [RATE LIMIT] Run again later to continue from where we left off.")
                system.rate_limited = True
                break
            else:
                print(f"\n  [ERROR] {e}")
                raise

    elapsed = time.time() - start_time
    total_done = existing_count + processed_this_run
    print(f"\n=== Run complete ===")
    print(f"Claims processed this run: {processed_this_run}")
    print(f"Total claims processed: {total_done}/{len(all_claims)}")
    print(f"Gemini API calls this run: {system.api_calls}")
    print(f"Elapsed: {elapsed:.1f}s")


def main():
    parser = argparse.ArgumentParser(
        description="Damage Claim Verification System"
    )
    parser.add_argument(
        "--debug", metavar="USER_ID",
        help="Debug mode: process one claim and show detailed comparison"
    )
    parser.add_argument(
        "--input", default="dataset/sample_claims.csv",
        help="Input claims CSV (default: dataset/sample_claims.csv)"
    )
    parser.add_argument(
        "--output", default=None,
        help="Output CSV path (default: output_sample.csv or output.csv based on input)"
    )
    parser.add_argument(
        "--model", default="gemini-2.5-flash",
        help="Gemini model name (default: gemini-2.5-flash)"
    )
    args = parser.parse_args()

    # Default output path based on input
    if args.output is None:
        if "sample" in args.input:
            args.output = "output_sample.csv"
        else:
            args.output = "output.csv"

    system = DamageClaimSystem(model_name=args.model)

    if args.debug:
        run_debug(system, args.input, args.debug)
    else:
        run_batch(system, args.input, args.output)


if __name__ == "__main__":
    main()
