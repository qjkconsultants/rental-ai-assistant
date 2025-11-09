# src/snug/agents/memory_agent.py
from typing import Dict, Any, List
from datetime import datetime, UTC
from ..logging import log
import json
import os


class MemoryAgent:
    """
    Simple in-memory history manager for RAG interactions.
    Keeps the last N entries and can persist them to disk.
    """
    def __init__(
        self,
        max_history: int = 10,
        storage_path: str | None = None,
        persist_path: str | None = None,  # ← add this alias
    ):
        self.persist_path = persist_path  # ensure attribute always exists ✅
        # prefer persist_path if provided
        self.storage_path = persist_path or storage_path or "data/memory.json"
        self.max_history = max_history
        self._history: List[Dict[str, Any]] = []
        self._load_memory()

    # ----------------------------------------------------------------------
    # 💾 Internal helpers
    # ----------------------------------------------------------------------
    def _load_memory(self):
        """Load memory from disk if file exists."""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, "r") as f:
                    self._history = json.load(f)
            log.info("memory_loaded", entries=len(self._history))
        except Exception as e:
            log.error("memory_load_error", error=str(e))
            self._history = []

    def _save_memory(self):
        """Persist memory to disk safely."""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, "w") as f:
                json.dump(self._history[-self.max_history :], f, indent=2)
            log.info("memory_saved", entries=len(self._history))
        except Exception as e:
            log.error("memory_save_error", error=str(e))

    # ----------------------------------------------------------------------
    # 🧠 Core memory operations
    # ----------------------------------------------------------------------
    def _remember(self, entry: Dict[str, Any]):
        """Append a new memory entry with timestamp."""
        entry = dict(entry)
        entry["timestamp"] = datetime.now(UTC).isoformat()
        self._history.append(entry)
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history :]

    def recall(self, state: str) -> Dict[str, Any] | None:
        """Return the most recent entry for a given state."""
        for e in reversed(self._history):
            if e.get("state") == state:
                return e
        return None

    def snapshot(self, k: int = 3) -> List[Dict[str, Any]]:
        """Return the last k memory entries."""
        return self._history[-k:]

    # ----------------------------------------------------------------------
    # ✅ Compatibility shim (prevents AttributeError)
    # ----------------------------------------------------------------------
    @property
    def memory(self):
        """Alias for _history to satisfy legacy or test references."""
        return self._history
