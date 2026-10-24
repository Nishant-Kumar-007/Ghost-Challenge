"""Deletion Policy Evaluator.

Applies deletion_rules.csv to determine the compliant state, required operations,
and whether a case is COMPLETE, INCOMPLETE, or NOT_APPLICABLE.
"""

import os
from typing import Dict, List, Optional
import pandas as pd


class PolicyEvaluator:
    """Evaluates resources and observations against deletion_rules.csv."""

    def __init__(self, dataset_dir: str = "dataset"):
        self.rules_path = os.path.join(dataset_dir, "deletion_rules.csv")
        self.rules: Dict[str, Dict[str, str]] = {}
        self._load_rules()

    def _load_rules(self) -> None:
        if not os.path.exists(self.rules_path):
            return
        df = pd.read_csv(self.rules_path)
        for _, r in df.iterrows():
            cat = str(r["data_category"]).strip()
            self.rules[cat] = {
                "rule_id": str(r["rule_id"]).strip(),
                "condition": str(r["condition"]).strip(),
                "required_action": str(r["required_action"]).strip().upper(),
            }

    def get_required_action(self, data_category: str) -> str:
        """Returns DELETE, REDACT, ANONYMIZE, or RETAIN."""
        rule = self.rules.get(data_category)
        if rule:
            return rule["required_action"]
        # Defaults based on challenge spec
        defaults = {
            "USER_PROFILE": "DELETE",
            "SECONDARY_IDENTIFIER": "DELETE",
            "SEARCH_INDEX_ENTRY": "DELETE",
            "CACHE_ENTRY": "DELETE",
            "SUPPORT_MESSAGE": "REDACT",
            "SUPPORT_ATTACHMENT": "DELETE",
            "ANALYTICS_PROFILE": "ANONYMIZE",
            "PRODUCT_TELEMETRY": "ANONYMIZE",
            "USER_EXPORT": "DELETE",
            "MARKETING_PROFILE": "DELETE",
            "EMAIL_DELIVERY_LOG": "REDACT",
            "SECURITY_AUDIT_LOG": "RETAIN",
            "LEGAL_HOLD_RECORD": "RETAIN",
            "BACKUP_ARCHIVE": "RETAIN",
            "ACCOUNT_TOMBSTONE": "REDACT",
            "DATA_FLOW": "DISABLE",
        }
        return defaults.get(data_category, "DELETE")
