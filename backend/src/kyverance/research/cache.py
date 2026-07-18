"""Derived research cache port — in-memory default; never source of truth."""

from __future__ import annotations

import json
import threading
import time
from typing import Any, Protocol

from kyverance.config import Settings, get_settings


class ResearchCache(Protocol):
    def available(self) -> bool: ...
    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str, *, ttl_seconds: int | None = None) -> None: ...
    def delete(self, key: str) -> None: ...
    def set_nx(self, key: str, value: str, *, ttl_seconds: int) -> bool: ...


class MemoryResearchCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[str, float | None]] = {}
        self._lock = threading.Lock()

    def available(self) -> bool:
        return True

    def _purge_expired(self, key: str) -> None:
        item = self._store.get(key)
        if not item:
            return
        _, expires = item
        if expires is not None and time.time() > expires:
            del self._store[key]

    def get(self, key: str) -> str | None:
        with self._lock:
            self._purge_expired(key)
            item = self._store.get(key)
            return item[0] if item else None

    def set(self, key: str, value: str, *, ttl_seconds: int | None = None) -> None:
        expires = time.time() + ttl_seconds if ttl_seconds else None
        with self._lock:
            self._store[key] = (value, expires)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def set_nx(self, key: str, value: str, *, ttl_seconds: int) -> bool:
        with self._lock:
            self._purge_expired(key)
            if key in self._store:
                return False
            self._store[key] = (value, time.time() + ttl_seconds)
            return True


_MEMORY_CACHE = MemoryResearchCache()


def get_research_cache(settings: Settings | None = None, *, force_memory: bool = True) -> MemoryResearchCache:
    """RSRCH-01 uses in-memory derived cache; Redis may be added later without domain changes."""
    _ = settings or get_settings()
    _ = force_memory
    return _MEMORY_CACHE


def reset_research_cache() -> None:
    global _MEMORY_CACHE
    _MEMORY_CACHE = MemoryResearchCache()


def redis_keys(security_id: str) -> dict[str, str]:
    return {
        "latest": f"research:latest:{security_id}",
        "freshness": f"research:freshness:{security_id}",
        "lock": f"research:lock:{security_id}",
    }


def version_key(security_id: str, version_id: str) -> str:
    return f"research:version:{security_id}:{version_id}"


def acquire_generation_lock(cache: MemoryResearchCache, security_id: str, *, ttl_seconds: int = 300) -> str | None:
    import uuid

    token = str(uuid.uuid4())
    keys = redis_keys(security_id)
    if cache.set_nx(keys["lock"], token, ttl_seconds=ttl_seconds):
        return token
    return None


def release_generation_lock(cache: MemoryResearchCache, security_id: str, token: str) -> None:
    keys = redis_keys(security_id)
    current = cache.get(keys["lock"])
    if current == token:
        cache.delete(keys["lock"])


def publish_research_atomic(
    cache: MemoryResearchCache,
    *,
    security_id: str,
    version_id: str,
    report: dict[str, Any],
    freshness: dict[str, Any],
    ttl_seconds: int = 86_400,
) -> None:
    keys = redis_keys(security_id)
    cache.set(version_key(security_id, version_id), json.dumps(report, default=str), ttl_seconds=ttl_seconds)
    cache.set(keys["freshness"], json.dumps(freshness, default=str), ttl_seconds=ttl_seconds)
    cache.set(keys["latest"], version_id, ttl_seconds=ttl_seconds)
