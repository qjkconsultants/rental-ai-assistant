# src/snug/graph.py
from typing import TypedDict, Dict, Any, List
from langgraph.graph import StateGraph, START, END

class AppState(TypedDict, total=False):
    state: str
    profile: Dict[str, Any]
    documents: List[str]
    extracted: Dict[str, Any]
    missing: List[str]
    errors: List[str]

def build_graph(profile_agent, doc_agent, reason_agent):
    # define the stateful workflow
    workflow = StateGraph(AppState)

    # nodes are callables: (state: AppState) -> AppState
    workflow.add_node("profile", profile_agent.run)
    workflow.add_node("docs", doc_agent.run)
    workflow.add_node("reason", reason_agent.run)

    # wire edges
    workflow.add_edge(START, "profile")
    workflow.add_edge("profile", "docs")
    workflow.add_edge("docs", "reason")
    workflow.add_edge("reason", END)

    # compile to a runnable graph
    return workflow.compile()
