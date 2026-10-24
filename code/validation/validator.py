"""Output Validation Module.

Enforces strict compliance with the submission format, allowed operations,
sorting constraints, sequential step numbering, and evidence rules.
"""

import json
import os
from typing import Dict, List, Optional, Set, Tuple
import pandas as pd


VALID_STATUSES = {"COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"}

VALID_OPERATIONS = {
    "FINDING": {
        "REPORT_REMAINING_RECORD": "PRESENT",
        "REPORT_EXPOSED_PII": "PRESENT",
        "REPORT_ACTIVE_DATA_FLOW": "ACTIVE",
        "REPORT_RESTORE_RISK": "ACTIVE",
    },
    "REMEDIATION": {
        "DISABLE_DATA_FLOW": "DISABLED",
        "BLOCK_RESTORE": "BLOCKED",
        "DELETE_RECORD": "ABSENT",
        "REDACT_RECORD": "REDACTED",
        "ANONYMIZE_RECORD": "ANONYMIZED",
    },
    "VERIFICATION": {
        "VERIFY_RECORD_ABSENT": "ABSENT",
        "VERIFY_RECORD_PRESENT": "PRESENT",
        "VERIFY_RECORD_REDACTED": "REDACTED",
        "VERIFY_RECORD_ANONYMIZED": "ANONYMIZED",
        "VERIFY_DATA_FLOW_DISABLED": "DISABLED",
        "VERIFY_RESTORE_BLOCKED": "BLOCKED",
    },
}

PHASE_ORDER = {"FINDING": 1, "REMEDIATION": 2, "VERIFICATION": 3}


CANONICAL_SYSTEMS = {
    "account_service",
    "analytics_platform",
    "backup_service",
    "export_service",
    "identity_service",
    "integration_service",
    "search_service",
    "security_service",
    "support_platform",
}

REMEDIATION_OP_PRIORITY = {
    "DISABLE_DATA_FLOW": 1,
    "BLOCK_RESTORE": 2,
    "DELETE_RECORD": 3,
    "REDACT_RECORD": 4,
    "ANONYMIZE_RECORD": 5,
}

REQUIRED_STEP_FIELDS = {
    "step_no",
    "phase",
    "system_id",
    "resource_id",
    "operation",
    "state",
    "evidence_id",
}


class OutputValidator:
    """Validates output.csv against all challenge rules."""

    def __init__(
        self,
        expected_row_count: int = 518,
        requests_csv_path: Optional[str] = "dataset/deletion_requests.csv",
        evidence_csv_path: Optional[str] = "dataset/evidence_files.csv",
    ):
        self.expected_row_count = expected_row_count
        self.requests_csv_path = requests_csv_path
        self.evidence_csv_path = evidence_csv_path

        self.valid_evidence_files: Dict[str, str] = {}
        if evidence_csv_path and os.path.exists(evidence_csv_path):
            ev_df = pd.read_csv(evidence_csv_path)
            for _, r in ev_df.iterrows():
                self.valid_evidence_files[str(r["file_id"]).strip()] = str(r["captured_at"]).strip()

        self.input_cases: Dict[str, Dict[str, Any]] = {}
        if requests_csv_path and os.path.exists(requests_csv_path):
            req_df = pd.read_csv(requests_csv_path)
            for _, r in req_df.iterrows():
                self.input_cases[str(r["case_id"]).strip()] = {
                    "audit_at": str(r.get("audit_at", "")).strip(),
                    "email": str(r.get("email", "")).strip(),
                }

    def validate_file(self, csv_path: str) -> Tuple[bool, List[str]]:
        errors = []

        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            return False, [f"Failed to read CSV: {e}"]

        # 1. Check exact columns and order
        expected_cols = ["case_id", "deletion_status", "steps_json"]
        if list(df.columns) != expected_cols:
            errors.append(f"Invalid columns: expected {expected_cols}, got {list(df.columns)}")

        # 2. Check row count
        if len(df) != self.expected_row_count:
            errors.append(f"Invalid row count: expected {self.expected_row_count}, got {len(df)}")

        # 3. Check case_id sorting and uniqueness
        case_ids = df["case_id"].tolist()
        sorted_case_ids = sorted(case_ids)
        if case_ids != sorted_case_ids:
            errors.append("Rows are not sorted by case_id")

        if len(case_ids) != len(set(case_ids)):
            errors.append("Duplicate case_ids detected in output")

        # 4. Check that all input case_ids are accounted for
        if self.input_cases:
            missing_cases = set(self.input_cases.keys()) - set(case_ids)
            if missing_cases:
                errors.append(f"Missing results for {len(missing_cases)} input cases: {sorted(list(missing_cases))[:5]}")
            extra_cases = set(case_ids) - set(self.input_cases.keys())
            if extra_cases:
                errors.append(f"Extra results not in input cases: {sorted(list(extra_cases))[:5]}")

        for idx, row in df.iterrows():
            cid = str(row["case_id"]).strip()
            status = str(row["deletion_status"]).strip()
            raw_steps = row["steps_json"]
            audit_at = self.input_cases.get(cid, {}).get("audit_at", "")

            # 5. Permitted statuses
            if status not in VALID_STATUSES:
                errors.append(f"Row {idx} ({cid}): invalid status '{status}'")
                continue

            # 6. JSON array parsing
            try:
                steps = json.loads(raw_steps) if isinstance(raw_steps, str) else raw_steps
                if not isinstance(steps, list):
                    errors.append(f"Row {idx} ({cid}): steps_json is not an array")
                    continue
            except Exception as e:
                errors.append(f"Row {idx} ({cid}): JSON decode error: {e}")
                continue

            # 7. NOT_APPLICABLE must have empty array
            if status == "NOT_APPLICABLE":
                if len(steps) != 0:
                    errors.append(f"Row {idx} ({cid}): NOT_APPLICABLE must have steps_json=[]")
                continue

            # Check steps
            last_phase_rank = 0
            phases_present = set()
            last_remediation_rank = 0

            for s_idx, s in enumerate(steps):
                expected_step_no = s_idx + 1

                # 8. Check exact step fields
                if set(s.keys()) != REQUIRED_STEP_FIELDS:
                    extra = set(s.keys()) - REQUIRED_STEP_FIELDS
                    missing = REQUIRED_STEP_FIELDS - set(s.keys())
                    errors.append(f"Row {idx} ({cid}) step {expected_step_no}: invalid schema (extra={extra}, missing={missing})")

                # 9. Consecutive step numbering
                if s.get("step_no") != expected_step_no:
                    errors.append(f"Row {idx} ({cid}) step {s_idx}: step_no expected {expected_step_no}, got {s.get('step_no')}")

                phase = s.get("phase")
                sys_id = s.get("system_id")
                rid = s.get("resource_id")
                op = s.get("operation")
                state = s.get("state")
                ev_id = str(s.get("evidence_id", "")).strip()

                phases_present.add(phase)

                # 10. Canonical system identification
                if sys_id not in CANONICAL_SYSTEMS:
                    errors.append(f"Row {idx} ({cid}) step {expected_step_no}: non-canonical system_id '{sys_id}'")

                # 11. Valid phase and phase ordering
                if phase not in VALID_OPERATIONS:
                    errors.append(f"Row {idx} ({cid}) step {expected_step_no}: invalid phase '{phase}'")
                    continue

                phase_rank = PHASE_ORDER[phase]
                if phase_rank < last_phase_rank:
                    errors.append(f"Row {idx} ({cid}) step {expected_step_no}: phase order violated ({phase} after higher phase)")
                last_phase_rank = phase_rank

                # 12. Allowed operation and state matching
                allowed_ops = VALID_OPERATIONS[phase]
                if op not in allowed_ops:
                    errors.append(f"Row {idx} ({cid}) step {expected_step_no}: operation '{op}' not allowed in phase '{phase}'")
                elif allowed_ops[op] != state:
                    errors.append(f"Row {idx} ({cid}) step {expected_step_no}: operation '{op}' expects state '{allowed_ops[op]}', got '{state}'")

                # 13. Remediation dependency ordering
                if phase == "REMEDIATION":
                    rem_rank = REMEDIATION_OP_PRIORITY.get(op, 99)
                    if rem_rank < last_remediation_rank:
                        errors.append(f"Row {idx} ({cid}) step {expected_step_no}: remediation dependency ordering violated ({op} after higher priority operation)")
                    last_remediation_rank = rem_rank

                # 14. Evidence validity and temporal cutoff
                if ev_id:
                    if self.valid_evidence_files and ev_id not in self.valid_evidence_files:
                        errors.append(f"Row {idx} ({cid}) step {expected_step_no}: invalid evidence citation '{ev_id}'")
                    elif audit_at and ev_id in self.valid_evidence_files:
                        captured_at = self.valid_evidence_files[ev_id]
                        if captured_at > audit_at:
                            errors.append(f"Row {idx} ({cid}) step {expected_step_no}: cited evidence '{ev_id}' captured at {captured_at} after audit_at {audit_at}")

                # 15. Case type evidence rules
                if status == "COMPLETE":
                    if phase != "VERIFICATION":
                        errors.append(f"Row {idx} ({cid}) step {expected_step_no}: COMPLETE case cannot have {phase} phase")
                    if not ev_id:
                        errors.append(f"Row {idx} ({cid}) step {expected_step_no}: COMPLETE verification must cite evidence_id")
                elif status == "INCOMPLETE":
                    if phase == "FINDING" and not ev_id:
                        errors.append(f"Row {idx} ({cid}) step {expected_step_no}: FINDING step must cite evidence_id")
                    elif phase in ["REMEDIATION", "VERIFICATION"] and ev_id != "":
                        errors.append(f"Row {idx} ({cid}) step {expected_step_no}: INCOMPLETE {phase} must have empty evidence_id, got '{ev_id}'")

            # 16. INCOMPLETE case completeness
            if status == "INCOMPLETE":
                if not ({"FINDING", "REMEDIATION", "VERIFICATION"}.issubset(phases_present)):
                    missing_p = {"FINDING", "REMEDIATION", "VERIFICATION"} - phases_present
                    errors.append(f"Row {idx} ({cid}): INCOMPLETE case missing required phases: {missing_p}")

        is_valid = len(errors) == 0
        return is_valid, errors


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "output.csv"
    print(f"Validating {target}...")
    v = OutputValidator()
    valid, errs = v.validate_file(target)
    if valid:
        print(f"VALIDATION PASSED: {target} conforms to all competition contracts (0 errors).")
        sys.exit(0)
    else:
        print(f"VALIDATION FAILED: {len(errs)} errors found in {target}:")
        for e in errs[:20]:
            print(f"  - {e}")
        if len(errs) > 20:
            print(f"  ... and {len(errs) - 20} more errors.")
        sys.exit(1)

