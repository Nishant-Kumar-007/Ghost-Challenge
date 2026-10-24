"""Identity Resolution Module.

Resolves current and historical user identities from user_identities.csv
and user_audit_log.csv into a unified identity profile.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
import pandas as pd


@dataclass
class UserIdentity:
    user_id: str
    name: str
    primary_email: str
    emails: Set[str] = field(default_factory=set)
    phones: Set[str] = field(default_factory=set)
    email_hashes: Set[str] = field(default_factory=set)
    names: Set[str] = field(default_factory=set)
    updated_at: Optional[str] = None

    def matches_email(self, email: str) -> bool:
        if not email:
            return False
        return email.strip().lower() in self.emails

    def matches_phone(self, phone: str) -> bool:
        if not phone:
            return False
        clean_target = "".join(filter(str.isalnum, phone))
        for p in self.phones:
            if clean_target and clean_target == "".join(filter(str.isalnum, p)):
                return True
        return False

    def matches_hash(self, email_hash: str) -> bool:
        if not email_hash:
            return False
        return email_hash.strip().lower() in self.email_hashes


class IdentityResolver:
    """Loads and resolves user identities and historical changes."""

    def __init__(self, dataset_dir: str = "dataset"):
        self.dataset_dir = dataset_dir
        self.users: Dict[str, UserIdentity] = {}
        self.email_to_user_id: Dict[str, str] = {}
        self.phone_to_user_id: Dict[str, str] = {}
        self.hash_to_user_id: Dict[str, str] = {}
        self._load_identities()
        self._load_audit_log()

    def _load_identities(self) -> None:
        identities_path = os.path.join(self.dataset_dir, "user_identities.csv")
        if not os.path.exists(identities_path):
            raise FileNotFoundError(f"Missing {identities_path}")

        df = pd.read_csv(identities_path)
        for _, row in df.iterrows():
            uid = str(row["user_id"]).strip()
            name = str(row["name"]).strip() if pd.notna(row["name"]) else ""
            email = str(row["email"]).strip().lower() if pd.notna(row["email"]) else ""
            phone = str(row["phone"]).strip() if pd.notna(row["phone"]) else ""
            email_hash = str(row["email_hash"]).strip().lower() if pd.notna(row["email_hash"]) else ""
            updated_at = str(row["updated_at"]).strip() if pd.notna(row["updated_at"]) else None

            user = UserIdentity(
                user_id=uid,
                name=name,
                primary_email=email,
                updated_at=updated_at,
            )
            if email:
                user.emails.add(email)
                self.email_to_user_id[email] = uid
            if phone:
                user.phones.add(phone)
                clean_phone = "".join(filter(str.isalnum, phone))
                if clean_phone:
                    self.phone_to_user_id[clean_phone] = uid
            if email_hash:
                user.email_hashes.add(email_hash)
                self.hash_to_user_id[email_hash] = uid
            if name:
                user.names.add(name)

            self.users[uid] = user

    def _load_audit_log(self) -> None:
        audit_path = os.path.join(self.dataset_dir, "user_audit_log.csv")
        if not os.path.exists(audit_path):
            return

        df = pd.read_csv(audit_path)
        for _, row in df.iterrows():
            uid = str(row["user_id"]).strip()
            field_name = str(row["field_name"]).strip()
            old_val = str(row["old_value"]).strip() if pd.notna(row["old_value"]) else ""
            new_val = str(row["new_value"]).strip() if pd.notna(row["new_value"]) else ""

            if uid not in self.users:
                continue
            user = self.users[uid]

            if field_name == "email":
                if old_val:
                    old_email = old_val.lower()
                    user.emails.add(old_email)
                    self.email_to_user_id[old_email] = uid
                if new_val:
                    new_email = new_val.lower()
                    user.emails.add(new_email)
                    self.email_to_user_id[new_email] = uid

            elif field_name == "phone":
                if old_val:
                    user.phones.add(old_val)
                    clean_phone = "".join(filter(str.isalnum, old_val))
                    if clean_phone:
                        self.phone_to_user_id[clean_phone] = uid
                if new_val:
                    user.phones.add(new_val)
                    clean_phone = "".join(filter(str.isalnum, new_val))
                    if clean_phone:
                        self.phone_to_user_id[clean_phone] = uid

            elif field_name == "email_hash":
                if old_val:
                    old_h = old_val.lower()
                    user.email_hashes.add(old_h)
                    self.hash_to_user_id[old_h] = uid
                if new_val:
                    new_h = new_val.lower()
                    user.email_hashes.add(new_h)
                    self.hash_to_user_id[new_h] = uid

            elif field_name == "name":
                if old_val:
                    user.names.add(old_val)
                if new_val:
                    user.names.add(new_val)

    def resolve(self, identifier: str) -> Optional[UserIdentity]:
        """Resolve a user by user_id, current email, historical email, phone, or hash."""
        if not identifier:
            return None
        ident = identifier.strip()

        # Check by user_id
        if ident in self.users:
            return self.users[ident]

        # Check by email
        ident_lower = ident.lower()
        if ident_lower in self.email_to_user_id:
            return self.users[self.email_to_user_id[ident_lower]]

        # Check by hash
        if ident_lower in self.hash_to_user_id:
            return self.users[self.hash_to_user_id[ident_lower]]

        # Check by phone
        clean_phone = "".join(filter(str.isalnum, ident))
        if clean_phone in self.phone_to_user_id:
            return self.users[self.phone_to_user_id[clean_phone]]

        return None

    def get_all_users(self) -> Dict[str, UserIdentity]:
        return self.users
