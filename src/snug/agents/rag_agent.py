# src/snug/agents/rag_agent.py
from typing import Dict, Any, List
from ..mcp.schema import MCPMessage
from ..logging import log
from ..core.vector_db import VectorDB
from ..agents.memory_agent import MemoryAgent


class RAGAgent:
    """
    Retrieval-Augmented Generation (RAG) Agent using ChromaDB.
    - Checks MemoryAgent first for recent context
    - Falls back to VectorDB (Chroma) for new retrievals
    - Always persists the query + results to memory
    """

    def __init__(
        self,
        vector_client: VectorDB | None = None,
        memory_agent: MemoryAgent | None = None,
    ):
        self.vdb = vector_client or VectorDB(collection_name="rental_kb")
        self.memory = memory_agent or MemoryAgent()

    def handle(self, msg: MCPMessage) -> MCPMessage:
        payload = msg.payload
        state = payload.get("state", "GENERAL").upper()
        query_text = payload.get("query", f"rental application requirements {state}")

        # ─── Try Memory First ────────────────────────────────
        memory_hit = self.memory.recall(state)
        if memory_hit:
            log.info("rag_agent_memory_hit", state=state)
            kb_texts = memory_hit.get("retrieved_docs", [])
            results = [{"text": t, "score": 1.0} for t in kb_texts]
        else:
            # ─── Fall Back to VectorDB Search ────────────────
            try:
                results = self.vdb.search(query_text, limit=3)
                kb_texts = [r["text"] for r in results]
            except Exception as e:
                log.error("rag_agent_error", error=str(e))
                results = []
                kb_texts = ["General rental application guidance not available."]

        # ─── Always Persist New or Reused Knowledge ──────────
        self.memory._remember(
            {
                "state": state,
                "query": query_text,
                "retrieved_docs": kb_texts,
            }
        )
        self.memory._save_memory()

        # attach KB + recent memory snippet
        payload["kb"] = {
            "state": state,
            "retrieved_docs": kb_texts,
            "top_chunks": results,
        }
        payload["memory_snippet"] = self.memory.snapshot(k=3)

        # ✅ Add the "context_used" field expected by the test
        payload["context_used"] = {
            "retrieved_docs": kb_texts,
            "memory_hit": memory_hit,
        }

        log.info("rag_agent", state=state, results=len(results))
        return MCPMessage(
            sender="rag_agent",
            receiver="response_agent",
            type="response",
            payload=payload,
            context=msg.context,
        )

