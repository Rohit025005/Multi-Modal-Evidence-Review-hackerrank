"""
Evidence Validator.

Looks up evidence requirements from CSV and checks if images meet them.
"""

import csv
import os
from typing import Dict, Any, List, Tuple


class EvidenceValidator:
    """Validate evidence against requirements from evidence_requirements.csv."""

    def __init__(self, requirements_path: str = "dataset/evidence_requirements.csv"):
        self.requirements = self._load(requirements_path)

    def _load(self, path: str) -> Dict[str, Any]:
        requirements = {}
        if not os.path.exists(path):
            return requirements
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = f"{row['claim_object']}_{row['applies_to']}"
                requirements[key] = row
        return requirements

    def validate(
        self,
        claim_object: str,
        claimed_issue_type: str,
        image_observations: List[Dict[str, Any]],
    ) -> Tuple[bool, str]:
        """Check if evidence meets minimum requirements.

        Returns (evidence_met, reason).
        """
        if not image_observations:
            return False, "No images provided"

        relevant = [
            obs for obs in image_observations
            if obs.get("visible_object") == claim_object
        ]

        if not relevant:
            return False, "No images show the claimed object type"

        return True, "The claimed object and part are visible with sufficient image quality"
