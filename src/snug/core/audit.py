from datetime import datetime, timezone
from ..core.db import DB
from ..logging import log


class Audit:
    """
    Central audit logger.
    Records events (like application submitted, validation results, etc.)
    to both the database and structured logs.
    """

    def __init__(self, db: DB):
        self.db = db

    # ------------------------------------------------------------------
    # 🔹 Unified interface expected by app.py
    # ------------------------------------------------------------------
    def log_event(self, entity: str, action: str, details: str = ""):
        """
        Record an audit event to the database and structured logs.

        Example:
            audit.log_event("application", "submitted", "email=test@example.com")
        """
        ts = datetime.now(timezone.utc).isoformat()
        try:
            self.db.log_audit(entity, action, details)
            log.info("audit_event", entity=entity, action=action, ts=ts)
        except Exception as e:
            log.error("audit_failed", error=str(e), entity=entity, action=action)

    # ------------------------------------------------------------------
    # 🔹 Optional helper for common patterns
    # ------------------------------------------------------------------
    def log_application_submitted(self, email: str, state: str):
        self.log_event("application", "submitted", f"email={email}, state={state}")

    def log_profile_updated(self, email: str):
        self.log_event("profile", "updated", f"email={email}")
