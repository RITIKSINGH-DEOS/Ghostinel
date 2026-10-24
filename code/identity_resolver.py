"""
Identity Resolver for Ghostinel.
Maps current and historical identifiers across user_identities.csv and user_audit_log.csv.
"""
import csv
import hashlib
from typing import Dict, Optional, Set
from code.models import UserIdentity


class IdentityResolver:
    def __init__(self, identities_csv: str = "dataset/user_identities.csv", audit_log_csv: str = "dataset/user_audit_log.csv"):
        self.identities_csv = identities_csv
        self.audit_log_csv = audit_log_csv
        self.users_by_id: Dict[str, UserIdentity] = {}
        self.email_to_user_id: Dict[str, str] = {}
        self.phone_to_user_id: Dict[str, str] = {}
        self.hash_to_user_id: Dict[str, str] = {}
        self.name_to_user_id: Dict[str, str] = {}
        self.user_email_hashes: Dict[str, Set[str]] = {}
        self._load_data()

    def _load_data(self):
        # 1. Load primary identities
        with open(self.identities_csv, mode="r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                uid = row["user_id"]
                email = row["email"].strip().lower()
                phone = row["phone"].strip()
                name = row["name"].strip()
                email_hash = row["email_hash"].strip().lower()
                user = UserIdentity(
                    user_id=uid,
                    name=name,
                    email=row["email"].strip(),
                    phone=phone,
                    email_hash=email_hash,
                    updated_at=row["updated_at"].strip(),
                )
                self.users_by_id[uid] = user
                self.email_to_user_id[email] = uid
                if name:
                    self.name_to_user_id[name.lower()] = uid
                if phone:
                    self.phone_to_user_id[phone] = uid
                if email_hash:
                    self.hash_to_user_id[email_hash] = uid
                    self.user_email_hashes.setdefault(uid, set()).add(email_hash)

                # Also compute sha256 of primary email
                calc_h = hashlib.sha256(email.encode("utf-8")).hexdigest().lower()
                self.hash_to_user_id[calc_h] = uid
                self.user_email_hashes.setdefault(uid, set()).add(calc_h)

        # 2. Enrich with historical changes from audit log
        with open(self.audit_log_csv, mode="r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                uid = row["user_id"]
                field = row["field_name"]
                old_val = row["old_value"].strip()
                new_val = row["new_value"].strip()
                audit_id = row["audit_id"].strip()

                if uid in self.users_by_id:
                    user = self.users_by_id[uid]
                    user.audit_ids.add(audit_id)

                    if field == "email":
                        if old_val:
                            user.historical_emails.add(old_val)
                            self.email_to_user_id[old_val.lower()] = uid
                            h_old = hashlib.sha256(old_val.lower().encode("utf-8")).hexdigest().lower()
                            self.hash_to_user_id[h_old] = uid
                            self.user_email_hashes.setdefault(uid, set()).add(h_old)
                        if new_val:
                            self.email_to_user_id[new_val.lower()] = uid
                            h_new = hashlib.sha256(new_val.lower().encode("utf-8")).hexdigest().lower()
                            self.hash_to_user_id[h_new] = uid
                            self.user_email_hashes.setdefault(uid, set()).add(h_new)

                    elif field == "email_hash":
                        if old_val:
                            self.hash_to_user_id[old_val.lower()] = uid
                            self.user_email_hashes.setdefault(uid, set()).add(old_val.lower())
                        if new_val:
                            self.hash_to_user_id[new_val.lower()] = uid
                            self.user_email_hashes.setdefault(uid, set()).add(new_val.lower())

                    elif field == "phone":
                        if old_val:
                            user.historical_phones.add(old_val)
                            self.phone_to_user_id[old_val] = uid
                        if new_val:
                            self.phone_to_user_id[new_val] = uid

                    elif field == "name":
                        if old_val:
                            user.historical_names.add(old_val)
                            self.name_to_user_id[old_val.lower()] = uid
                        if new_val:
                            self.name_to_user_id[new_val.lower()] = uid

    def resolve_by_email(self, email: str) -> Optional[UserIdentity]:
        if not email:
            return None
        cleaned = email.strip().lower()
        uid = self.email_to_user_id.get(cleaned)
        if uid:
            return self.users_by_id.get(uid)
        return None

    def resolve_by_id(self, user_id: str) -> Optional[UserIdentity]:
        return self.users_by_id.get(user_id)

    def resolve_by_hash(self, email_hash: str) -> Optional[UserIdentity]:
        if not email_hash:
            return None
        uid = self.hash_to_user_id.get(email_hash.strip().lower())
        if uid:
            return self.users_by_id.get(uid)
        return None

    def resolve_by_name(self, name: str) -> Optional[UserIdentity]:
        if not name:
            return None
        uid = self.name_to_user_id.get(name.strip().lower())
        if uid:
            return self.users_by_id.get(uid)
        return None

    def get_all_identifiers(self, user: UserIdentity) -> Set[str]:
        """Returns all identity strings (emails, phones, name, id, email_hashes)."""
        tokens = {user.user_id, user.name, user.email, user.phone, user.email_hash}
        tokens.update(user.historical_emails)
        tokens.update(user.historical_phones)
        tokens.update(user.historical_names)
        tokens.update(self.user_email_hashes.get(user.user_id, set()))
        return {t for t in tokens if t}
