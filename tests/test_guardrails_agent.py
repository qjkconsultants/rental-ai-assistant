import pytest
from snug.agents.guardrails_agent import GuardrailsAgent
from snug.core.db import DB
from snug.core.audit import Audit
from snug.mcp.schema import MCPMessage

@pytest.mark.usefixtures("tmp_path")
def test_guardrails_detects_sensitive_fields(tmp_path, monkeypatch):
    """Ensure GuardrailsAgent flags sensitive fields such as emails and phone numbers."""
    # Isolate DB in a temporary folder
    monkeypatch.chdir(tmp_path)

    # Setup dependencies
    db = DB()
    audit = Audit(db)
    agent = GuardrailsAgent(db, audit)

    # Construct a fake MCPMessage input
    msg = MCPMessage(
        sender="test",
        receiver="guardrails",
        type="request",
        payload={
            "state": "NSW",
            "profile": {
                "email": "alice.smith@example.com",
                "phone_number": "0400123456",
                "employer_contact": "0400789123",
                "first_name": "Alice",
                "last_name": "Smith",
            },
            "documents": ["dummy.pdf"]
        },
        context={"test_case": "guardrails_detection"}
    )

    # Run the guardrails check
    result = agent.handle(msg)

    # Extract payload safely
    payload = getattr(result, "payload", {})

    # ─────────────────────────────
    # ✅ Assertions
    # ─────────────────────────────
    assert isinstance(payload, dict), "GuardrailsAgent should return a dict payload"
    assert "guardrails_findings" in payload, "GuardrailsAgent should include guardrails_findings key"

    findings = payload["guardrails_findings"]
    assert isinstance(findings, list)
    assert len(findings) >= 1, "Expected at least one sensitive field detection"

    # Extract all field names from findings
    flagged_fields = [f["field"] for f in findings]

    # Confirm expected sensitive fields were detected
    assert "email" in flagged_fields
    assert "phone_number" in flagged_fields or "employer_contact" in flagged_fields

    # Verify sensitive data was redacted
    profile = payload["profile"]
    assert "[REDACTED]" in profile["email"], "Email should be redacted"
    assert "[REDACTED]" in profile["phone_number"], "Phone should be redacted"
