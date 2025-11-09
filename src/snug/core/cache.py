# src/snug/core/cache.py
import time
from threading import Lock


class InMemoryCache:
    """
    Simple thread-safe cache with optional TTL (time-to-live).
    Used by RAGAgent to avoid repeated VectorDB queries.
    """

    def __init__(self, ttl_seconds: int = 900):
        self._cache = {}
        self.ttl = ttl_seconds
        self._lock = Lock()

    def get(self, key: str):
        with self._lock:
            entry = self._cache.get(key)
            if not entry:
                return None
            value, expires = entry
            if expires < time.time():
                del self._cache[key]
                return None
            return value

    def set(self, key: str, value):
        with self._lock:
            self._cache[key] = (value, time.time() + self.ttl)

    def clear(self):
        with self._lock:
            self._cache.clear()

    def keys(self):
        with self._lock:
            return list(self._cache.keys())

    def size(self):
        with self._lock:
            return len(self._cache)
