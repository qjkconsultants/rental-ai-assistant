# src/snug/core/vector_db.py
import re
import os
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
from ..logging import log


class VectorDB:
    """
    Lightweight local ChromaDB wrapper for semantic retrieval.
    Stores vector embeddings for rental compliance and guidance text.
    Includes PII redaction, deduplication, and inspection helpers.
    """

    def __init__(
        self,
        collection_name: str = "rental_kb",
        persist_dir: str = "data/chroma_store",
        anonymized_telemetry: bool = True,
    ):
        os.makedirs(persist_dir, exist_ok=True)
        log.info("chroma_connect", path=persist_dir, collection=collection_name)

        self.client = chromadb.Client(
            Settings(anonymized_telemetry=anonymized_telemetry, persist_directory=persist_dir)
        )
        self.collection = self.client.get_or_create_collection(collection_name)
        self._model = None  # Lazy load to reduce startup time

    # ─────────────────────────────────────────────
    # 🧠 MODEL HANDLING
    # ─────────────────────────────────────────────
    @property
    def model(self):
        """Lazy-load the sentence transformer model."""
        if self._model is None:
            log.info("model_load", name="all-MiniLM-L6-v2")
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._model

    # ─────────────────────────────────────────────
    # 🛡️ SANITIZATION HELPERS
    # ─────────────────────────────────────────────
    @staticmethod
    def sanitize_text(text: str) -> str:
        """Remove or redact sensitive data before embedding."""
        redactions = {
            r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b": "[REDACTED_EMAIL]",
            r"\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b": "[REDACTED_CARD]",
            r"\b\d{10}\b": "[REDACTED_PHONE]",
            r"\b\d{2}/\d{2}/\d{4}\b": "[REDACTED_DOB]",
            r"\b[A-Z]{2}\d{6,}\b": "[REDACTED_ID]",
        }
        for pattern, replacement in redactions.items():
            text = re.sub(pattern, replacement, text, flags=re.I)
        return text.strip()

    # ─────────────────────────────────────────────
    # ➕ INSERT DOCUMENTS
    # ─────────────────────────────────────────────
    def add_documents(
        self,
        texts: List[str],
        metas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ):
        """Insert or upsert sanitized text documents into ChromaDB."""
        if not texts:
            log.warn("chroma_insert_skipped", reason="no_texts")
            return

        # Deduplicate to avoid embedding same text twice
        unique_texts = list(dict.fromkeys([t.strip() for t in texts if t.strip()]))
        clean_texts = [self.sanitize_text(t) for t in unique_texts]

        embeddings = self.model.encode(clean_texts, show_progress_bar=False).tolist()
        ids = ids or [f"id_{i}" for i in range(len(clean_texts))]
        metas = metas or [{}] * len(clean_texts)

        try:
            self.collection.add(
                documents=clean_texts,
                metadatas=metas,
                ids=ids,
                embeddings=embeddings,
            )
            log.info("chroma_insert", count=len(clean_texts))
        except Exception as e:
            log.error("chroma_insert_failed", error=str(e))
            raise

    # ─────────────────────────────────────────────
    # 🔍 SEMANTIC SEARCH
    # ─────────────────────────────────────────────
    def search(self, query_text: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Perform semantic search using cosine similarity."""
        if not query_text:
            return []
        query_emb = self.model.encode([query_text], show_progress_bar=False).tolist()
        results = self.collection.query(query_embeddings=query_emb, n_results=limit)

        docs = results.get("documents", [[]])[0]
        scores = results.get("distances", [[]])[0]
        return [{"text": t, "score": float(s)} for t, s in zip(docs, scores)]

    # ─────────────────────────────────────────────
    # 🧩 UTILITY FUNCTIONS
    # ─────────────────────────────────────────────
    def count(self) -> int:
        """Return number of stored documents."""
        try:
            return self.collection.count()
        except Exception:
            return 0

    def list_collections(self) -> List[str]:
        """List all collections in the local Chroma store."""
        try:
            return [c.name for c in self.client.list_collections()]
        except Exception as e:
            log.error("chroma_list_failed", error=str(e))
            return []

    def clear(self):
        """Delete all data in the current collection."""
        self.collection.delete(where={})
        log.info("chroma_cleared", collection=self.collection.name)
