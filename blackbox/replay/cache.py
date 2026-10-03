"""
blackbox/replay/cache.py
────────────────────────
Cache manager for deterministic tool and LLM replay.
Avoids redundant external computation during time-travel debugging.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Callable


class ExecutionCache:
    """In-memory and persistent cache for replay execution."""

    def __init__(self):
        self._cache: dict[str, Any] = {}

    @staticmethod
    def make_key(namespace: str, inputs: dict[str, Any]) -> str:
        serialized = json.dumps(inputs, sort_keys=True, default=str)
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
        return f"{namespace}:{digest}"

    def get(self, namespace: str, inputs: dict[str, Any]) -> Any | None:
        key = self.make_key(namespace, inputs)
        return self._cache.get(key)

    def set(self, namespace: str, inputs: dict[str, Any], result: Any) -> None:
        key = self.make_key(namespace, inputs)
        self._cache[key] = result

    def get_or_call(self, namespace: str, inputs: dict[str, Any], fn: Callable[[], Any]) -> Any:
        cached = self.get(namespace, inputs)
        if cached is not None:
            return cached
        result = fn()
        self.set(namespace, inputs, result)
        return result

    def clear(self) -> None:
        self._cache.clear()
