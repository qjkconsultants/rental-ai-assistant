from typing import List, Dict, Any

class VectorClient:
    """Milvus hook. For PoC tests we no-op but keep interface consistent."""
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self.mem: list[Dict[str, Any]] = []

    def upsert(self, vectors: List[list[float]], metas: List[dict]):
        if not self.enabled:
            # store in-memory for dev
            for v, m in zip(vectors, metas):
                self.mem.append({"vec": v, "meta": m})
            return len(vectors)
        # Wire to Milvus here later.
        return 0

    def query(self, vector: list[float], top_k: int = 5) -> List[dict]:
        # naive fake retrieval for PoC
        return self.mem[:top_k]
