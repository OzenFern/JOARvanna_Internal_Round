"""
blackbox/agents/llm.py
───────────────────────
Common LLM interface so the rest of the project stays provider-agnostic.

For training/demo, MockLLM provides deterministic, scripted responses
keyed on the task + step so fault injection works reproducibly.
"""
from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from typing import Any


class BaseLLM(ABC):
    @abstractmethod
    def call(self, prompt: str, *, system: str = "", **kwargs) -> tuple[str, int, int]:
        """Returns (response_text, input_tokens, output_tokens)."""

    def estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)


class MockLLM(BaseLLM):
    """
    Deterministic mock LLM for training data generation.
    Responses are driven by a response_map keyed on (task_type, step_index).
    """

    def __init__(self, response_map: dict[tuple, str]):
        self._map    = response_map
        self._cursor = 0     # auto-advances through map entries if no key match

    def call(self, prompt: str, *, system: str = "", **kwargs) -> tuple[str, int, int]:
        key    = kwargs.get("_key")
        resp   = self._map.get(key, self._map.get(self._cursor, "OK"))
        self._cursor += 1
        inp    = self.estimate_tokens(prompt + system)
        out    = self.estimate_tokens(str(resp))
        return str(resp), inp, out


class OpenAILLM(BaseLLM):
    """Thin wrapper around the OpenAI Chat Completions API."""

    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None):
        self.model   = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")

    def call(self, prompt: str, *, system: str = "", **kwargs) -> tuple[str, int, int]:
        import httpx, json
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "messages": messages, "temperature": 0},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return text, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
