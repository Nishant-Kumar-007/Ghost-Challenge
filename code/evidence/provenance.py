"""Provenance Verification Module.

Ensures every finding and verification step cites a valid participant-visible
file_id, activity_id, or audit_id, and that remediation steps use an empty evidence_id.
"""

from typing import Dict, List, Optional, Set


class ProvenanceVerifier:
    """Verifies that evidence citations adhere to the challenge rules."""

    def __init__(self, valid_file_ids: Set[str], valid_activity_ids: Set[str], valid_audit_ids: Set[str]):
        self.valid_file_ids = valid_file_ids
        self.valid_activity_ids = valid_activity_ids
        self.valid_audit_ids = valid_audit_ids

    def is_valid_evidence_id(self, evidence_id: str) -> bool:
        if not evidence_id:
            return False
        return (
            evidence_id in self.valid_file_ids or
            evidence_id in self.valid_activity_ids or
            evidence_id in self.valid_audit_ids
        )

    def verify_step(self, step: Dict[str, any], is_complete_case: bool) -> List[str]:
        """Returns list of error messages if step violates provenance rules."""
        errors = []
        phase = step.get("phase")
        ev_id = step.get("evidence_id", "")

        if phase == "FINDING":
            if not ev_id:
                errors.append(f"FINDING step {step.get('step_no')} missing evidence_id")
            elif not self.is_valid_evidence_id(ev_id):
                errors.append(f"FINDING step {step.get('step_no')} cites unknown evidence_id '{ev_id}'")

        elif phase == "REMEDIATION":
            if ev_id != "":
                errors.append(f"REMEDIATION step {step.get('step_no')} must have empty evidence_id, got '{ev_id}'")

        elif phase == "VERIFICATION":
            if is_complete_case:
                if not ev_id:
                    errors.append(f"COMPLETE VERIFICATION step {step.get('step_no')} must cite evidence_id")
                elif not self.is_valid_evidence_id(ev_id):
                    errors.append(f"COMPLETE VERIFICATION step {step.get('step_no')} cites unknown evidence_id '{ev_id}'")
            else:
                # Incomplete case post-remediation verification must have empty evidence_id
                if ev_id != "":
                    errors.append(f"INCOMPLETE VERIFICATION step {step.get('step_no')} must have empty evidence_id, got '{ev_id}'")

        return errors
