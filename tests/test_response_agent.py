import pytest
from snug.agents.response_agent import ResponseAgent
from snug.mcp.schema import MCPMessage

@pytest.mark.usefixtures("tmp_path")
def test_response_agent_final_response_structure(tmp_path, monkeypatch):
    """
    Ensure ResponseAgent normalizes, sanitizes, and finalizes multi-agent output correctly.
    """

    agent = ResponseAgent()

    # ─────────────────────────────
    # 1️⃣ Simulate incoming multi-agent payload
    # ─────────────────────────────
    fake_payload = {
        "state": "VIC",
        "profile": {
            "email": "vic.tester@example.com",
            "first_name": "Alice",
            "last_name": "Brown",
            "phone_number": "[REDACTED]",
            "income": 62000,
        },
        "missing": ["rental_history", "references"],
        "guardrails_findings": [
            {"field": "email", "reason": "Detects email addresses", "severity": "medium"},
            {"field": "phone_number", "reason": "Detects 10-digit phone numbers", "severity": "medium"}
        ],
        "context_used": {
            "retrieved_docs": [
                "VIC applicants must provide ID, income, and references.",
                "Ensure documents are recent and legible."
            ],
            "guardrails_findings": []
        },
    }

    msg = MCPMessage(
        sender="guardrails",
        receiver="response",
        type="request",
        payload=fake_payload,
        context={"request_id": "test-response-agent-001"}
    )

    # ─────────────────────────────
    # 2️⃣ Run the agent
    # ─────────────────────────────
    result = agent.handle(msg)
    payload = getattr(result, "payload", {})

    # ─────────────────────────────
    # 3️⃣ Assertions
    # ─────────────────────────────
    assert isinstance(payload, dict), "ResponseAgent should return a dictionary payload"
    assert "state" in payload, "Payload must contain state"
    assert payload["state"] == "VIC", "State should be preserved"
    assert "email" in payload or "profile" in payload, "Email/profile must exist in final response"

    profile = payload.get("profile", {})
    assert isinstance(profile, dict)
    assert "first_name" in profile
    assert "last_name" in profile
    assert "income" in profile

    # Ensure missing fields are reflected
    assert "missing" in payload
    assert isinstance(payload["missing"], list)
    assert "references" in payload["missing"]

    # Ensure summary message is provided
    assert "message" in payload or "final_response" in payload, \
        "ResponseAgent should include a message summarizing output"

    # Confirm any sensitive values remain redacted
    redacted_fields = [v for v in profile.values() if isinstance(v, str) and "[REDACTED]" in v]
    assert len(redacted_fields) >= 1, "Sensitive fields should stay redacted"

    # Check timestamp and context integrity
    assert "timestamp" in payload, "Response should include a timestamp"
    assert "context_used" in payload, "Response should carry prior context"
    assert "retrieved_docs" in payload["context_used"]
