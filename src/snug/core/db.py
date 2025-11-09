import sqlite3
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from ..logging import log
from ..settings import settings


class DB:
    """
    SQLite-backed database layer with safe auto-seeding.
    - Stores renter profiles, applications, and audit logs
    - Seeds compliance and guardrail rules only when tables are empty
    """

    def __init__(self, path: Optional[str] = None):
        self.conn = sqlite3.connect(path or settings.sqlite_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self._migrate()
        self._auto_seed_if_empty()

    # ─────────────────────────────────────────────
    # 📦 Schema Setup
    # ─────────────────────────────────────────────
    def _migrate(self):
        c = self.conn.cursor()
        schema = [
            """
            CREATE TABLE IF NOT EXISTS profiles (
                email TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                state TEXT,
                data TEXT NOT NULL,
                submitted_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity TEXT,
                action TEXT,
                details TEXT,
                ts TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS compliance_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                state TEXT,
                rule_name TEXT,
                rule_text TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS guardrails_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT,
                severity TEXT,
                description TEXT
            )
            """
        ]
        for stmt in schema:
            c.execute(stmt)
        self.conn.commit()
        log.info("db_migrated", message="SQLite schema initialized")

    # ─────────────────────────────────────────────
    # 🪴 Conditional Auto-Seeding
    # ─────────────────────────────────────────────
    def _auto_seed_if_empty(self):
        """Automatically seed tables if empty (first run only)."""
        compliance_count = self.count_rules("compliance_rules")
        guardrails_count = self.count_rules("guardrails_rules")

        if compliance_count == 0:
            log.info("db_autoseed", message="Compliance rules table empty, seeding...")
            self.seed_compliance_rules()
        if guardrails_count == 0:
            log.info("db_autoseed", message="Guardrails table empty, seeding...")
            self.seed_guardrails_rules()

    # ─────────────────────────────────────────────
    # 🌏 Multi-State Compliance Rules
    # ─────────────────────────────────────────────
    def seed_compliance_rules(self):
        """Populate NSW, VIC, and QLD with realistic compliance rules."""
        cur = self.conn.cursor()
        cur.execute("DELETE FROM compliance_rules;")

        state_rules = {
            "NSW": [
                ("proof_of_income", "Provide at least 2 recent payslips or a bank statement."),
                ("identity_check", "Provide driver’s licence or passport."),
                ("rental_history", "List your last two rental addresses or references."),
            ],
            "VIC": [
                ("employment_verification", "Provide employer letter or contract."),
                ("references", "Include at least 2 rental or personal references."),
                ("id_verification", "Submit photo ID or Medicare card."),
            ],
            "QLD": [
                ("income_validation", "Upload payslips or Centrelink statement."),
                ("rental_history", "Provide contact details of previous landlords."),
                ("proof_of_identity", "Upload driver’s licence or utility bill."),
            ],
        }

        rows = [(state, name, text) for state, rules in state_rules.items() for name, text in rules]
        cur.executemany(
            "INSERT INTO compliance_rules (state, rule_name, rule_text) VALUES (?, ?, ?)", rows
        )
        self.conn.commit()
        log.info("db_seeded_compliance", count=len(rows))

    # ─────────────────────────────────────────────
    # 🔒 Guardrails Rules
    # ─────────────────────────────────────────────
    def seed_guardrails_rules(self):
        """Insert static regex guardrails for sensitive data detection."""
        cur = self.conn.cursor()
        cur.execute("DELETE FROM guardrails_rules;")

        guardrails = [
            (r"\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b", "high", "Detects potential credit card numbers"),
            (r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "medium", "Detects email addresses"),
            (r"\b\d{10}\b", "medium", "Detects 10-digit phone numbers"),
            (r"\b\d{2}/\d{2}/\d{4}\b", "low", "Detects possible date of birth patterns"),
        ]

        cur.executemany(
            "INSERT INTO guardrails_rules (pattern, severity, description) VALUES (?, ?, ?)",
            guardrails,
        )
        self.conn.commit()
        log.info("db_seeded_guardrails", count=len(guardrails))

    # ─────────────────────────────────────────────
    # 👤 Profile Management
    # ─────────────────────────────────────────────
    def save_profile(self, email: str, data: Dict[str, Any]):
        """Insert or update a renter profile."""
        self.conn.execute(
            "INSERT OR REPLACE INTO profiles (email, data, updated_at) VALUES (?, ?, ?)",
            (email, json.dumps(data), datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()
        log.info("profile_saved", email=email)

    def get_profile(self, email: str) -> Optional[Dict[str, Any]]:
        """Retrieve renter profile."""
        row = self.conn.execute("SELECT data FROM profiles WHERE email=?", (email,)).fetchone()
        return json.loads(row[0]) if row else None

    # ─────────────────────────────────────────────
    # 🧾 Applications
    # ─────────────────────────────────────────────
    def save_application(self, application: Dict[str, Any]):
        """Persist a rental application to SQLite."""
        # 🔹 Try to retrieve email from multiple possible sources
        email = (
            application.get("email")
            or application.get("profile", {}).get("email")
        )
        if not email:
            raise ValueError("Application missing 'email' in both application and profile")

        state = application.get("state", "")
        try:
            self.conn.execute(
                """
                INSERT INTO applications (email, state, data, submitted_at)
                VALUES (?, ?, ?, ?)
                """,
                (email, state, json.dumps(application), datetime.now(timezone.utc).isoformat()),
            )
            self.conn.commit()
            log.info("application_saved", email=email, state=state)
        except Exception as e:
            log.error("application_save_failed", error=str(e), email=email, state=state)
            raise


    def list_applications(self) -> List[Dict[str, Any]]:
        """Return all stored applications."""
        rows = self.conn.execute("SELECT data FROM applications ORDER BY submitted_at DESC").fetchall()
        return [json.loads(r[0]) for r in rows]

    # ─────────────────────────────────────────────
    # 📜 Audit Trail
    # ─────────────────────────────────────────────
    def log_audit(self, entity: str, action: str, details: str):
        """Insert an audit log record for transparency."""
        self.conn.execute(
            "INSERT INTO audit_logs (entity, action, details, ts) VALUES (?, ?, ?, ?)",
            (entity, action, details, datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()
        log.info("audit_logged", entity=entity, action=action)

    # ─────────────────────────────────────────────
    # 🧩 Utilities
    # ─────────────────────────────────────────────
    def count_rules(self, table: str = "compliance_rules") -> int:
        """Return the number of rules in a table."""
        row = self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return int(row[0]) if row else 0
