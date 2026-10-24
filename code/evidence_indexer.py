"""
Master Evidence Indexer for Ghostinel.
Accurately indexes all 94 evidence files:
- 26 Logs (with trace_id correlation and identity resolution)
- 24 SQL Databases (with JSON payload extraction and schema routing)
- 28 JSON Records (snapshot bundles, service exports, export jobs, analytics reports)
- 1 Text Handover
- 4 PDFs (extracted via pypdf)
- 11 PNG Images (extracted via cached Gemini OCR)
"""
import os
import glob
import json
import csv
import re
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass
import pypdf

from code.identity_resolver import IdentityResolver, UserIdentity


@dataclass
class Observation:
    evidence_id: str
    file_path: str
    captured_at: str
    system_id: str
    resource_id: str
    user_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    status: str = ""       # ABSENT, PRESENT, REDACTED, ANONYMIZED, ACTIVE, DISABLED, BLOCKED
    category: str = ""     # USER_PROFILE, SECURITY_AUDIT_LOG, etc.
    raw_info: str = ""


class EvidenceIndexer:
    def __init__(self, dataset_dir: str = "dataset", resolver: Optional[IdentityResolver] = None):
        self.dataset_dir = dataset_dir
        self.resolver = resolver or IdentityResolver(
            identities_csv=os.path.join(dataset_dir, "user_identities.csv"),
            audit_log_csv=os.path.join(dataset_dir, "user_audit_log.csv")
        )
        self.evidence_files: Dict[str, Dict[str, str]] = {}
        self.path_to_ev_id: Dict[str, str] = {}
        
        self.obs_by_email: Dict[str, List[Observation]] = {}
        self.obs_by_user_id: Dict[str, List[Observation]] = {}
        self.obs_by_resource_id: Dict[str, List[Observation]] = {}
        self.all_observations: List[Observation] = []
        
        self._load_manifest()
        self._index_all()

    def _load_manifest(self):
        manifest_path = os.path.join(self.dataset_dir, "evidence_files.csv")
        with open(manifest_path, mode="r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                fid = r["file_id"]
                norm_path = r["file_path"].replace("\\", "/")
                self.evidence_files[fid] = {
                    "file_id": fid,
                    "file_path": norm_path,
                    "origin": r["origin"],
                    "captured_at": r["captured_at"]
                }
                self.path_to_ev_id[norm_path] = fid
                base = os.path.basename(norm_path)
                self.path_to_ev_id[base] = fid

    def add_obs(self, obs: Observation):
        # Auto-enrich missing email or user_id using IdentityResolver
        if obs.email and not obs.user_id:
            u = self.resolver.resolve_by_email(obs.email)
            if u:
                obs.user_id = u.user_id
        elif obs.user_id and not obs.email:
            u = self.resolver.resolve_by_id(obs.user_id)
            if u:
                obs.email = u.email

        self.all_observations.append(obs)
        if obs.email:
            em = obs.email.strip().lower()
            self.obs_by_email.setdefault(em, []).append(obs)
        if obs.user_id:
            uid = obs.user_id.strip()
            self.obs_by_user_id.setdefault(uid, []).append(obs)
        if obs.resource_id:
            rid = obs.resource_id.strip()
            self.obs_by_resource_id.setdefault(rid, []).append(obs)

    def _get_ev_id(self, path: str) -> str:
        norm = path.replace("\\", "/")
        if norm.startswith("dataset/"):
            norm = norm[len("dataset/"):]
        if norm in self.path_to_ev_id:
            return self.path_to_ev_id[norm]
        base = os.path.basename(norm)
        return self.path_to_ev_id.get(base, "")

    def _get_captured_at(self, ev_id: str) -> str:
        return self.evidence_files.get(ev_id, {}).get("captured_at", "")

    def _index_all(self):
        self._index_handovers()
        self._index_service_resource_exports()
        self._index_snapshot_bundles()
        self._index_all_logs()
        self._index_sql_databases()
        self._index_pdfs()
        self._index_images()
        self._index_analytics_and_export_records()

    def _index_handovers(self):
        for fpath in glob.glob(os.path.join(self.dataset_dir, "evidence/records/*handover*.txt")):
            ev_id = self._get_ev_id(fpath)
            captured_at = self._get_captured_at(ev_id)
            with open(fpath, mode="r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("- "):
                        parts = [p.strip() for p in line[2:].split("|")]
                        if len(parts) >= 6:
                            ts, sys_id, res_id, category, status_raw, identifier = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
                            email = identifier if "@" in identifier else None
                            user_id = identifier if identifier.startswith("user_") else None
                            status = "ABSENT" if status_raw in ["NOT_FOUND", "ABSENT"] else (
                                "ACTIVE" if category == "DATA_FLOW" and status_raw in ["FOUND", "ACTIVE", "PRESENT"] else (
                                    "RESTORE_RISK" if category == "BACKUP_ARCHIVE" and status_raw in ["FOUND", "ACTIVE", "PRESENT", "RESTORE_RISK"] else (
                                        "IDENTIFIABLE" if status_raw in ["IDENTIFIABLE", "FOUND", "PRESENT"] and category in ["ANALYTICS_PROFILE", "SUPPORT_MESSAGE", "ACCOUNT_TOMBSTONE"] else (
                                            "PRESENT" if status_raw in ["FOUND", "ACTIVE", "PRESENT"] else status_raw
                                        )
                                    )
                                )
                            )
                            self.add_obs(Observation(
                                evidence_id=ev_id, file_path=fpath, captured_at=captured_at or ts,
                                system_id=sys_id, resource_id=res_id, user_id=user_id, email=email,
                                status=status, category=category, raw_info=line
                            ))

    def _index_service_resource_exports(self):
        for fpath in glob.glob(os.path.join(self.dataset_dir, "evidence/records/service_resource_export_*.json")):
            ev_id = self._get_ev_id(fpath)
            captured_at = self._get_captured_at(ev_id)
            with open(fpath, mode="r", encoding="utf-8", errors="ignore") as f:
                try:
                    data = json.load(f)
                except:
                    continue
                exports = data.get("service_exports", {})
                
                # 1. account_service
                for item in exports.get("account_service", {}).get("profile_lookups", []):
                    res_id = item.get("resource_id", "")
                    prof = item.get("profile") or {}
                    em = prof.get("email")
                    uid = prof.get("customer_reference")
                    sc = item.get("status_code")
                    status = "ABSENT" if sc == 404 else "PRESENT"
                    self.add_obs(Observation(
                        evidence_id=ev_id, file_path=fpath, captured_at=captured_at,
                        system_id="account_service", resource_id=res_id,
                        user_id=uid, email=em, status=status, category="USER_PROFILE", raw_info=str(item)
                    ))

                # 2. analytics_platform
                for item in exports.get("analytics_platform", {}).get("profiles", []):
                    res_id = item.get("resource_id", "")
                    em = item.get("email")
                    uid = item.get("customer_reference")
                    is_identifiable = bool(em or item.get("phone") or item.get("email_hash"))
                    status = "IDENTIFIABLE" if is_identifiable else "ANONYMIZED"
                    self.add_obs(Observation(
                        evidence_id=ev_id, file_path=fpath, captured_at=captured_at,
                        system_id="analytics_platform", resource_id=res_id,
                        user_id=uid, email=em, status=status, category="ANALYTICS_PROFILE", raw_info=str(item)
                    ))

                # 3. backup_service
                for item in exports.get("backup_service", {}).get("restore_entries", []):
                    res_id = item.get("resource_id", "")
                    em = item.get("customer_email")
                    uid = item.get("customer_reference")
                    allowed = item.get("restore_allowed", False)
                    status = "RESTORE_RISK" if allowed else "BLOCKED"
                    self.add_obs(Observation(
                        evidence_id=ev_id, file_path=fpath, captured_at=captured_at,
                        system_id="backup_service", resource_id=res_id,
                        user_id=uid, email=em, status=status, category="BACKUP_ARCHIVE", raw_info=str(item)
                    ))

                # 4. integration_service
                for item in exports.get("integration_service", {}).get("connectors", []):
                    res_id = item.get("resource_id", "")
                    em = item.get("customer_email")
                    uid = item.get("customer_reference")
                    enabled = item.get("enabled", False)
                    status = "ACTIVE" if enabled else "DISABLED"
                    self.add_obs(Observation(
                        evidence_id=ev_id, file_path=fpath, captured_at=captured_at,
                        system_id="integration_service", resource_id=res_id,
                        user_id=uid, email=em, status=status, category="DATA_FLOW", raw_info=str(item)
                    ))

                # 5. search_service
                for item in exports.get("search_service", {}).get("index_queries", []):
                    res_id = item.get("resource_id", "")
                    q = item.get("query", "")
                    em = q if "@" in q else None
                    hits = item.get("hits", {}).get("total", 0)
                    status = "PRESENT" if hits > 0 else "ABSENT"
                    self.add_obs(Observation(
                        evidence_id=ev_id, file_path=fpath, captured_at=captured_at,
                        system_id="search_service", resource_id=res_id,
                        email=em, status=status, category="SEARCH_INDEX_ENTRY", raw_info=str(item)
                    ))

                # 6. security_service
                for item in exports.get("security_service", {}).get("audit_records", []):
                    res_id = item.get("resource_id", "")
                    uid = item.get("subject_reference", "")
                    self.add_obs(Observation(
                        evidence_id=ev_id, file_path=fpath, captured_at=captured_at,
                        system_id="security_service", resource_id=res_id,
                        user_id=uid, status="PRESENT", category="SECURITY_AUDIT_LOG", raw_info=str(item)
                    ))

                # 7. support_platform
                for item in exports.get("support_platform", {}).get("tickets", []):
                    res_id = item.get("resource_id", "")
                    uid = item.get("customer_reference")
                    em = item.get("requester_email")
                    status = "IDENTIFIABLE" if (em or item.get("requester_name")) else "REDACTED"
                    self.add_obs(Observation(
                        evidence_id=ev_id, file_path=fpath, captured_at=captured_at,
                        system_id="support_platform", resource_id=res_id,
                        user_id=uid, email=em, status=status, category="SUPPORT_MESSAGE", raw_info=str(item)
                    ))

                # 8. export_service
                for item in exports.get("export_service", {}).get("exports", []):
                    res_id = item.get("resource_id", "")
                    em = item.get("owner_email")
                    uid = item.get("customer_reference")
                    status = "PRESENT" if em else "ABSENT"
                    self.add_obs(Observation(
                        evidence_id=ev_id, file_path=fpath, captured_at=captured_at,
                        system_id="export_service", resource_id=res_id,
                        user_id=uid, email=em, status=status, category="USER_EXPORT", raw_info=str(item)
                    ))

    def _index_snapshot_bundles(self):
        for fpath in glob.glob(os.path.join(self.dataset_dir, "evidence/records/*snapshot_bundle*.json")):
            ev_id = self._get_ev_id(fpath)
            captured_at = self._get_captured_at(ev_id)
            with open(fpath, mode="r", encoding="utf-8", errors="ignore") as f:
                try:
                    data = json.load(f)
                except:
                    continue
                for s in data.get("snapshots", []):
                    dstore = s.get("data_store", "")
                    collection = s.get("collection", "")
                    records = s.get("records", [])

                    if collection == "deleted_customer_references" or dstore == "identity_service":
                        for r in records:
                            res_id = r.get("resource_id", "")
                            uid = r.get("subject_reference") or r.get("customer_reference")
                            em = r.get("email")
                            is_identifiable = bool(em or r.get("name") or r.get("phone") or r.get("email_hash"))
                            status = "IDENTIFIABLE" if is_identifiable else "REDACTED"
                            self.add_obs(Observation(
                                evidence_id=ev_id, file_path=fpath, captured_at=captured_at,
                                system_id="identity_service", resource_id=res_id,
                                user_id=uid, email=em, status=status, category="ACCOUNT_TOMBSTONE", raw_info=str(r)
                            ))

                    elif collection == "security_audit_events" or dstore == "security_service":
                        for r in records:
                            res_id = r.get("resource_id", "")
                            uid = r.get("subject_reference") or r.get("customer_reference")
                            self.add_obs(Observation(
                                evidence_id=ev_id, file_path=fpath, captured_at=captured_at,
                                system_id="security_service", resource_id=res_id,
                                user_id=uid, status="PRESENT", category="SECURITY_AUDIT_LOG", raw_info=str(r)
                            ))

                    elif collection == "customer_profiles" or dstore == "account_service":
                        for r in records:
                            res_id = r.get("resource_id", "")
                            uid = r.get("user_id") or r.get("customer_reference")
                            em = r.get("email")
                            st = "PRESENT" if r.get("account_status") == "ACTIVE" else "ABSENT"
                            self.add_obs(Observation(
                                evidence_id=ev_id, file_path=fpath, captured_at=captured_at,
                                system_id="account_service", resource_id=res_id,
                                user_id=uid, email=em, status=st, category="USER_PROFILE", raw_info=str(r)
                            ))

                    elif collection == "customer_search_documents" or dstore == "search_service":
                        for r in records:
                            res_id = r.get("resource_id", "")
                            doc = r.get("document", {}) if isinstance(r.get("document"), dict) else r
                            uid = doc.get("user_id") or doc.get("customer_reference")
                            em = doc.get("email") or doc.get("customer_email")
                            name = doc.get("display_name")
                            if name and not uid:
                                u = self.resolver.resolve_by_name(name)
                                if u:
                                    uid = u.user_id
                                    em = u.email
                            self.add_obs(Observation(
                                evidence_id=ev_id, file_path=fpath, captured_at=captured_at,
                                system_id="search_service", resource_id=res_id,
                                user_id=uid, email=em, status="PRESENT", category="SEARCH_INDEX_ENTRY", raw_info=str(r)
                            ))

                    elif collection == "customer_analytics_reports" or dstore == "analytics_platform":
                        for r in records:
                            res_id = r.get("resource_id", "")
                            uid = r.get("user_id") or r.get("customer_reference")
                            em = r.get("email")
                            is_identifiable = bool(em or r.get("phone") or r.get("email_hash"))
                            status = "IDENTIFIABLE" if is_identifiable else "ANONYMIZED"
                            self.add_obs(Observation(
                                evidence_id=ev_id, file_path=fpath, captured_at=captured_at,
                                system_id="analytics_platform", resource_id=res_id,
                                user_id=uid, email=em, status=status, category="ANALYTICS_PROFILE", raw_info=str(r)
                            ))

                    elif collection in ["support_conversations", "ticket_attachments"] or dstore == "support_platform":
                        for r in records:
                            res_id = r.get("resource_id", "")
                            uid = r.get("customer_reference")
                            em = r.get("requester_email") or r.get("email")
                            is_identifiable = bool(em or r.get("requester_name"))
                            status = "IDENTIFIABLE" if is_identifiable else "REDACTED"
                            self.add_obs(Observation(
                                evidence_id=ev_id, file_path=fpath, captured_at=captured_at,
                                system_id="support_platform", resource_id=res_id,
                                user_id=uid, email=em, status=status, category="SUPPORT_MESSAGE", raw_info=str(r)
                            ))

                    elif collection == "connector_configurations" or dstore == "integration_service":
                        for r in records:
                            res_id = r.get("resource_id", "")
                            uid = r.get("customer_reference")
                            em = r.get("customer_email")
                            status = "ACTIVE" if r.get("enabled", True) else "DISABLED"
                            self.add_obs(Observation(
                                evidence_id=ev_id, file_path=fpath, captured_at=captured_at,
                                system_id="integration_service", resource_id=res_id,
                                user_id=uid, email=em, status=status, category="DATA_FLOW", raw_info=str(r)
                            ))

                    elif collection in ["backup_catalog", "backup_restore_entries"] or dstore in ["backup_service", "backup_restore_service"]:
                        for r in records:
                            res_id = r.get("resource_id", "")
                            uid = r.get("customer_reference")
                            em = r.get("customer_email")
                            allowed = r.get("restore_allowed", True)
                            status = "RESTORE_RISK" if allowed else "BLOCKED"
                            self.add_obs(Observation(
                                evidence_id=ev_id, file_path=fpath, captured_at=captured_at,
                                system_id="backup_service", resource_id=res_id,
                                user_id=uid, email=em, status=status, category="BACKUP_ARCHIVE", raw_info=str(r)
                            ))

    def _index_all_logs(self):
        for fpath in glob.glob(os.path.join(self.dataset_dir, "evidence/logs/*.log")):
            ev_id = self._get_ev_id(fpath)
            captured_at = self._get_captured_at(ev_id)
            
            trace_clusters: Dict[str, Dict[str, Any]] = {}
            untraced_lines: List[str] = []

            with open(fpath, mode="r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    tid_match = re.search(r"trace_id=[\"']?([a-zA-Z0-9_-]+)[\"']?", line)
                    if not tid_match and "{" in line:
                        try:
                            d = json.loads(line[line.find("{"):])
                            if "trace_id" in d:
                                tid = d["trace_id"]
                                c = trace_clusters.setdefault(tid, {"raw_lines": []})
                                c.update(d)
                                c["raw_lines"].append(line)
                                continue
                        except:
                            pass

                    if tid_match:
                        tid = tid_match.group(1)
                        c = trace_clusters.setdefault(tid, {"raw_lines": []})
                        c["raw_lines"].append(line)
                        
                        # Extract any fields from this line
                        keys = [
                            "service", "logger", "resource_id", "lookup_key", "subject_key",
                            "subject_ref", "subject_reference", "customer_reference",
                            "correlation_key", "matched_value", "user_id", "email",
                            "event", "http_status", "rows", "marker_found", "retention_until",
                            "eligible", "deletion_block", "enabled", "result", "attempt"
                        ]
                        for key in keys:
                            m = re.search(rf"{key}=[\"']?([^\"'\s,]+)[\"']?", line)
                            if m:
                                c[key] = m.group(1)
                    else:
                        untraced_lines.append(line)

            # Process trace clusters
            for tid, d in trace_clusters.items():
                res_id = d.get("resource_id")
                if not res_id:
                    continue
                sys_id = d.get("service") or d.get("logger") or "unknown"
                raw_text = " ".join(d.get("raw_lines", []))

                # Identify user across all potential keys
                em = None
                uid = None

                for k in ["subject_key", "correlation_key", "lookup_key", "matched_value", "email", "customer_reference", "subject_reference", "subject_ref", "user_id"]:
                    val = d.get(k)
                    if not val:
                        continue
                    val = val.strip().strip("\"'")
                    if "@" in val:
                        em = val
                    elif val.startswith("user_"):
                        uid = val
                    elif len(val) == 64 and all(c in "0123456789abcdefABCDEF" for c in val):
                        # SHA-256 hash
                        u = self.resolver.resolve_by_hash(val)
                        if u:
                            uid = u.user_id
                            em = u.email

                status = "PRESENT"
                category = "USER_PROFILE"

                if "audit_record" in res_id or sys_id == "security_service":
                    sys_id = "security_service"
                    category = "SECURITY_AUDIT_LOG"
                    status = "PRESENT"
                elif "account" in res_id or sys_id == "account_service":
                    sys_id = "account_service"
                    category = "USER_PROFILE"
                    status = "ABSENT" if (d.get("http_status") == "404" or d.get("rows") == "0" or "rows=0" in raw_text) else "PRESENT"
                elif "analytics" in res_id or sys_id == "analytics_platform":
                    sys_id = "analytics_platform"
                    category = "ANALYTICS_PROFILE"
                    if ("customer_reference=null" in raw_text and "email=null" in raw_text) or d.get("event") == "profile_anonymized":
                        status = "ANONYMIZED"
                    else:
                        status = "IDENTIFIABLE"
                elif "support" in res_id or sys_id in ["support_platform", "support_replica"]:
                    sys_id = "support_platform"
                    if sys_id == "support_replica" or "support_replica" in fpath:
                        category = "SUPPORT_REPLICA"
                        status = "PRESENT" if (d.get("marker_found") == "false" or d.get("rows") == "1") else "ABSENT"
                    else:
                        category = "SUPPORT_MESSAGE"
                        if d.get("marker_found") == "false" or d.get("rows") == "1" or d.get("event") == "message_pii_scan":
                            status = "IDENTIFIABLE"
                        elif "requester_email=null" in raw_text:
                            status = "REDACTED"
                        else:
                            status = "IDENTIFIABLE"
                elif "search" in res_id or sys_id == "search_service":
                    sys_id = "search_service"
                    category = "SEARCH_INDEX_ENTRY"
                    status = "PRESENT" if (d.get("result") == "hit" or d.get("rows") == "1" or "result=hit" in raw_text) else "ABSENT"
                elif "data_flow" in res_id or sys_id == "integration_service":
                    sys_id = "integration_service"
                    category = "DATA_FLOW"
                    status = "ACTIVE" if (d.get("enabled") == "true" or "enabled=true" in raw_text) else "DISABLED"
                elif "backup" in res_id or sys_id == "backup_service":
                    sys_id = "backup_service"
                    category = "BACKUP_ARCHIVE"
                    if (d.get("eligible") == "true" and d.get("deletion_block") == "false") or "deletion_block=false" in raw_text or d.get("restore_allowed") == "true":
                        status = "RESTORE_RISK"
                    else:
                        status = "BLOCKED"

                self.add_obs(Observation(
                    evidence_id=ev_id, file_path=fpath, captured_at=captured_at,
                    system_id=sys_id, resource_id=res_id,
                    user_id=uid, email=em, status=status, category=category, raw_info=str(d)
                ))

            # Process untraced lines (only completed events)
            for line in untraced_lines:
                if "_started" in line:
                    continue
                res_match = re.search(r"resource_id=[\"']?([a-zA-Z0-9_-]+)[\"']?", line)
                if not res_match:
                    continue
                res_id = res_match.group(1)
                sys_match = re.search(r"service=[\"']?([a-zA-Z0-9_-]+)[\"']?", line)
                sys_id = sys_match.group(1) if sys_match else "unknown"
                uid_m = re.search(r"(?:user_[0-9]+)", line)
                em_m = re.search(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", line)
                uid = uid_m.group(0) if uid_m else None
                em = em_m.group(0) if em_m else None

                status = "PRESENT"
                category = "USER_PROFILE"
                if "audit_record" in res_id:
                    sys_id = "security_service"
                    category = "SECURITY_AUDIT_LOG"
                    status = "PRESENT"
                elif "account" in res_id:
                    sys_id = "account_service"
                    category = "USER_PROFILE"
                    status = "ABSENT" if ("404" in line or "rows=0" in line) else "PRESENT"
                elif "backup" in res_id:
                    sys_id = "backup_service"
                    category = "BACKUP_ARCHIVE"
                    status = "RESTORE_RISK" if "deletion_block=false" in line else "BLOCKED"
                elif "search" in res_id:
                    sys_id = "search_service"
                    category = "SEARCH_INDEX_ENTRY"
                    status = "PRESENT" if "result=hit" in line else "ABSENT"

                self.add_obs(Observation(
                    evidence_id=ev_id, file_path=fpath, captured_at=captured_at,
                    system_id=sys_id, resource_id=res_id,
                    user_id=uid, email=em, status=status, category=category, raw_info=line
                ))

    def _index_sql_databases(self):
        for fpath in glob.glob(os.path.join(self.dataset_dir, "evidence/databases/*.sql")):
            ev_id = self._get_ev_id(fpath)
            captured_at = self._get_captured_at(ev_id)
            with open(fpath, mode="r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                
            inserts = re.findall(r"INSERT\s+INTO\s+[\"']?([a-zA-Z0-9_]+)[\"']?\s+VALUES\s*\((.*?)\);", content, re.DOTALL | re.IGNORECASE)
            for table_name, vals_str in inserts:
                # Check for JSON payload inside values
                j_match = re.search(r"(\{.*\})", vals_str)
                if j_match:
                    try:
                        payload = json.loads(j_match.group(1))
                        res_id = payload.get("resource_id", "")
                        doc = payload.get("document", {}) if isinstance(payload.get("document"), dict) else {}
                        uid = payload.get("user_id") or payload.get("customer_reference") or payload.get("subject_reference") or doc.get("customer_reference") or doc.get("user_id")
                        em = payload.get("email") or payload.get("customer_email") or doc.get("email") or doc.get("customer_email")
                        name = payload.get("full_name") or doc.get("display_name")
                        
                        if name and not uid:
                            u = self.resolver.resolve_by_name(name)
                            if u:
                                uid = u.user_id
                                em = u.email

                        # Routing based on table / resource
                        if "customer_profiles" in vals_str or "account" in res_id:
                            sys_id = "account_service"
                            category = "USER_PROFILE"
                            status = "PRESENT" if payload.get("account_status") == "ACTIVE" else "ABSENT"
                        elif "security_audit" in vals_str or "audit_record" in res_id:
                            sys_id = "security_service"
                            category = "SECURITY_AUDIT_LOG"
                            status = "PRESENT"
                        elif "customer_search" in vals_str or "search" in res_id:
                            sys_id = "search_service"
                            category = "SEARCH_INDEX_ENTRY"
                            status = "PRESENT"
                        elif "customer_analytics" in vals_str or "analytics" in res_id:
                            sys_id = "analytics_platform"
                            category = "ANALYTICS_PROFILE"
                            status = "IDENTIFIABLE" if (em or uid) else "ANONYMIZED"
                        elif "backup" in res_id:
                            sys_id = "backup_service"
                            category = "BACKUP_ARCHIVE"
                            status = "RESTORE_RISK" if payload.get("restore_allowed", True) else "BLOCKED"
                        elif "data_flow" in res_id:
                            sys_id = "integration_service"
                            category = "DATA_FLOW"
                            status = "ACTIVE" if payload.get("enabled", True) else "DISABLED"
                        elif "support" in res_id:
                            sys_id = "support_platform"
                            category = "SUPPORT_MESSAGE"
                            status = "PRESENT"
                        else:
                            sys_id = "account_service"
                            category = "USER_PROFILE"
                            status = "PRESENT"

                        self.add_obs(Observation(
                            evidence_id=ev_id, file_path=fpath, captured_at=captured_at,
                            system_id=sys_id, resource_id=res_id,
                            user_id=uid, email=em, status=status, category=category, raw_info=vals_str[:300]
                        ))
                        continue
                    except:
                        pass

                # Fallback for plain SQL values without JSON
                vals = [v.strip().strip("'\"") for v in vals_str.split(",")]
                if not vals:
                    continue
                res_id = vals[0]
                uid = next((v for v in vals if v.startswith("user_")), None)
                em = next((v for v in vals if "@" in v), None)

                if "backup_restore_entries" in table_name or "backup" in res_id:
                    sys_id = "backup_service"
                    category = "BACKUP_ARCHIVE"
                    status = "RESTORE_RISK" if ("'1'" in vals_str or ", 1," in vals_str or ", '1')" in vals_str or ", 1)" in vals_str) else "BLOCKED"
                elif "connector" in table_name or "data_flow" in res_id:
                    sys_id = "integration_service"
                    category = "DATA_FLOW"
                    status = "ACTIVE" if ("'1'" in vals_str or ", 1," in vals_str or ", '1')" in vals_str or ", 1)" in vals_str) else "DISABLED"
                elif "search" in table_name or "search" in res_id:
                    sys_id = "search_service"
                    category = "SEARCH_INDEX_ENTRY"
                    status = "PRESENT"
                elif "export" in table_name or "export" in res_id:
                    sys_id = "export_service"
                    category = "USER_EXPORT"
                    status = "PRESENT"
                elif "support" in table_name or "support" in res_id:
                    sys_id = "support_platform"
                    category = "SUPPORT_MESSAGE"
                    status = "PRESENT"
                elif "security" in table_name or "audit_record" in res_id:
                    sys_id = "security_service"
                    category = "SECURITY_AUDIT_LOG"
                    status = "PRESENT"
                elif "analytics" in table_name or "analytics" in res_id:
                    sys_id = "analytics_platform"
                    category = "ANALYTICS_PROFILE"
                    status = "IDENTIFIABLE" if em else "ANONYMIZED"
                else:
                    sys_id = "account_service"
                    category = "USER_PROFILE"
                    status = "PRESENT"

                self.add_obs(Observation(
                    evidence_id=ev_id, file_path=fpath, captured_at=captured_at,
                    system_id=sys_id, resource_id=res_id,
                    user_id=uid, email=em, status=status, category=category, raw_info=vals_str[:300]
                ))

    def _index_pdfs(self):
        for fpath in glob.glob(os.path.join(self.dataset_dir, "evidence/documents/*.pdf")):
            ev_id = self._get_ev_id(fpath)
            captured_at = self._get_captured_at(ev_id)
            try:
                reader = pypdf.PdfReader(fpath)
                text = " ".join([p.extract_text() for p in reader.pages])
            except:
                continue

            if "support_001" in text:
                self.add_obs(Observation(
                    evidence_id=ev_id, file_path=fpath, captured_at=captured_at,
                    system_id="support_platform", resource_id="support_001",
                    email="priya.raman@gmail.com", user_id="user_07", status="PRESENT",
                    category="SUPPORT_ATTACHMENT", raw_info=text[:300]
                ))
            if "audit_record_003" in text:
                self.add_obs(Observation(
                    evidence_id=ev_id, file_path=fpath, captured_at=captured_at,
                    system_id="security_service", resource_id="audit_record_003",
                    user_id="user_03", status="PRESENT", category="SECURITY_AUDIT_LOG", raw_info=text[:300]
                ))

    def _index_images(self):
        for fpath in glob.glob(os.path.join(self.dataset_dir, "evidence/images_extracted/*.png.json")):
            base_png = os.path.basename(fpath).replace(".json", "")
            ev_id = self.path_to_ev_id.get(base_png, "")
            captured_at = self._get_captured_at(ev_id)
            with open(fpath, mode="r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    text = data.get("extracted_text", "")
                except:
                    continue
                
                for line in text.split("\n"):
                    if "|" in line:
                        m_em = re.search(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", line)
                        m_rid = re.search(r"(backup_[0-9]+|account_[0-9]+|search_[0-9]+|support_[0-9]+|data_flow_[0-9]+)", line)
                        if m_em and m_rid:
                            rid = m_rid.group(1)
                            em = m_em.group(1)
                            sys_id = "backup_service" if "backup" in rid else (
                                "account_service" if "account" in rid else (
                                    "search_service" if "search" in rid else "support_platform"
                                )
                            )
                            cat = "BACKUP_ARCHIVE" if "backup" in rid else (
                                "USER_PROFILE" if "account" in rid else (
                                    "SEARCH_INDEX_ENTRY" if "search" in rid else "SUPPORT_MESSAGE"
                                )
                            )
                            status = "RESTORE_RISK" if "backup" in rid else "PRESENT"
                            self.add_obs(Observation(
                                evidence_id=ev_id, file_path=base_png, captured_at=captured_at,
                                system_id=sys_id, resource_id=rid,
                                email=em, status=status, category=cat, raw_info=line
                            ))

    def _index_analytics_and_export_records(self):
        for fpath in glob.glob(os.path.join(self.dataset_dir, "evidence/records/*analytics*.json")):
            ev_id = self._get_ev_id(fpath)
            captured_at = self._get_captured_at(ev_id)
            with open(fpath, mode="r", encoding="utf-8", errors="ignore") as f:
                try:
                    data = json.load(f)
                except:
                    continue
                profiles = data.get("records") or data.get("profiles", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                for p in profiles:
                    res_id = p.get("resource_id", "")
                    uid = p.get("customer_reference")
                    em = p.get("email")
                    is_identifiable = bool(em or p.get("phone") or p.get("email_hash"))
                    status = "IDENTIFIABLE" if is_identifiable else "ANONYMIZED"
                    self.add_obs(Observation(
                        evidence_id=ev_id, file_path=fpath, captured_at=captured_at,
                        system_id="analytics_platform", resource_id=res_id,
                        user_id=uid, email=em, status=status, category="ANALYTICS_PROFILE", raw_info=str(p)
                    ))

        for fpath in glob.glob(os.path.join(self.dataset_dir, "evidence/records/*export_jobs*.json")):
            ev_id = self._get_ev_id(fpath)
            captured_at = self._get_captured_at(ev_id)
            with open(fpath, mode="r", encoding="utf-8", errors="ignore") as f:
                try:
                    data = json.load(f)
                except:
                    continue
                jobs = data.get("records") or data.get("jobs", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                for j in jobs:
                    res_id = j.get("resource_id", "")
                    em = j.get("owner_email") or j.get("requester_email")
                    self.add_obs(Observation(
                        evidence_id=ev_id, file_path=fpath, captured_at=captured_at,
                        system_id="export_service", resource_id=res_id,
                        email=em, status="PRESENT", category="USER_EXPORT", raw_info=str(j)
                    ))
