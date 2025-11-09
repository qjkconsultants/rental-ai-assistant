import pytest
from snug.agents.compliance_agent import ComplianceAgent
from snug.core.db import DB
from snug.validation.state_validator import StateValidator
from snug.state_config import STATE_CONFIG
from snug.core.audit import Audit
from snug.mcp.schema import MCPMessage

@pytest.mark.usefixtures("tmp_path")
def test_compliance_detects_missing_fields(tmp_path, monkeypatch):
    """Ensure ComplianceAgent correctly identifies missing required fields."""
    # Create an isolated temporary DB
    monkeypatch.chdir(tmp_path)

    # Initialize dependencies
    db = DB()
    validator = StateValidator(STATE_CONFIG)
    audit = Audit(db)
    agent = ComplianceAgent(db, validator, audit)

    # Fake message wrapped in MCPMessage (LangGraph format)
    msg = MCPMessage(
        sender="test",
        receiver="compliance",
        type="request",
        payload={
            "state": "NSW",
            "profile": {"email": "a@b.com", "income": 40000},
            "extracted": {}
        },
        context={"test_id": "T001"}
    )

    # Run agent
    result = agent.handle(msg)

    # Extract normalized payload
    payload = getattr(result, "payload", {})
    assert "missing" in payload, "ComplianceAgent should report missing fields"
    assert isinstance(payload["missing"], list)
    assert len(payload["missing"]) > 0
    assert "income" not in payload["missing"], "Income should not be considered missing"
