# src/snug/agents/memory_agent.py
import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from ..logging import log


class MemoryAgent:
    """
    Lightweight, file-backed memory for recent RAG interactions.

    - Stores a small rolling window of recent queries + retrieved docs
    - Persists to JSON so it survives restarts
    - Simple recall by state
    """

    def __init__(
        self,
        persist_path: str = "data/memory_store.json",
        max_history: int = 50,
    ):
        self.persist_path = persist_path
        self.max_history = max_history
        os.makedirs(os.path.dirname(persist_path), exist_ok=True)
        self._history: List[Dict[str, Any]] = []
        self._load_memory()

    # ─────────────────────────────────────────────
    # Internal persistence
    # ─────────────────────────────────────────────
    def _load_memory(self):
        try:
            if os.path.exists(self.persist_path):
                with open(self.persist_path, "r") as f:
                    self._history = json.load(f)
            else:
                self._history = []
            log.info("memory_loaded", entries=len(self._history))
        except Exception as e:
            log.error("memory_load_failed", error=str(e))
            self._history = []

    def _save_memory(self):
        try:
            with open(self.persist_path, "w") as f:
                json.dump(self._history, f)
            log.info("memory_saved", entries=len(self._history))
        except Exception as e:
            log.error("memory_save_failed", error=str(e))

    def _remember(self, entry: Dict[str, Any]):
        """Store a memory entry with a UTC-aware timestamp, trimming history size."""
        entry = dict(entry)
        entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        self._history.append(entry)

        # Keep only the most recent N entries
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history:]

    # ─────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────
    def recall(self, state: str) -> Optional[Dict[str, Any]]:
        """
        Return the most recent memory entry for a given state, if any.
        (Simple heuristic – can be later upgraded to semantic recall.)
        """
        state = (state or "").upper()
        for entry in reversed(self._history):
            if (entry.get("state") or "").upper() == state:
                return entry
        return None

    def snapshot(self, k: int = 3) -> List[Dict[str, Any]]:
        """Return last k memory entries (for LLM context)."""
        return self._history[-k:]

    def status(self) -> Dict[str, Any]:
        states = list(
            { (e.get("state") or "UNKNOWN") for e in self._history }
        )
        return {
            "entries": len(self._history),
            "states_tracked": states,
            "recent": self.snapshot(5),
            "persist_path": self.persist_path,
            "max_history": self.max_history,
        }
