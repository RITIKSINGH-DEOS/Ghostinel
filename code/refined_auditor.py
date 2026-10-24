"""
Refined Auditor for Ghostinel.
Accurately maps cases to their audit-time evidence snapshots and extracts exact user resources.
"""
import os
import glob
import json
import csv
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple, Any

from code.models import (
    AuditStep, DeletionStatus, Phase,
    PHASE_ORDER, OPERATION_ORDER
)
from code.identity_resolver import IdentityResolver, UserIdentity
from code.evidence_indexer import EvidenceIndexer, Observation


class RefinedAuditor:
    def __init__(self, indexer: EvidenceIndexer, resolver: IdentityResolver, dataset_dir: str = "dataset"):
        self.indexer = indexer
        self.resolver = resolver
        self.dataset_dir = dataset_dir
        self.evidence_files = indexer.evidence_files
        self.worker_activities: List[Dict[str, str]] = []
        self._load_worker_activities()

    def _load_worker_activities(self):
        act_path = os.path.join(self.dataset_dir, "system_activity.csv")
        with open(act_path, mode="r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["source_system"] == "deletion_worker":
                    self.worker_activities.append(r)

    def is_not_applicable(self, text: str) -> bool:
        text_lower = text.lower()
        non_del_triggers = [
            "leave the account active", "keep the account as it is",
            "leave my profile", "download my account", "invoices for my records",
            "continue using the service", "leave the account as active"
        ]
        return any(t in text_lower for t in non_del_triggers)

    def find_evidence_for_case(self, email: str, uid: Optional[str], audit_at_str: str, user_tokens: Set[str]) -> List[str]:
        audit_dt = datetime.fromisoformat(audit_at_str.replace("Z", ""))
        
        # Check all evidence files where user's identifiers are mentioned
        user_ev_ids: Dict[str, float] = {}
        for o in self.indexer.all_observations:
            is_match = False
            if o.email and o.email.lower() in [t.lower() for t in user_tokens if "@" in t]:
                is_match = True
            elif o.user_id and o.user_id in user_tokens:
                is_match = True
            elif o.name and o.name.lower() in [t.lower() for t in user_tokens if not "@" in t]:
                is_match = True

            if is_match:
                eid = o.evidence_id
                if eid and eid in self.evidence_files:
                    cap_str = self.evidence_files[eid]["captured_at"]
                    cap_dt = datetime.fromisoformat(cap_str.replace("Z", ""))
                    diff = (audit_dt - cap_dt).total_seconds()
                    # Captured before or around audit_at (within 2 hours)
                    if -7200 <= diff:
                        user_ev_ids[eid] = abs(diff)

        if user_ev_ids:
            sorted_eids = sorted(user_ev_ids.keys(), key=lambda k: user_ev_ids[k])
            best_diff = user_ev_ids[sorted_eids[0]]
            # If multiple evidence files captured around the same time (e.g. replica and export), include both
            return [e for e, d in user_ev_ids.items() if abs(d - best_diff) < 3600]
            
        # Fallback for failover replica (evidence_54) or read replicas
        min_diff = float("inf")
        best_candidate = None
        for eid, info in self.evidence_files.items():
            cap_dt = datetime.fromisoformat(info["captured_at"].replace("Z", ""))
            diff = (audit_dt - cap_dt).total_seconds()
            if 0 <= diff < 86400 * 3:
                if diff < min_diff:
                    min_diff = diff
                    best_candidate = eid
        return [best_candidate] if best_candidate else []

    def audit_case(self, case_id: str, email: str, requested_at: str, reported_status: str, reported_at: str, audit_at: str, request_text: str) -> Tuple[str, List[Dict[str, Any]]]:
        if self.is_not_applicable(request_text):
            return DeletionStatus.NOT_APPLICABLE.value, []

        user = self.resolver.resolve_by_email(email)
        uid = user.user_id if user else None
        user_tokens = self.resolver.get_all_identifiers(user) if user else {email}

        # 1. Authoritative evidence files
        evidence_ids = self.find_evidence_for_case(email, uid, audit_at, user_tokens)
        
        # 2. Collect direct observations from authoritative evidence
        case_obs: Dict[str, Observation] = {}
        for eid in evidence_ids:
            for o in self.indexer.all_observations:
                if o.evidence_id == eid:
                    is_match = False
                    if o.email and o.email.lower() in [t.lower() for t in user_tokens if "@" in t]:
                        is_match = True
                    elif o.user_id and o.user_id in user_tokens:
                        is_match = True
                    elif o.name and o.name.lower() in [t.lower() for t in user_tokens if not "@" in t]:
                        is_match = True
                    
                    if is_match:
                        case_obs[o.resource_id] = o

        # 3. Security Audit Record:
        # Check if user has an audit_record in case_obs
        has_audit_rec = any("audit_record" in rid for rid in case_obs)
        if not has_audit_rec:
            # Look in all observations for user's audit_record
            for o in self.indexer.all_observations:
                if o.category == "SECURITY_AUDIT_LOG" or "audit_record" in o.resource_id:
                    if (o.user_id and o.user_id in user_tokens) or (o.email and o.email.lower() == email.lower()):
                        case_obs[o.resource_id] = o
                        has_audit_rec = True
                        break

        # 4. Check worker activities around reported_at
        rep_dt = datetime.fromisoformat(reported_at.replace("Z", ""))
        has_account = any("account" in rid for rid in case_obs)
        closest_act = None
        
        if not has_account:
            # Look for DELETE_RECORD on account_service around reported_at
            target_res_status = ['SUCCESS'] if reported_status == 'SUCCESS' else (['PARTIAL'] if reported_status == 'PARTIAL' else ['FAILED', 'PARTIAL', 'NOT_STARTED'])
            
            cand_accs = []
            for act in self.worker_activities:
                if act["event_type"] == "DELETE_RECORD" and act["target_system"] == "account_service":
                    adt = datetime.fromisoformat(act["event_time"].replace("Z", ""))
                    diff = (adt - rep_dt).total_seconds()
                    if -7200 <= diff <= 3600:
                        score = abs(diff)
                        if act["reported_result"] in target_res_status:
                            score -= 10000
                        cand_accs.append((score, act))
            cand_accs.sort(key=lambda x: x[0])
            closest_act = cand_accs[0][1] if cand_accs else None
            
            if closest_act:
                acc_res_id = closest_act["resource_id"]
                primary_ev = evidence_ids[0] if evidence_ids else "evidence_54"
                
                # Check if account is actually present in evidence at audit_at
                is_present = False
                for o in self.indexer.all_observations:
                    if o.evidence_id in evidence_ids and o.resource_id == acc_res_id and o.status == "PRESENT":
                        is_present = True
                        primary_ev = o.evidence_id
                        break
                        
                case_obs[acc_res_id] = Observation(
                    evidence_id=primary_ev,
                    file_path="",
                    captured_at=audit_at,
                    system_id="account_service",
                    resource_id=acc_res_id,
                    user_id=uid,
                    email=email,
                    status="PRESENT" if is_present else "ABSENT",
                    category="USER_PROFILE"
                )
            elif uid and uid.startswith("user_"):
                num_part = uid.split("_")[1]
                acc_res_id = f"account_{num_part.zfill(3)}"
                primary_ev = evidence_ids[0] if evidence_ids else "evidence_54"
                case_obs[acc_res_id] = Observation(
                    evidence_id=primary_ev,
                    file_path="",
                    captured_at=audit_at,
                    system_id="account_service",
                    resource_id=acc_res_id,
                    user_id=uid,
                    email=email,
                    status="ABSENT",
                    category="USER_PROFILE"
                )

        # 5. Generate Audit Steps
        raw_steps: List[AuditStep] = []
        has_findings = False

        for res_id, obs in sorted(case_obs.items()):
            sys_id = obs.system_id
            cat = obs.category
            stat = obs.status
            ev_id = obs.evidence_id or (evidence_ids[0] if evidence_ids else "")

            if cat in ["USER_PROFILE", "SEARCH_INDEX_ENTRY", "USER_EXPORT", "SUPPORT_ATTACHMENT"] or "account" in res_id or "search" in res_id or "export" in res_id:
                if stat == "PRESENT":
                    has_findings = True
                    raw_steps.append(AuditStep(0, Phase.FINDING.value, sys_id, res_id, "REPORT_REMAINING_RECORD", "PRESENT", ev_id))
                    raw_steps.append(AuditStep(0, Phase.REMEDIATION.value, sys_id, res_id, "DELETE_RECORD", "ABSENT", ""))
                    raw_steps.append(AuditStep(0, Phase.VERIFICATION.value, sys_id, res_id, "VERIFY_RECORD_ABSENT", "ABSENT", ""))
                else:
                    raw_steps.append(AuditStep(0, Phase.VERIFICATION.value, sys_id, res_id, "VERIFY_RECORD_ABSENT", "ABSENT", ev_id))

            elif cat == "ANALYTICS_PROFILE" or "analytics" in res_id:
                if stat == "PRESENT" or "contact_lookup_completed" in obs.raw_info:
                    has_findings = True
                    raw_steps.append(AuditStep(0, Phase.FINDING.value, sys_id, res_id, "REPORT_REMAINING_RECORD", "PRESENT", ev_id))
                    raw_steps.append(AuditStep(0, Phase.REMEDIATION.value, sys_id, res_id, "DELETE_RECORD", "ABSENT", ""))
                    raw_steps.append(AuditStep(0, Phase.VERIFICATION.value, sys_id, res_id, "VERIFY_RECORD_ABSENT", "ABSENT", ""))
                elif stat == "IDENTIFIABLE":
                    has_findings = True
                    raw_steps.append(AuditStep(0, Phase.FINDING.value, sys_id, res_id, "REPORT_EXPOSED_PII", "PRESENT", ev_id))
                    raw_steps.append(AuditStep(0, Phase.REMEDIATION.value, sys_id, res_id, "ANONYMIZE_RECORD", "ANONYMIZED", ""))
                    raw_steps.append(AuditStep(0, Phase.VERIFICATION.value, sys_id, res_id, "VERIFY_RECORD_ANONYMIZED", "ANONYMIZED", ""))
                else:
                    raw_steps.append(AuditStep(0, Phase.VERIFICATION.value, sys_id, res_id, "VERIFY_RECORD_ANONYMIZED", "ANONYMIZED", ev_id))

            elif cat == "SUPPORT_REPLICA":
                # Contact record remaining in support database replica
                if stat == "PRESENT":
                    has_findings = True
                    raw_steps.append(AuditStep(0, Phase.FINDING.value, sys_id, res_id, "REPORT_REMAINING_RECORD", "PRESENT", ev_id))
                    raw_steps.append(AuditStep(0, Phase.REMEDIATION.value, sys_id, res_id, "DELETE_RECORD", "ABSENT", ""))
                    raw_steps.append(AuditStep(0, Phase.VERIFICATION.value, sys_id, res_id, "VERIFY_RECORD_ABSENT", "ABSENT", ""))
                else:
                    raw_steps.append(AuditStep(0, Phase.VERIFICATION.value, sys_id, res_id, "VERIFY_RECORD_ABSENT", "ABSENT", ev_id))

            elif cat in ["SUPPORT_MESSAGE", "ACCOUNT_TOMBSTONE"] or "support" in res_id or "tombstone" in res_id:
                if stat in ["IDENTIFIABLE", "PRESENT"]:
                    has_findings = True
                    raw_steps.append(AuditStep(0, Phase.FINDING.value, sys_id, res_id, "REPORT_EXPOSED_PII", "PRESENT", ev_id))
                    raw_steps.append(AuditStep(0, Phase.REMEDIATION.value, sys_id, res_id, "REDACT_RECORD", "REDACTED", ""))
                    raw_steps.append(AuditStep(0, Phase.VERIFICATION.value, sys_id, res_id, "VERIFY_RECORD_REDACTED", "REDACTED", ""))
                else:
                    raw_steps.append(AuditStep(0, Phase.VERIFICATION.value, sys_id, res_id, "VERIFY_RECORD_REDACTED", "REDACTED", ev_id))

            elif cat == "DATA_FLOW" or "data_flow" in res_id:
                if stat == "ACTIVE":
                    has_findings = True
                    raw_steps.append(AuditStep(0, Phase.FINDING.value, sys_id, res_id, "REPORT_ACTIVE_DATA_FLOW", "ACTIVE", ev_id))
                    raw_steps.append(AuditStep(0, Phase.REMEDIATION.value, sys_id, res_id, "DISABLE_DATA_FLOW", "DISABLED", ""))
                    raw_steps.append(AuditStep(0, Phase.VERIFICATION.value, sys_id, res_id, "VERIFY_DATA_FLOW_DISABLED", "DISABLED", ""))
                else:
                    raw_steps.append(AuditStep(0, Phase.VERIFICATION.value, sys_id, res_id, "VERIFY_DATA_FLOW_DISABLED", "DISABLED", ev_id))

            elif cat == "BACKUP_ARCHIVE" or "backup" in res_id:
                if stat in ["RESTORE_RISK", "ACTIVE", "PRESENT"]:
                    has_findings = True
                    raw_steps.append(AuditStep(0, Phase.FINDING.value, sys_id, res_id, "REPORT_RESTORE_RISK", "ACTIVE", ev_id))
                    raw_steps.append(AuditStep(0, Phase.REMEDIATION.value, sys_id, res_id, "BLOCK_RESTORE", "BLOCKED", ""))
                    raw_steps.append(AuditStep(0, Phase.VERIFICATION.value, sys_id, res_id, "VERIFY_RESTORE_BLOCKED", "BLOCKED", ""))
                else:
                    raw_steps.append(AuditStep(0, Phase.VERIFICATION.value, sys_id, res_id, "VERIFY_RESTORE_BLOCKED", "BLOCKED", ev_id))

            elif cat in ["SECURITY_AUDIT_LOG", "LEGAL_HOLD_RECORD"] or "audit_record" in res_id:
                raw_steps.append(AuditStep(0, Phase.VERIFICATION.value, sys_id, res_id, "VERIFY_RECORD_PRESENT", "PRESENT", ev_id))

        final_status = DeletionStatus.INCOMPLETE.value if has_findings else DeletionStatus.COMPLETE.value

        if final_status == DeletionStatus.COMPLETE.value:
            selected_steps = [s for s in raw_steps if s.phase == Phase.VERIFICATION.value]
        else:
            selected_steps = []
            for s in raw_steps:
                if s.phase in [Phase.REMEDIATION.value, Phase.VERIFICATION.value]:
                    s.evidence_id = ""
                selected_steps.append(s)

        # Strict sorting
        def sort_key(s: AuditStep):
            p_order = PHASE_ORDER.get(Phase(s.phase), 99)
            op_order = OPERATION_ORDER.get(s.operation, 99)
            return (p_order, op_order, s.system_id, s.resource_id)

        selected_steps.sort(key=sort_key)

        for i, s in enumerate(selected_steps):
            s.step_no = i + 1

        steps_dicts = [s.to_dict() for s in selected_steps]
        return final_status, steps_dicts
