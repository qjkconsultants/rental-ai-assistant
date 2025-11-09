from snug.mcp.schema import MCPMessage
from snug.agents.intent_agent import IntentAgent

def test_intent_agent_slots():
    agent = IntentAgent()
    msg = MCPMessage(sender="t", receiver="intent_agent", type="intent",
                     payload={"state":"VIC", "documents": ["payslip.pdf"], "profile": {}}, context={})
    out = agent.handle(msg)
    assert out.type == "canonical"
    assert out.payload["slots"]["state"] == "VIC"
    assert out.payload["slots"]["has_payslip"] is True
