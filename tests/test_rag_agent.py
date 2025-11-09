import pytest
from snug.agents.rag_agent import RAGAgent
from snug.mcp.schema import MCPMessage
from snug.agents.memory_agent import MemoryAgent
from snug.core.vector_db import VectorDB


@pytest.mark.usefixtures("tmp_path")
def test_rag_agent_retrieval_and_memory_save(tmp_path, monkeypatch):
    """
    Ensure RAGAgent retrieves contextual data and stores memory for audit continuity.
    """
    # Isolate environment
    monkeypatch.chdir(tmp_path)

    # Setup mock memory + vector DB
    memory_agent = MemoryAgent(max_history=3)
    vector_client = VectorDB(collection_name="test_rental_kb")

    # Instantiate RAGAgent like in production
    agent = RAGAgent(vector_client=vector_client, memory_agent=memory_agent)

    # Construct simulated MCPMessage
    msg = MCPMessage(
        sender="test",
        receiver="rag",
        type="request",
        payload={
            "state": "NSW",
            "goal": "apply_rental",
            "profile": {
                "email": "nsw.tester@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "income": 85000,
            },
            "documents": ["dummy_form.pdf"],
            "guardrails_findings": [
                {"field": "email", "reason": "Detects email addresses", "severity": "medium"},
                {"field": "phone_number", "reason": "Detects 10-digit phone numbers", "severity": "medium"},
            ],
        },
        context={"source": "unit_test_rag_agent"}
    )

    # Run RAGAgent
    result = agent.handle(msg)
    payload = getattr(result, "payload", {})

    # ─────────────────────────────
    # ✅ Assertions
    # ─────────────────────────────
    assert isinstance(payload, dict), "RAGAgent should return a dictionary payload"
    assert "context_used" in payload, "RAGAgent should return contextual knowledge"
    assert "retrieved_docs" in payload["context_used"], "Context should include retrieved_docs list"
    assert isinstance(payload["context_used"]["retrieved_docs"], list)

    # Check that memory was actually updated
    mem_entries = memory_agent.memory
    assert len(mem_entries) > 0, "MemoryAgent should store at least one recall event"
    assert any("state" in m and m["state"] == "NSW" for m in mem_entries), "State NSW should appear in memory entries"

    # Validate persisted knowledge is recent
    last_entry = mem_entries[-1]
    assert "timestamp" in last_entry, "Each memory entry must include a timestamp"
    assert last_entry["state"] == "NSW"

    # Check payload integrity
    assert "state" in payload
    assert payload["state"] == "NSW"
    assert "profile" in payload
    assert "email" in payload["profile"]
