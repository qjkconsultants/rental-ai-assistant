from ..mcp.schema import MCPMessage
from ..logging import log

def _canon_state(s: str) -> str:
    if not s: return s
    s = s.upper()
    return "NSW" if s in ("NSW", "NEW SOUTH WALES") else ("VIC" if s in ("VIC", "VICTORIA") else s)

def _canon_date(d: str) -> str:
    # very light normalisation; full parser can be added later
    return d

class CanonicalAgent:
    """Normalises input into canonical fields & formats."""
    def handle(self, msg: MCPMessage) -> MCPMessage:
        p = msg.payload
        prof = p.get("profile", {}).copy()
        # Normalise common fields
        prof["dob"] = _canon_date(prof.get("dob", ""))
        p["profile"] = prof
        p["state"] = _canon_state(p.get("state", ""))
        log.info("canonical_agent", state=p["state"])
        return MCPMessage(
            sender="canonical_agent",
            receiver="compliance_agent",
            type="compliance",
            payload=p,
            context=msg.context,
        )
