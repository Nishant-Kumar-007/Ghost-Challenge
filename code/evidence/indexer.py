"""Evidence Indexer Module.

Stores normalized evidence records into an indexed SQLite database
and supports time-bounded querying by user identifiers and resources.
"""

import os
import sqlite3
from typing import Any, Dict, List, Optional, Set
from code.evidence.ingestion import EvidenceIngestor
from code.identity.resolver import UserIdentity


class EvidenceIndexer:
    """Manages the SQLite evidence database and indexed lookups."""

    def __init__(self, db_path: str = ":memory:", dataset_dir: str = "dataset"):
        self.db_path = db_path
        self.dataset_dir = dataset_dir
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS evidence_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT NOT NULL,
            origin TEXT,
            captured_at TEXT NOT NULL,
            system_id TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            resource_type TEXT,
            customer_reference TEXT,
            email TEXT,
            phone TEXT,
            name TEXT,
            email_hash TEXT,
            state_observed TEXT,
            details TEXT
        );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ev_email ON evidence_records(email);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ev_cust_ref ON evidence_records(customer_reference);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ev_resource ON evidence_records(resource_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ev_system ON evidence_records(system_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ev_captured ON evidence_records(captured_at);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ev_file_id ON evidence_records(file_id);")
        self.conn.commit()

    def build_index(self) -> int:
        """Ingests all evidence files and populates SQLite index."""
        ingestor = EvidenceIngestor(self.dataset_dir)
        cur = self.conn.cursor()
        cur.execute("DELETE FROM evidence_records;")

        count = 0
        batch = []
        for record in ingestor.ingest_all():
            batch.append((
                record["file_id"],
                record["origin"],
                record["captured_at"],
                record["system_id"],
                record["resource_id"],
                record["resource_type"],
                record["customer_reference"],
                record["email"],
                record["phone"],
                record["name"],
                record["email_hash"],
                record["state_observed"],
                record["details"]
            ))
            count += 1
            if len(batch) >= 1000:
                cur.executemany("""
                INSERT INTO evidence_records (
                    file_id, origin, captured_at, system_id, resource_id,
                    resource_type, customer_reference, email, phone, name,
                    email_hash, state_observed, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, batch)
                self.conn.commit()
                batch.clear()

        if batch:
            cur.executemany("""
            INSERT INTO evidence_records (
                file_id, origin, captured_at, system_id, resource_id,
                resource_type, customer_reference, email, phone, name,
                email_hash, state_observed, details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, batch)
            self.conn.commit()

        return count

    def find_evidence_for_user(
        self,
        user: UserIdentity,
        audit_at: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Finds all evidence records for a user up to audit_at."""
        cur = self.conn.cursor()

        # Build query matching user_id or any of user's emails, phones, hashes
        conditions = []
        params: List[Any] = []

        # Customer reference (user_id)
        if user.user_id:
            conditions.append("customer_reference = ?")
            params.append(user.user_id)

        # Emails
        if user.emails:
            placeholders = ",".join("?" for _ in user.emails)
            conditions.append(f"email IN ({placeholders})")
            params.extend(list(user.emails))

        # Email hashes
        if user.email_hashes:
            placeholders = ",".join("?" for _ in user.email_hashes)
            conditions.append(f"email_hash IN ({placeholders})")
            params.extend(list(user.email_hashes))

        # Phones
        if user.phones:
            placeholders = ",".join("?" for _ in user.phones)
            conditions.append(f"phone IN ({placeholders})")
            params.extend(list(user.phones))

        if not conditions:
            return []

        where_clause = " OR ".join(f"({c})" for c in conditions)
        query = f"SELECT * FROM evidence_records WHERE ({where_clause})"

        if audit_at:
            query += " AND captured_at <= ?"
            params.append(audit_at)

        query += " ORDER BY captured_at ASC, id ASC"

        cur.execute(query, params)
        rows = cur.fetchall()
        return [dict(r) for r in rows]

    def find_evidence_by_resource(
        self,
        resource_id: str,
        audit_at: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Finds all evidence records for a specific resource ID up to audit_at."""
        cur = self.conn.cursor()
        query = "SELECT * FROM evidence_records WHERE resource_id = ?"
        params: List[Any] = [resource_id]

        if audit_at:
            query += " AND captured_at <= ?"
            params.append(audit_at)

        query += " ORDER BY captured_at ASC, id ASC"
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]

    def close(self) -> None:
        self.conn.close()
