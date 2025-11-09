# src/snug/graph_multi.py
from langgraph.graph import StateGraph, START, END
from .mcp.schema import MCPMessage
from .logging import log


def build_multiagent_graph(
    intent_agent,
    canonical_agent,
    compliance_agent,
    guardrails_agent,
    rag_agent,
    response_agent,
):
    """
    Define and compile a multi-agent LangGraph:
      intent → canonical → compliance → guardrails → rag → response → END

    This ensures `response_agent` is the final node and always returns
    the MCPMessage, not the node name.
    """

    g = StateGraph(MCPMessage)

    # ─── Nodes ────────────────────────────────
    g.add_node("intent", intent_agent.handle)
    g.add_node("canonical", canonical_agent.handle)
    g.add_node("compliance", compliance_agent.handle)
    g.add_node("guardrails", guardrails_agent.handle)
    g.add_node("rag", rag_agent.handle)
    g.add_node("response", response_agent.handle)

    # ─── Edges ────────────────────────────────
    g.add_edge(START, "intent")
    g.add_edge("intent", "canonical")
    g.add_edge("canonical", "compliance")
    g.add_edge("compliance", "guardrails")
    g.add_edge("guardrails", "rag")
    g.add_edge("rag", "response")
    g.add_edge("response", END)

    # ─── Compile ──────────────────────────────
    compiled = g.compile()

    # ─── Wrap to guarantee final MCPMessage ───
    def invoke(msg: MCPMessage) -> MCPMessage:
        """Run the compiled graph and ensure final message is returned."""
        result = compiled.invoke(msg)
        if isinstance(result, MCPMessage):
            return result
        # Sometimes LangGraph returns node outputs by name
        if isinstance(result, dict) and "payload" in result:
            return MCPMessage(**result)
        log.info("graph_invoke_auto_wrap", result_type=str(type(result)))
        # fallback to original message if unclear
        return msg

    return type("CompiledMultiGraph", (), {"invoke": staticmethod(invoke)})
