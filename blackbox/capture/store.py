"""
blackbox/capture/store.py
──────────────────────────
Persists and retrieves AgentTrace objects.

Storage layout
──────────────
  data/traces/          ← one JSON file per trace (human-readable)
  data/artifacts/       ← Parquet datasets for ML training

Design
──────
Traces are stored as JSON (human-readable, easy to inspect).
For ML training, TraceStore.export_dataset() converts them to Parquet.
"""
from __future__ import annotations

import json
import pickle
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from blackbox.capture.schema import (
    AgentError, AgentStep, AgentTrace, ModelCall,
    StepType, TaskType, ToolCall, TokenUsage, Checkpoint,
)
from blackbox.paths import ARTIFACTS_DIR, TRACES_DIR

# ── Serialisation helpers ──────────────────────────────────────────────────────

def _default(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, (StepType, TaskType)):
        return obj.value
    raise TypeError(f"Not serialisable: {type(obj)}")


def trace_to_dict(trace: AgentTrace) -> dict:
    return json.loads(json.dumps(asdict(trace), default=_default))


def _parse_step(d: dict) -> AgentStep:
    d = dict(d)
    d["step_type"] = StepType(d["step_type"])
    d["timestamp"] = datetime.fromisoformat(d["timestamp"])
    if d.get("error"):
        d["error"] = AgentError(**d["error"])
    if d.get("tokens"):
        d["tokens"] = TokenUsage(**d["tokens"])
    if d.get("tool_call"):
        tc = d["tool_call"]
        if tc.get("error"):
            tc["error"] = AgentError(**tc["error"])
        d["tool_call"] = ToolCall(**tc)
    if d.get("model_call"):
        mc = d["model_call"]
        mc["tokens"] = TokenUsage(**mc["tokens"])
        d["model_call"] = ModelCall(**mc)
    d.pop("model_call", None)   # skip for now; not needed for analysis
    return AgentStep(**{k: v for k, v in d.items() if k != "model_call"})


def dict_to_trace(d: dict) -> AgentTrace:
    d = dict(d)
    d["task_type"]   = TaskType(d["task_type"])
    d["started_at"]  = datetime.fromisoformat(d["started_at"])
    d["ended_at"]    = datetime.fromisoformat(d["ended_at"])
    d["steps"]       = [_parse_step(s) for s in d["steps"]]
    if d.get("error"):
        d["error"]   = AgentError(**d["error"])
    return AgentTrace(**d)


# ── Store ──────────────────────────────────────────────────────────────────────

class TraceStore:
    def __init__(self, traces_dir: Path = TRACES_DIR):
        self.traces_dir = Path(traces_dir)
        self.traces_dir.mkdir(parents=True, exist_ok=True)

    def save(self, trace: AgentTrace) -> Path:
        path = self.traces_dir / f"{trace.run_id}.json"
        with open(path, "w") as f:
            json.dump(trace_to_dict(trace), f, indent=2)
        return path

    def load(self, run_id: str) -> AgentTrace:
        path = self.traces_dir / f"{run_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Trace not found: {run_id}")
        with open(path) as f:
            return dict_to_trace(json.load(f))

    def load_all(self) -> list[AgentTrace]:
        traces = []
        for p in sorted(self.traces_dir.glob("*.json")):
            try:
                traces.append(self.load(p.stem))
            except Exception:
                pass
        return traces

    def list_runs(self) -> list[str]:
        return sorted(p.stem for p in self.traces_dir.glob("*.json"))

    def save_batch(self, traces: list[AgentTrace]) -> None:
        for t in traces:
            self.save(t)

    def export_pkl(self, path: Path) -> None:
        """Export all traces as a pickle for fast ML loading."""
        traces = self.load_all()
        with open(path, "wb") as f:
            pickle.dump(traces, f)

    @staticmethod
    def load_pkl(path: Path) -> list[AgentTrace]:
        with open(path, "rb") as f:
            return pickle.load(f)


# ── Convenience functions ──────────────────────────────────────────────────────

_default_store = TraceStore()


def save_trace(trace: AgentTrace, store: TraceStore | None = None) -> Path:
    return (store or _default_store).save(trace)


def load_trace(run_id: str, store: TraceStore | None = None) -> AgentTrace:
    return (store or _default_store).load(run_id)
