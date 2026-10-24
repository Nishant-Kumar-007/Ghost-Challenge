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

    def evaluate_compliance(
        self,
        data_category: str,
        observed_state: str,
    ) -> Dict[str, Any]:
        """Evaluates whether an observed resource state satisfies deletion policy.

        Returns a dictionary containing compliance status, required operations,
        and target states.
        """
        req_action = self.get_required_action(data_category)

        # 1. Categories requiring deletion
        if data_category in [
            "USER_PROFILE", "SECONDARY_IDENTIFIER", "SEARCH_INDEX_ENTRY",
            "CACHE_ENTRY", "USER_EXPORT", "MARKETING_PROFILE", "SUPPORT_ATTACHMENT"
        ]:
            if observed_state == "PRESENT":
                return {
                    "is_compliant": False,
                    "required_action": "DELETE",
                    "finding": {"operation": "REPORT_REMAINING_RECORD", "state": "PRESENT"},
                    "remediation": {"operation": "DELETE_RECORD", "state": "ABSENT"},
                    "verification": {"operation": "VERIFY_RECORD_ABSENT", "state": "ABSENT"},
                }
            else:
                return {
                    "is_compliant": True,
                    "required_action": "DELETE",
                    "finding": None,
                    "remediation": None,
                    "verification": {"operation": "VERIFY_RECORD_ABSENT", "state": "ABSENT"},
                }

        # 2. Categories requiring redaction (support messages, delivery logs, account tombstones)
        elif data_category in ["SUPPORT_MESSAGE", "EMAIL_DELIVERY_LOG", "ACCOUNT_TOMBSTONE"]:
            if observed_state == "PRESENT":
                return {
                    "is_compliant": False,
                    "required_action": "REDACT",
                    "finding": {"operation": "REPORT_EXPOSED_PII", "state": "PRESENT"},
                    "remediation": {"operation": "REDACT_RECORD", "state": "REDACTED"},
                    "verification": {"operation": "VERIFY_RECORD_REDACTED", "state": "REDACTED"},
                }
            else:
                return {
                    "is_compliant": True,
                    "required_action": "REDACT",
                    "finding": None,
                    "remediation": None,
                    "verification": {"operation": "VERIFY_RECORD_REDACTED", "state": "REDACTED"},
                }

        # 3. Categories requiring anonymization (analytics profiles, product telemetry)
        elif data_category in ["ANALYTICS_PROFILE", "PRODUCT_TELEMETRY"]:
            if observed_state == "PRESENT":
                return {
                    "is_compliant": False,
                    "required_action": "ANONYMIZE",
                    "finding": {"operation": "REPORT_EXPOSED_PII", "state": "PRESENT"},
                    "remediation": {"operation": "ANONYMIZE_RECORD", "state": "ANONYMIZED"},
                    "verification": {"operation": "VERIFY_RECORD_ANONYMIZED", "state": "ANONYMIZED"},
                }
            else:
                return {
                    "is_compliant": True,
                    "required_action": "ANONYMIZE",
                    "finding": None,
                    "remediation": None,
                    "verification": {"operation": "VERIFY_RECORD_ANONYMIZED", "state": "ANONYMIZED"},
                }

        # 4. Active data flow processes
        elif data_category in ["DATA_FLOW"]:
            if observed_state == "ACTIVE":
                return {
                    "is_compliant": False,
                    "required_action": "DISABLE",
                    "finding": {"operation": "REPORT_ACTIVE_DATA_FLOW", "state": "ACTIVE"},
                    "remediation": {"operation": "DISABLE_DATA_FLOW", "state": "DISABLED"},
                    "verification": {"operation": "VERIFY_DATA_FLOW_DISABLED", "state": "DISABLED"},
                }
            else:
                return {
                    "is_compliant": True,
                    "required_action": "DISABLE",
                    "finding": None,
                    "remediation": None,
                    "verification": {"operation": "VERIFY_DATA_FLOW_DISABLED", "state": "DISABLED"},
                }

        # 5. Backup archives / restore risks
        elif data_category in ["BACKUP_ARCHIVE"]:
            if observed_state == "ACTIVE":
                return {
                    "is_compliant": False,
                    "required_action": "BLOCK",
                    "finding": {"operation": "REPORT_RESTORE_RISK", "state": "ACTIVE"},
                    "remediation": {"operation": "BLOCK_RESTORE", "state": "BLOCKED"},
                    "verification": {"operation": "VERIFY_RESTORE_BLOCKED", "state": "BLOCKED"},
                }
            else:
                return {
                    "is_compliant": True,
                    "required_action": "BLOCK",
                    "finding": None,
                    "remediation": None,
                    "verification": {"operation": "VERIFY_RESTORE_BLOCKED", "state": "BLOCKED"},
                }

        # 6. Categories requiring retention (security audit logs, legal hold records)
        elif data_category in ["SECURITY_AUDIT_LOG", "LEGAL_HOLD_RECORD"]:
            return {
                "is_compliant": True,
                "required_action": "RETAIN",
                "finding": None,
                "remediation": None,
                "verification": {"operation": "VERIFY_RECORD_PRESENT", "state": "PRESENT"},
            }

        # Default fallback
        return {
            "is_compliant": observed_state == "ABSENT",
            "required_action": "DELETE",
            "finding": {"operation": "REPORT_REMAINING_RECORD", "state": "PRESENT"} if observed_state == "PRESENT" else None,
            "remediation": {"operation": "DELETE_RECORD", "state": "ABSENT"} if observed_state == "PRESENT" else None,
            "verification": {"operation": "VERIFY_RECORD_ABSENT", "state": "ABSENT"},
        }

