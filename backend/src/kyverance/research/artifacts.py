"""Local artifact store port — no Azure in RSRCH-01."""

from __future__ import annotations

import hashlib
import json
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from kyverance.config import Settings, get_settings


class ArtifactStore(ABC):
    @abstractmethod
    def put_json(self, key: str, payload: dict[str, Any]) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_json(self, key: str) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def exists(self, key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def checksum(self, key: str) -> str | None:
        raise NotImplementedError


class LocalArtifactStore(ArtifactStore):
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe = key.replace("\\", "/").lstrip("/")
        path = self.root / safe
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def put_json(self, key: str, payload: dict[str, Any]) -> str:
        path = self._path(key)
        if path.exists():
            # Immutable: never overwrite prior validated objects.
            return key
        body = json.dumps(payload, default=str, indent=2, sort_keys=True)
        checksum = hashlib.sha256(body.encode("utf-8")).hexdigest()
        path.write_text(body, encoding="utf-8")
        self._path(key + ".sha256").write_text(checksum, encoding="utf-8")
        return key

    def get_json(self, key: str) -> dict[str, Any] | None:
        path = self._path(key)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def checksum(self, key: str) -> str | None:
        meta = self._path(key + ".sha256")
        if meta.exists():
            return meta.read_text(encoding="utf-8").strip()
        return None


class MemoryArtifactStore(ArtifactStore):
    """In-memory adapter for tests / CI."""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, Any]] = {}
        self._checksums: dict[str, str] = {}

    def put_json(self, key: str, payload: dict[str, Any]) -> str:
        if key in self._data:
            return key
        body = json.dumps(payload, default=str, sort_keys=True)
        self._data[key] = json.loads(body)
        self._checksums[key] = hashlib.sha256(body.encode("utf-8")).hexdigest()
        return key

    def get_json(self, key: str) -> dict[str, Any] | None:
        return self._data.get(key)

    def exists(self, key: str) -> bool:
        return key in self._data

    def checksum(self, key: str) -> str | None:
        return self._checksums.get(key)


_MEMORY_STORE: MemoryArtifactStore | None = None


def research_artifact_key(ticker: str, market_date: str, version_id: str, name: str = "report.json") -> str:
    return f"research/{ticker.upper()}/{market_date}/{version_id}/{name}"


def get_artifact_store(settings: Settings | None = None, *, force_memory: bool = False) -> ArtifactStore:
    global _MEMORY_STORE
    s = settings or get_settings()
    backend = (s.research_artifact_backend or "local").strip().lower()
    if force_memory or backend in {"memory", "mem"}:
        if _MEMORY_STORE is None:
            _MEMORY_STORE = MemoryArtifactStore()
        return _MEMORY_STORE
    root = s.research_artifact_root or str(Path(tempfile.gettempdir()) / "kyverance-research-artifacts")
    return LocalArtifactStore(root)


def reset_memory_artifact_store() -> None:
    global _MEMORY_STORE
    _MEMORY_STORE = None
