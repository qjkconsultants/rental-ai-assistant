# src/snug/agents/guardrails_agent.py
import re
from ..mcp.schema import MCPMessage
from ..logging import log
from ..core.audit import Audit
from ..core.db import DB
from typing import Dict, List, Any


class GuardrailsAgent:
    """
    Applies regex-based data-safety checks and redaction using guardrails_rules table.
    Can return plain dicts or MCPMessages depending on invocation.
    """

    def __init__(self, db: DB, audit: Audit):
        self.db = db
        self.audit = audit
        self._rules: Optional[List] = None

    def _load_rules(self):
        rows = self.db.conn.execute(
            "SELECT pattern, severity, description FROM guardrails_rules"
        ).fetchall()
        self._rules = [(re.compile(p, re.I), sev, desc) for (p, sev, desc) in rows]

    def _scan_profile(self, profile: Dict[str, Any]) -> List[Dict[str, str]]:
        if self._rules is None:
            self._load_rules()
        findings = []
        for k, v in profile.items():
            if not isinstance(v, str):
                continue
            for rx, sev, desc in self._rules:
                if rx.search(v):
                    findings.append({"field": k, "severity": sev, "reason": desc})
                    profile[k] = "[REDACTED]"
        return findings

    def scan_document(self, text: str) -> Dict[str, Any]:
        """Standalone text scan."""
        if self._rules is None:
            self._load_rules()
        issues = []
        for rx, sev, desc in self._rules:
            if re.search(rx, text, re.I):
                issues.append({"pattern": rx.pattern, "severity": sev, "description": desc})
        self.audit.log_event("guardrails", "scanned", f"found={len(issues)}")
        return {"issues": issues, "count": len(issues)}

    def handle(self, msg: MCPMessage) -> MCPMessage:
        p = msg.payload
        profile = p.get("profile", {})
        findings = self._scan_profile(profile)
        p["guardrails_findings"] = findings
        if findings:
            self.audit.log_event("guardrails", "flagged", f"{len(findings)} findings")
        log.info("guardrails_agent", findings=len(findings))
        return MCPMessage(
            sender="guardrails_agent",
            receiver="rag_agent",
            type="rag",
            payload=p,
            context=msg.context,
        )
