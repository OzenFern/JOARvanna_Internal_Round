"""
blackbox/capture/schema.py
───────────────────────────
Domain-agnostic data structures for agent execution traces.
Everything the system observes flows through these types.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


# ── Primitives ─────────────────────────────────────────────────────────────────

class StepType(str, Enum):
    LLM_CALL    = "llm_call"
    TOOL_CALL   = "tool_call"
    OBSERVATION = "observation"
    DECISION    = "decision"
    RETRIEVAL   = "retrieval"


class TaskType(str, Enum):
    QA       = "qa"
    TEXT2SQL = "text2sql"
    MATH     = "math"
    CUSTOM   = "custom"


@dataclass
class TokenUsage:
    input_tokens:  int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class AgentError:
    error_type: str                 # e.g. "ToolError", "ValidationError"
    message:    str
    traceback:  str | None = None


@dataclass
class ToolCall:
    tool_name:  str
    arguments:  dict[str, Any]
    result:     Any
    latency_ms: float
    error:      AgentError | None = None


@dataclass
class ModelCall:
    model:      str
    prompt:     str | list[dict]    # str or chat messages
    response:   str
    tokens:     TokenUsage
    latency_ms: float


# ── Step ───────────────────────────────────────────────────────────────────────

@dataclass
class AgentStep:
    step_index:    int
    step_type:     StepType
    timestamp:     datetime
    latency_ms:    float
    inputs:        dict[str, Any]
    output:        Any
    tool:          str | None           = None
    tool_call:     ToolCall | None      = None
    model_call:    ModelCall | None     = None
    error:         AgentError | None    = None
    tokens:        TokenUsage | None    = None
    checkpoint_id: str | None          = None
    metadata:      dict[str, Any]      = field(default_factory=dict)
    step_id:       str                 = field(default_factory=lambda: str(uuid.uuid4())[:8])

    @property
    def has_error(self) -> bool:
        return self.error is not None

    @property
    def name(self) -> str:
        """Short display name for this step."""
        if self.tool:
            return f"{self.tool}()"
        return self.step_type.value


# ── Checkpoint ─────────────────────────────────────────────────────────────────

@dataclass
class Checkpoint:
    checkpoint_id: str
    step_index:    int
    state:         dict[str, Any]       # serialisable agent state
    timestamp:     datetime


# ── Trace ──────────────────────────────────────────────────────────────────────

@dataclass
class AgentTrace:
    run_id:          str
    task_id:         str
    task_type:       TaskType
    task_description: str
    steps:           list[AgentStep]
    final_output:    Any
    expected_output: Any
    success:         bool
    started_at:      datetime
    ended_at:        datetime
    error:           AgentError | None  = None
    fault_type:      str | None        = None   # set for training runs
    fault_step:      int | None        = None   # set for training runs
    meta:            dict[str, Any]    = field(default_factory=dict)

    @property
    def n_steps(self) -> int:
        return len(self.steps)

    @property
    def total_latency_ms(self) -> float:
        return sum(s.latency_ms for s in self.steps)

    @property
    def total_tokens(self) -> int:
        return sum(s.tokens.total_tokens for s in self.steps if s.tokens)

    @property
    def error_steps(self) -> list[AgentStep]:
        return [s for s in self.steps if s.has_error]

    def step(self, index: int) -> AgentStep:
        return self.steps[index]
