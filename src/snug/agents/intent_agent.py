from typing import Any, Dict
from ..mcp.schema import MCPMessage
from ..logging import log

class IntentAgent:
    """
    Extracts user intent & slots (state, goal, doc types).
    Uses rule-based extraction with optional LLM later.
    """
    def __init__(self, use_llm: bool = False, llm_client=None):
        self.use_llm = use_llm
        self.llm = llm_client

    def handle(self, msg: MCPMessage) -> MCPMessage:
        p = msg.payload
        # Infer intent and slots from provided form payload
        state = (p.get("state") or "").upper()
        docs = p.get("documents", [])
        goal = "apply_rental"

        slots: Dict[str, Any] = {
            "state": state,
            "has_payslip": any(d.lower().endswith(".pdf") for d in docs),
            "doc_count": len(docs),
        }
        log.info("intent_agent", state=state, doc_count=len(docs), goal=goal)

        # Attach intent/slots to payload for next agent
        new_payload = {**p, "intent": goal, "slots": slots}
        return MCPMessage(
            sender="intent_agent",
            receiver="canonical_agent",
            type="canonical",
            payload=new_payload,
            context=msg.context,
        )
