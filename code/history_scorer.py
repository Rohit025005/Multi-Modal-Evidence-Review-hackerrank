"""
History Scorer.

Loads user history from CSV and returns risk flags.
"""

import csv
import os
from typing import Dict, Any, List, Tuple


class HistoryScorer:
    """Score user history and return risk flags."""

    def __init__(self, history_path: str = "dataset/user_history.csv"):
        self.history_data = self._load(history_path)

    def _load(self, path: str) -> Dict[str, Any]:
        history = {}
        if not os.path.exists(path):
            return history
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                history[row["user_id"]] = row
        return history

    def score(self, user_id: str) -> Tuple[List[str], str]:
        """Return (risk_flags, history_summary) for a user."""
        if user_id not in self.history_data:
            return [], "No history available"

        user = self.history_data[user_id]
        flags = []

        history_flags_raw = user.get("history_flags", "").strip()
        if history_flags_raw and history_flags_raw != "none":
            for f in history_flags_raw.split(";"):
                f = f.strip()
                if f and f not in flags:
                    flags.append(f)

        try:
            rejected = int(user.get("rejected_claim", 0))
            if rejected > 0 and "user_history_risk" not in flags:
                flags.append("user_history_risk")
        except (ValueError, TypeError):
            pass

        try:
            manual = int(user.get("manual_review_claim", 0))
            if manual > 0 and "manual_review_required" not in flags:
                flags.append("manual_review_required")
        except (ValueError, TypeError):
            pass

        summary = user.get("history_summary", "No history available")
        return flags, summary
