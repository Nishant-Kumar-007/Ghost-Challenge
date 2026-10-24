"""Historical State Reconstruction and Deletion Audit Engine.

Reconstructs the true state of a customer's personal data across systems
at the case's audit_at cutoff, applies deletion policy, and generates
the complete audit result.
"""

import json
import os
import sqlite3
from typing import Any, Dict, List, Optional, Set, Tuple
import pandas as pd

from code.identity.resolver import IdentityResolver, UserIdentity
from code.classification.classifier import RequestClassifier
from code.evidence.indexer import EvidenceIndexer
from code.audit.policy_evaluator import PolicyEvaluator
from code.audit.remediation_planner import RemediationPlanner


class DeletionAuditEngine:
    """End-to-end engine for auditing deletion requests."""

    def __init__(self, dataset_dir: str = "dataset"):
        self.dataset_dir = dataset_dir
        self.identity_resolver = IdentityResolver(dataset_dir)
        self.classifier = RequestClassifier()
        self.indexer = EvidenceIndexer(":memory:", dataset_dir)
        self.indexer.build_index()
        self.policy_evaluator = PolicyEvaluator(dataset_dir)
        self.planner = RemediationPlanner()
        self._load_system_activity()

    def _load_system_activity(self) -> None:
        act_path = os.path.join(self.dataset_dir, "system_activity.csv")
        self.activities: List[Dict[str, Any]] = []
        if os.path.exists(act_path):
            df = pd.read_csv(act_path)
            for _, r in df.iterrows():
                self.activities.append({
                    "activity_id": str(r["activity_id"]).strip(),
                    "event_time": str(r["event_time"]).strip(),
                    "event_type": str(r["event_type"]).strip(),
                    "source_system": str(r["source_system"]).strip() if pd.notna(r["source_system"]) else "",
                    "target_system": str(r["target_system"]).strip() if pd.notna(r["target_system"]) else "",
                    "resource_id": str(r["resource_id"]).strip() if pd.notna(r["resource_id"]) else "",
                    "reported_result": str(r["reported_result"]).strip() if pd.notna(r["reported_result"]) else "",
                    "details": str(r["details"]) if pd.notna(r["details"]) else "",
                })

    def _canonicalize_system_id(self, sys_id: str, rid: str = "") -> str:
        s = str(sys_id).lower() if sys_id else ""
        r = str(rid).lower() if rid else ""

        if "search" in s or r.startswith("search_"):
            return "search_service"
        elif "analytics" in s or "marketing" in s or r.startswith("analytics_"):
            return "analytics_platform"
        elif "support" in s or "attachment" in s or r.startswith("support_"):
            return "support_platform"
        elif "export" in s or r.startswith("export_"):
            return "export_service"
        elif "integration" in s or "connector" in s or "delivery" in s or r.startswith("data_flow_"):
            return "integration_service"
        elif "backup" in s or "restore" in s or r.startswith("backup_"):
            return "backup_service"
        elif "security" in s or "legal" in s or "audit" in s or r.startswith("audit_record_"):
            return "security_service"
        elif "identity" in s or "tombstone" in s or r.startswith("tombstone_"):
            return "identity_service"
        elif "account" in s or r.startswith("account_"):
            return "account_service"
        return "account_service"

    def audit_case(self, case_row: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
        """Audits a single request case.

        Returns (deletion_status, steps).
        """
        case_id = str(case_row["case_id"]).strip()
        email = str(case_row["email"]).strip()
        request_text = str(case_row.get("request_text", ""))
        audit_at = str(case_row.get("audit_at", "")).strip()

        # 1. Classification: Does request authorize deletion?
        is_deletion, reason = self.classifier.classify(request_text)
        if not is_deletion:
            return "NOT_APPLICABLE", []

        # 2. Identity Resolution
        user = self.identity_resolver.resolve(email)
        if not user:
            # Fallback if user not found: empty or incomplete
            return "NOT_APPLICABLE", []

        # 3. Evidence Gathering up to audit_at
        evidence_list = self.indexer.find_evidence_for_user(user, audit_at)

        # 4. Activity Gathering: Find resources touched by workflow for this user
        user_resources: Dict[str, Dict[str, Any]] = {}
        # From evidence
        for ev in evidence_list:
            rid = ev["resource_id"]
            if rid:
                canon_sys = self._canonicalize_system_id(ev["system_id"], rid)
                user_resources[rid] = {
                    "resource_id": rid,
                    "system_id": canon_sys,
                    "resource_type": ev["resource_type"],
                    "state_observed": ev["state_observed"],
                    "evidence_id": ev["file_id"],
                    "captured_at": ev["captured_at"],
                }

        # From system_activity (for any resource touched during deletion workflow)
        requested_at = str(case_row.get("requested_at", "")).strip()
        for act in self.activities:
            if act["event_time"] > audit_at:
                continue
            if requested_at and act["event_time"] < requested_at:
                continue
            rid = act["resource_id"]
            details = act["details"]
            # Check if this activity belongs to the user
            is_match = False
            if rid and rid in user_resources:
                is_match = True
            elif user.user_id and user.user_id in details:
                is_match = True
            elif any(e in details.lower() for e in user.emails):
                is_match = True

            if is_match and rid:
                if rid not in user_resources:
                    raw_sys = act["target_system"] or act["source_system"]
                    canon_sys = self._canonicalize_system_id(raw_sys, rid)
                    res_type = "USER_PROFILE"
                    if "search" in canon_sys:
                        res_type = "SEARCH_INDEX_ENTRY"
                    elif "analytics" in canon_sys:
                        res_type = "ANALYTICS_PROFILE"
                    elif "support" in canon_sys:
                        res_type = "SUPPORT_MESSAGE"
                    elif "export" in canon_sys:
                        res_type = "USER_EXPORT"
                    elif "integration" in canon_sys or "connector" in details:
                        res_type = "DATA_FLOW"
                    elif "backup" in canon_sys:
                        res_type = "BACKUP_ARCHIVE"
                    elif "security" in canon_sys or "audit" in details:
                        res_type = "SECURITY_AUDIT_LOG"

                    user_resources[rid] = {
                        "resource_id": rid,
                        "system_id": canon_sys,
                        "resource_type": res_type,
                        "state_observed": "ABSENT" if act["event_type"] == "DELETE_RECORD" and act["reported_result"] == "SUCCESS" else "PRESENT",
                        "evidence_id": act["activity_id"],
                        "captured_at": act["event_time"],
                    }

        # 5. Evaluate Compliance & Violations
        findings = []
        remediations = []
        verifications = []

        # Track what needs remediation
        has_violations = False

        for rid, info in sorted(user_resources.items()):
            sys_id = self._canonicalize_system_id(info["system_id"], rid)
            res_type = info["resource_type"]
            state = info["state_observed"]
            ev_id = info["evidence_id"]

            # Only actual evidence files can support findings
            if not ev_id.startswith("evidence_") and state in ["PRESENT", "ACTIVE"]:
                continue

            required_action = self.policy_evaluator.get_required_action(res_type)

            # Check Resource Violations
            if res_type in ["USER_PROFILE", "SECONDARY_IDENTIFIER", "SEARCH_INDEX_ENTRY", "USER_EXPORT", "MARKETING_PROFILE", "SUPPORT_ATTACHMENT"]:
                if state == "PRESENT":
                    has_violations = True
                    findings.append({
                        "phase": "FINDING",
                        "system_id": sys_id,
                        "resource_id": rid,
                        "operation": "REPORT_REMAINING_RECORD",
                        "state": "PRESENT",
                        "evidence_id": ev_id,
                    })
                    remediations.append({
                        "phase": "REMEDIATION",
                        "system_id": sys_id,
                        "resource_id": rid,
                        "operation": "DELETE_RECORD",
                        "state": "ABSENT",
                        "evidence_id": "",
                    })
                    verifications.append({
                        "phase": "VERIFICATION",
                        "system_id": sys_id,
                        "resource_id": rid,
                        "operation": "VERIFY_RECORD_ABSENT",
                        "state": "ABSENT",
                        "evidence_id": "",
                    })
                elif state == "ABSENT":
                    verifications.append({
                        "phase": "VERIFICATION",
                        "system_id": sys_id,
                        "resource_id": rid,
                        "operation": "VERIFY_RECORD_ABSENT",
                        "state": "ABSENT",
                        "evidence_id": ev_id,
                    })

            elif res_type in ["SUPPORT_MESSAGE", "EMAIL_DELIVERY_LOG"]:
                if state == "PRESENT":
                    has_violations = True
                    findings.append({
                        "phase": "FINDING",
                        "system_id": sys_id,
                        "resource_id": rid,
                        "operation": "REPORT_EXPOSED_PII",
                        "state": "PRESENT",
                        "evidence_id": ev_id,
                    })
                    remediations.append({
                        "phase": "REMEDIATION",
                        "system_id": sys_id,
                        "resource_id": rid,
                        "operation": "REDACT_RECORD",
                        "state": "REDACTED",
                        "evidence_id": "",
                    })
                    verifications.append({
                        "phase": "VERIFICATION",
                        "system_id": sys_id,
                        "resource_id": rid,
                        "operation": "VERIFY_RECORD_REDACTED",
                        "state": "REDACTED",
                        "evidence_id": "",
                    })
                elif state == "REDACTED":
                    verifications.append({
                        "phase": "VERIFICATION",
                        "system_id": sys_id,
                        "resource_id": rid,
                        "operation": "VERIFY_RECORD_REDACTED",
                        "state": "REDACTED",
                        "evidence_id": ev_id,
                    })

            elif res_type in ["ANALYTICS_PROFILE", "PRODUCT_TELEMETRY"]:
                if state == "PRESENT":
                    has_violations = True
                    findings.append({
                        "phase": "FINDING",
                        "system_id": sys_id,
                        "resource_id": rid,
                        "operation": "REPORT_EXPOSED_PII",
                        "state": "PRESENT",
                        "evidence_id": ev_id,
                    })
                    remediations.append({
                        "phase": "REMEDIATION",
                        "system_id": sys_id,
                        "resource_id": rid,
                        "operation": "ANONYMIZE_RECORD",
                        "state": "ANONYMIZED",
                        "evidence_id": "",
                    })
                    verifications.append({
                        "phase": "VERIFICATION",
                        "system_id": sys_id,
                        "resource_id": rid,
                        "operation": "VERIFY_RECORD_ANONYMIZED",
                        "state": "ANONYMIZED",
                        "evidence_id": "",
                    })
                elif state == "ANONYMIZED":
                    verifications.append({
                        "phase": "VERIFICATION",
                        "system_id": sys_id,
                        "resource_id": rid,
                        "operation": "VERIFY_RECORD_ANONYMIZED",
                        "state": "ANONYMIZED",
                        "evidence_id": ev_id,
                    })

            elif res_type in ["ACCOUNT_TOMBSTONE"]:
                if state == "PRESENT":
                    has_violations = True
                    findings.append({
                        "phase": "FINDING",
                        "system_id": sys_id,
                        "resource_id": rid,
                        "operation": "REPORT_EXPOSED_PII",
                        "state": "PRESENT",
                        "evidence_id": ev_id,
                    })
                    remediations.append({
                        "phase": "REMEDIATION",
                        "system_id": sys_id,
                        "resource_id": rid,
                        "operation": "REDACT_RECORD",
                        "state": "REDACTED",
                        "evidence_id": "",
                    })
                    verifications.append({
                        "phase": "VERIFICATION",
                        "system_id": sys_id,
                        "resource_id": rid,
                        "operation": "VERIFY_RECORD_REDACTED",
                        "state": "REDACTED",
                        "evidence_id": "",
                    })
                elif state == "REDACTED":
                    verifications.append({
                        "phase": "VERIFICATION",
                        "system_id": sys_id,
                        "resource_id": rid,
                        "operation": "VERIFY_RECORD_REDACTED",
                        "state": "REDACTED",
                        "evidence_id": ev_id,
                    })

            elif res_type in ["DATA_FLOW"]:
                if state == "ACTIVE":
                    has_violations = True
                    findings.append({
                        "phase": "FINDING",
                        "system_id": sys_id,
                        "resource_id": rid,
                        "operation": "REPORT_ACTIVE_DATA_FLOW",
                        "state": "ACTIVE",
                        "evidence_id": ev_id,
                    })
                    remediations.append({
                        "phase": "REMEDIATION",
                        "system_id": sys_id,
                        "resource_id": rid,
                        "operation": "DISABLE_DATA_FLOW",
                        "state": "DISABLED",
                        "evidence_id": "",
                    })
                    verifications.append({
                        "phase": "VERIFICATION",
                        "system_id": sys_id,
                        "resource_id": rid,
                        "operation": "VERIFY_DATA_FLOW_DISABLED",
                        "state": "DISABLED",
                        "evidence_id": "",
                    })
                elif state == "DISABLED":
                    verifications.append({
                        "phase": "VERIFICATION",
                        "system_id": sys_id,
                        "resource_id": rid,
                        "operation": "VERIFY_DATA_FLOW_DISABLED",
                        "state": "DISABLED",
                        "evidence_id": ev_id,
                    })

            elif res_type in ["BACKUP_ARCHIVE"]:
                if state == "ACTIVE":
                    has_violations = True
                    findings.append({
                        "phase": "FINDING",
                        "system_id": sys_id,
                        "resource_id": rid,
                        "operation": "REPORT_RESTORE_RISK",
                        "state": "ACTIVE",
                        "evidence_id": ev_id,
                    })
                    remediations.append({
                        "phase": "REMEDIATION",
                        "system_id": sys_id,
                        "resource_id": rid,
                        "operation": "BLOCK_RESTORE",
                        "state": "BLOCKED",
                        "evidence_id": "",
                    })
                    verifications.append({
                        "phase": "VERIFICATION",
                        "system_id": sys_id,
                        "resource_id": rid,
                        "operation": "VERIFY_RESTORE_BLOCKED",
                        "state": "BLOCKED",
                        "evidence_id": "",
                    })
                elif state == "BLOCKED":
                    verifications.append({
                        "phase": "VERIFICATION",
                        "system_id": sys_id,
                        "resource_id": rid,
                        "operation": "VERIFY_RESTORE_BLOCKED",
                        "state": "BLOCKED",
                        "evidence_id": ev_id,
                    })

            elif res_type in ["SECURITY_AUDIT_LOG", "LEGAL_HOLD_RECORD"]:
                # Must be retained
                verifications.append({
                    "phase": "VERIFICATION",
                    "system_id": sys_id,
                    "resource_id": rid,
                    "operation": "VERIFY_RECORD_PRESENT",
                    "state": "PRESENT",
                    "evidence_id": ev_id,
                })

        # 6. Overall Deletion Status
        if has_violations:
            status = "INCOMPLETE"
            # In incomplete cases, post-remediation verifications have evidence_id=""
            for v in verifications:
                v["evidence_id"] = ""
            steps = self.planner.order_steps(findings, remediations, verifications)
        else:
            status = "COMPLETE"
            # In complete cases, only evidence-backed verifications are returned
            steps = self.planner.order_steps([], [], verifications)

        return status, steps
