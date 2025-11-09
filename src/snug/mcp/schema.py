from pydantic import BaseModel
from typing import Any, Dict, Optional

class MCPMessage(BaseModel):
    """Minimal MCP-style envelope used by all agents."""
    sender: str
    receiver: str
    type: str                 # "intent", "canonical", "compliance", "guardrails", "rag", "response"
    payload: Dict[str, Any]   # application state / fields / extracted info
    context: Optional[Dict[str, Any]] = {}
