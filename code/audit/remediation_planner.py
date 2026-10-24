"""Remediation and Verification Planning Module.

Constructs ordered finding, remediation, and verification steps according to
the required operation order, system_id, and resource_id sorting.
"""

from typing import Any, Dict, List


# Operation priority ordering per challenge specification
FINDING_OP_ORDER = {
    "REPORT_REMAINING_RECORD": 1,
    "REPORT_EXPOSED_PII": 2,
    "REPORT_ACTIVE_DATA_FLOW": 3,
    "REPORT_RESTORE_RISK": 4,
}

REMEDIATION_OP_ORDER = {
    "DISABLE_DATA_FLOW": 1,
    "BLOCK_RESTORE": 2,
    "DELETE_RECORD": 3,
    "REDACT_RECORD": 4,
    "ANONYMIZE_RECORD": 5,
}

VERIFICATION_OP_ORDER = {
    "VERIFY_RECORD_ABSENT": 1,
    "VERIFY_RECORD_PRESENT": 2,
    "VERIFY_RECORD_REDACTED": 3,
    "VERIFY_RECORD_ANONYMIZED": 4,
    "VERIFY_DATA_FLOW_DISABLED": 5,
    "VERIFY_RESTORE_BLOCKED": 6,
}


class RemediationPlanner:
    """Sorts and formats steps into a compliant JSON array."""

    @staticmethod
    def order_steps(
        findings: List[Dict[str, Any]],
        remediations: List[Dict[str, Any]],
        verifications: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Sorts findings, remediations, and verifications and assigns 1-based step numbers."""
        # Sort findings
        sorted_findings = sorted(
            findings,
            key=lambda s: (
                FINDING_OP_ORDER.get(s["operation"], 99),
                s.get("system_id", ""),
                s.get("resource_id", ""),
            )
        )

        # Sort remediations
        sorted_remediations = sorted(
            remediations,
            key=lambda s: (
                REMEDIATION_OP_ORDER.get(s["operation"], 99),
                s.get("system_id", ""),
                s.get("resource_id", ""),
            )
        )

        # Sort verifications
        sorted_verifications = sorted(
            verifications,
            key=lambda s: (
                VERIFICATION_OP_ORDER.get(s["operation"], 99),
                s.get("system_id", ""),
                s.get("resource_id", ""),
            )
        )

        # Combine into phase sequence: FINDING -> REMEDIATION -> VERIFICATION
        all_steps = []
        step_no = 1

        for step in sorted_findings + sorted_remediations + sorted_verifications:
            ordered_step = {
                "step_no": step_no,
                "phase": step["phase"],
                "system_id": step["system_id"],
                "resource_id": step["resource_id"],
                "operation": step["operation"],
                "state": step["state"],
                "evidence_id": step.get("evidence_id", ""),
            }
            all_steps.append(ordered_step)
            step_no += 1

        return all_steps
