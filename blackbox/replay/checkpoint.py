"""
blackbox/replay/checkpoint.py
─────────────────────────────
Captures and restores intermediate agent state snapshots.
Allows time-travel debugging and resumption from arbitrary checkpoints.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from blackbox.capture.schema import Checkpoint, AgentTrace, AgentStep


@dataclass
class StateSnapshot:
    step_index: int
    state_dict: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    checkpoint_id: str = ""

    def __post_init__(self):
        if not self.checkpoint_id:
            self.checkpoint_id = f"ckpt-step-{self.step_index}"


class CheckpointManager:
    """Manages creation and retrieval of step-level execution checkpoints."""

    @staticmethod
    def extract_state_at_step(trace: AgentTrace, step_index: int) -> dict[str, Any]:
        """
        Extracts reconstructed environment and memory state from trace history up to step_index.
        """
        state: dict[str, Any] = {
            "task_id": trace.task_id,
            "task_type": trace.task_type.value,
            "intermediate_results": {},
            "last_output": None,
            "doc": None,
            "docs": [],
            "sql": None,
            "history": []
        }

        limit = min(step_index + 1, len(trace.steps))
        for i in range(limit):
            step = trace.steps[i]
            state["history"].append({
                "step_index": step.step_index,
                "name": step.name,
                "output": step.output
            })
            state["last_output"] = step.output
            state["intermediate_results"][f"step_{i}"] = step.output

            if step.tool == "search":
                state["docs"] = step.output
            elif step.tool == "retrieve":
                state["doc"] = step.output
            elif step.step_type.value == "llm_call" and "SELECT" in str(step.output).upper():
                state["sql"] = step.output

        return state

    @staticmethod
    def create_checkpoint(trace: AgentTrace, step_index: int) -> Checkpoint:
        state = CheckpointManager.extract_state_at_step(trace, step_index)
        return Checkpoint(
            checkpoint_id=f"ckpt-{trace.run_id}-step-{step_index}",
            step_index=step_index,
            state=state,
            timestamp=datetime.now(timezone.utc)
        )
