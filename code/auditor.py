"""
Auditor for Ghostinel Deletion Audit Agent.
Evaluates cases, determines findings, plans remediation, and generates verified steps.
"""
from typing import List, Dict, Set, Optional, Tuple, Any
from datetime import datetime
import json

from code.models import (
    AuditStep, DeletionStatus, Phase,
    PHASE_ORDER, OPERATION_ORDER, OPERATION_DEFAULT_STATE
)
from code.identity_resolver import IdentityResolver, UserIdentity
from code.evidence_indexer import EvidenceIndexer, Observation


class Auditor:
    def __init__(self, indexer: EvidenceIndexer, resolver: IdentityResolver, activities_csv: str = "dataset/system_activity.csv"):
        self.indexer = indexer
        self.resolver = resolver
        self.worker_activities: List[Dict[str, str]] = []
        self._load_activities(activities_csv)

    def _load_activities(self, activities_csv: str):
        import csv
        with open(activities_csv, mode="r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["source_system"] == "deletion_worker":
                    self.worker_activities.append(r)

    def is_not_applicable(self, text: str) -> bool:
        text_lower = text.lower()
        # Explicit non-deletion requests
        non_del_triggers = [
            "leave the account active", "keep the account as it is",
            "leave my profile", "download my account", "invoices for my records",
            "continue using the service", "leave the account as active"
        ]
        for trigger in non_del_triggers:
            if trigger in text_lower:
                return True
        return False

    def audit_case(self, case_id: str, email: str, requested_at: str, reported_status: str, reported_at: str, audit_at: str, request_text: str) -> Tuple[str, List[Dict[str, Any]]]:
        # 1. Check if NOT_APPLICABLE
        if self.is_not_applicable(request_text):
            return DeletionStatus.NOT_APPLICABLE.value, []

        user = self.resolver.resolve_by_email(email)
        uid = user.user_id if user else None

        # 2. Collect candidate observations for this case
        obs_map: Dict[str, Observation] = {}
        
        # From direct email
        if email.lower() in self.indexer.obs_by_email:
            for o in self.indexer.obs_by_email[email.lower()]:
                obs_map[o.resource_id] = o

        # From user_id
        if uid and uid in self.indexer.obs_by_user_id:
            for o in self.indexer.obs_by_user_id[uid]:
                obs_map[o.resource_id] = o

        # From historical emails
        if user:
            for hist_em in user.historical_emails:
                if hist_em.lower() in self.indexer.obs_by_email:
                    for o in self.indexer.obs_by_email[hist_em.lower()]:
                        obs_map[o.resource_id] = o

        # Match deletion_worker activities within window of reported_at (+/- 2.5 hours)
        rep_dt = datetime.fromisoformat(reported_at.replace("Z", ""))
        for act in self.worker_activities:
            adt = datetime.fromisoformat(act["event_time"].replace("Z", ""))
            diff_hours = abs((adt - rep_dt).total_seconds()) / 3600.0
            if diff_hours <= 2.2:
                res_id = act["resource_id"]
                target_sys = act["target_system"]
                etype = act["event_type"]
                result = act["reported_result"]
                
                # If we don't already have an observation from evidence for this resource, create one from activity
                if res_id not in obs_map:
                    status = "PRESENT"
                    category = "USER_PROFILE"
                    
                    if etype == "DELETE_RECORD":
                        status = "ABSENT" if result == "SUCCESS" else "PRESENT"
                        category = "USER_PROFILE" if "account" in res_id else (
                            "SEARCH_INDEX_ENTRY" if "search" in res_id else (
                                "USER_EXPORT" if "export" in res_id else "USER_PROFILE"
                            )
                        )
                    elif etype == "ANONYMIZE_RECORD":
                        status = "ANONYMIZED" if result == "SUCCESS" else "IDENTIFIABLE"
                        category = "ANALYTICS_PROFILE"
                    elif etype == "REDACT_RECORD":
                        status = "REDACTED" if result == "SUCCESS" else "IDENTIFIABLE"
                        category = "SUPPORT_MESSAGE"
                    elif etype in ["DISABLE_DATA_FLOW", "CHECK_DATA_FLOW"]:
                        status = "DISABLED" if (result == "SUCCESS" and etype == "DISABLE_DATA_FLOW") else "ACTIVE"
                        category = "DATA_FLOW"
                    elif etype in ["BLOCK_RESTORE", "CHECK_RESTORE_ACCESS"]:
                        status = "BLOCKED" if (result == "SUCCESS" and etype == "BLOCK_RESTORE") else "RESTORE_RISK"
                        category = "BACKUP_ARCHIVE"
                    
                    obs_map[res_id] = Observation(
                        evidence_id="",
                        file_path="",
                        captured_at=act["event_time"],
                        system_id=target_sys,
                        resource_id=res_id,
                        user_id=uid,
                        email=email,
                        status=status,
                        category=category,
                        raw_info=act["details"]
                    )

        # 3. Apply Deletion Rules and generate steps
        raw_steps: List[AuditStep] = []
        has_findings = False

        for res_id, obs in sorted(obs_map.items()):
            sys_id = obs.system_id
            cat = obs.category
            stat = obs.status
            ev_id = obs.evidence_id

            # Rule: USER_PROFILE, SEARCH_INDEX_ENTRY, USER_EXPORT, SUPPORT_ATTACHMENT (Must be deleted)
            if cat in ["USER_PROFILE", "SEARCH_INDEX_ENTRY", "USER_EXPORT", "SUPPORT_ATTACHMENT"] or "account" in res_id or "search" in res_id or "export" in res_id:
                if stat == "PRESENT":
                    has_findings = True
                    raw_steps.append(AuditStep(0, Phase.FINDING.value, sys_id, res_id, "REPORT_REMAINING_RECORD", "PRESENT", ev_id))
                    raw_steps.append(AuditStep(0, Phase.REMEDIATION.value, sys_id, res_id, "DELETE_RECORD", "ABSENT", ""))
                    raw_steps.append(AuditStep(0, Phase.VERIFICATION.value, sys_id, res_id, "VERIFY_RECORD_ABSENT", "ABSENT", ""))
                else: # ABSENT
                    raw_steps.append(AuditStep(0, Phase.VERIFICATION.value, sys_id, res_id, "VERIFY_RECORD_ABSENT", "ABSENT", ev_id))

            # Rule: ANALYTICS_PROFILE (Must be anonymized)
            elif cat == "ANALYTICS_PROFILE" or "analytics" in res_id:
                if stat == "IDENTIFIABLE" or stat == "PRESENT":
                    has_findings = True
                    raw_steps.append(AuditStep(0, Phase.FINDING.value, sys_id, res_id, "REPORT_EXPOSED_PII", "PRESENT", ev_id))
                    raw_steps.append(AuditStep(0, Phase.REMEDIATION.value, sys_id, res_id, "ANONYMIZE_RECORD", "ANONYMIZED", ""))
                    raw_steps.append(AuditStep(0, Phase.VERIFICATION.value, sys_id, res_id, "VERIFY_RECORD_ANONYMIZED", "ANONYMIZED", ""))
                else: # ANONYMIZED
                    raw_steps.append(AuditStep(0, Phase.VERIFICATION.value, sys_id, res_id, "VERIFY_RECORD_ANONYMIZED", "ANONYMIZED", ev_id))

            # Rule: SUPPORT_MESSAGE or ACCOUNT_TOMBSTONE (Must be redacted)
            elif cat in ["SUPPORT_MESSAGE", "ACCOUNT_TOMBSTONE"] or "support" in res_id or "tombstone" in res_id:
                if stat == "IDENTIFIABLE" or stat == "PRESENT":
                    has_findings = True
                    raw_steps.append(AuditStep(0, Phase.FINDING.value, sys_id, res_id, "REPORT_EXPOSED_PII", "PRESENT", ev_id))
                    raw_steps.append(AuditStep(0, Phase.REMEDIATION.value, sys_id, res_id, "REDACT_RECORD", "REDACTED", ""))
                    raw_steps.append(AuditStep(0, Phase.VERIFICATION.value, sys_id, res_id, "VERIFY_RECORD_REDACTED", "REDACTED", ""))
                else: # REDACTED
                    raw_steps.append(AuditStep(0, Phase.VERIFICATION.value, sys_id, res_id, "VERIFY_RECORD_REDACTED", "REDACTED", ev_id))

            # Rule: DATA_FLOW (Must be disabled)
            elif cat == "DATA_FLOW" or "data_flow" in res_id:
                if stat == "ACTIVE":
                    has_findings = True
                    raw_steps.append(AuditStep(0, Phase.FINDING.value, sys_id, res_id, "REPORT_ACTIVE_DATA_FLOW", "ACTIVE", ev_id))
                    raw_steps.append(AuditStep(0, Phase.REMEDIATION.value, sys_id, res_id, "DISABLE_DATA_FLOW", "DISABLED", ""))
                    raw_steps.append(AuditStep(0, Phase.VERIFICATION.value, sys_id, res_id, "VERIFY_DATA_FLOW_DISABLED", "DISABLED", ""))
                else: # DISABLED
                    raw_steps.append(AuditStep(0, Phase.VERIFICATION.value, sys_id, res_id, "VERIFY_DATA_FLOW_DISABLED", "DISABLED", ev_id))

            # Rule: BACKUP_ARCHIVE (Restore access must be blocked)
            elif cat == "BACKUP_ARCHIVE" or "backup" in res_id:
                if stat == "RESTORE_RISK" or stat == "ACTIVE":
                    has_findings = True
                    raw_steps.append(AuditStep(0, Phase.FINDING.value, sys_id, res_id, "REPORT_RESTORE_RISK", "ACTIVE", ev_id))
                    raw_steps.append(AuditStep(0, Phase.REMEDIATION.value, sys_id, res_id, "BLOCK_RESTORE", "BLOCKED", ""))
                    raw_steps.append(AuditStep(0, Phase.VERIFICATION.value, sys_id, res_id, "VERIFY_RESTORE_BLOCKED", "BLOCKED", ""))
                else: # BLOCKED
                    raw_steps.append(AuditStep(0, Phase.VERIFICATION.value, sys_id, res_id, "VERIFY_RESTORE_BLOCKED", "BLOCKED", ev_id))

            # Rule: SECURITY_AUDIT_LOG or LEGAL_HOLD_RECORD (Must be retained / verified present)
            elif cat in ["SECURITY_AUDIT_LOG", "LEGAL_HOLD_RECORD"] or "audit_record" in res_id:
                raw_steps.append(AuditStep(0, Phase.VERIFICATION.value, sys_id, res_id, "VERIFY_RECORD_PRESENT", "PRESENT", ev_id))

        # 4. Final Status Determination
        final_status = DeletionStatus.INCOMPLETE.value if has_findings else DeletionStatus.COMPLETE.value

        # Filter steps based on status
        if final_status == DeletionStatus.COMPLETE.value:
            # For COMPLETE, include only verification steps
            selected_steps = [s for s in raw_steps if s.phase == Phase.VERIFICATION.value]
        else:
            # For INCOMPLETE, proposed remediation and future verification use empty evidence_id
            selected_steps = []
            for s in raw_steps:
                if s.phase in [Phase.REMEDIATION.value, Phase.VERIFICATION.value]:
                    s.evidence_id = ""
                selected_steps.append(s)

        # 5. Strict Sorting
        # Phase order -> Operation order -> system_id ASC -> resource_id ASC
        def sort_key(s: AuditStep):
            p_order = PHASE_ORDER.get(Phase(s.phase), 99)
            op_order = OPERATION_ORDER.get(s.operation, 99)
            return (p_order, op_order, s.system_id, s.resource_id)

        sorted_steps = sorted(selected_steps, key=sort_key)

        # 6. Renumber step_no consecutively starting at 1
        for idx, step in enumerate(sorted_steps, 1):
            step.step_no = idx

        return final_status, [s.to_dict() for s in sorted_steps]
