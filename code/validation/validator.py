"""Output Validation Module.

Enforces strict compliance with the submission format, allowed operations,
sorting constraints, sequential step numbering, and evidence rules.
"""

import json
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


class OutputValidator:
    """Validates output.csv against all challenge rules."""

    def __init__(self, expected_row_count: int = 518):
        self.expected_row_count = expected_row_count

    def validate_file(self, csv_path: str) -> Tuple[bool, List[str]]:
        errors = []

        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            return False, [f"Failed to read CSV: {e}"]

        # Check columns
        expected_cols = ["case_id", "deletion_status", "steps_json"]
        if list(df.columns) != expected_cols:
            errors.append(f"Invalid columns: expected {expected_cols}, got {list(df.columns)}")

        # Check row count
        if len(df) != self.expected_row_count:
            errors.append(f"Invalid row count: expected {self.expected_row_count}, got {len(df)}")

        # Check case_id sorting
        case_ids = df["case_id"].tolist()
        sorted_case_ids = sorted(case_ids)
        if case_ids != sorted_case_ids:
            errors.append("Rows are not sorted by case_id")

        for idx, row in df.iterrows():
            cid = str(row["case_id"])
            status = str(row["deletion_status"]).strip()
            raw_steps = row["steps_json"]

            if status not in VALID_STATUSES:
                errors.append(f"Row {idx} ({cid}): invalid status '{status}'")
                continue

            try:
                steps = json.loads(raw_steps) if isinstance(raw_steps, str) else raw_steps
                if not isinstance(steps, list):
                    errors.append(f"Row {idx} ({cid}): steps_json is not an array")
                    continue
            except Exception as e:
                errors.append(f"Row {idx} ({cid}): JSON decode error: {e}")
                continue

            # NOT_APPLICABLE must have empty array
            if status == "NOT_APPLICABLE":
                if len(steps) != 0:
                    errors.append(f"Row {idx} ({cid}): NOT_APPLICABLE must have steps_json=[]")
                continue

            # Check steps
            last_phase_rank = 0
            for s_idx, s in enumerate(steps):
                expected_step_no = s_idx + 1
                if s.get("step_no") != expected_step_no:
                    errors.append(f"Row {idx} ({cid}) step {s_idx}: step_no expected {expected_step_no}, got {s.get('step_no')}")

                phase = s.get("phase")
                op = s.get("operation")
                state = s.get("state")
                ev_id = s.get("evidence_id", "")

                if phase not in VALID_OPERATIONS:
                    errors.append(f"Row {idx} ({cid}) step {expected_step_no}: invalid phase '{phase}'")
                    continue

                phase_rank = PHASE_ORDER[phase]
                if phase_rank < last_phase_rank:
                    errors.append(f"Row {idx} ({cid}) step {expected_step_no}: phase order violated ({phase} after higher phase)")
                last_phase_rank = phase_rank

                allowed_ops = VALID_OPERATIONS[phase]
                if op not in allowed_ops:
                    errors.append(f"Row {idx} ({cid}) step {expected_step_no}: operation '{op}' not allowed in phase '{phase}'")
                elif allowed_ops[op] != state:
                    errors.append(f"Row {idx} ({cid}) step {expected_step_no}: operation '{op}' expects state '{allowed_ops[op]}', got '{state}'")

                # Evidence rules
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

        is_valid = len(errors) == 0
        return is_valid, errors
