"""
blackbox/compare/align.py
─────────────────────────
Sequence alignment algorithm for comparing execution traces.
Maps steps between two traces based on step index, step type, and tool name.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from blackbox.capture.schema import AgentTrace, AgentStep


@dataclass
class AlignedStepPair:
    index: int
    left_step: AgentStep | None
    right_step: AgentStep | None
    status: str  # "match", "modified", "left_only", "right_only"
    divergence_reason: str | None = None


@dataclass
class TraceAlignment:
    left_run_id: str
    right_run_id: str
    pairs: list[AlignedStepPair]
    is_compatible: bool = True
    match_count: int = 0
    divergence_count: int = 0


def align_traces(t1: AgentTrace, t2: AgentTrace) -> TraceAlignment:
    """
    Aligns two agent traces step-by-step.
    Handles equal-length and differing-length trajectories.
    """
    pairs: list[AlignedStepPair] = []
    max_len = max(len(t1.steps), len(t2.steps))
    match_count = 0
    divergence_count = 0

    for i in range(max_len):
        s1 = t1.steps[i] if i < len(t1.steps) else None
        s2 = t2.steps[i] if i < len(t2.steps) else None

        if s1 is not None and s2 is not None:
            # Check for exact or semantic match
            same_type = s1.step_type == s2.step_type
            same_tool = s1.tool == s2.tool
            same_output = str(s1.output).strip() == str(s2.output).strip()
            same_error = s1.has_error == s2.has_error

            if same_type and same_tool and same_output and same_error:
                status = "match"
                match_count += 1
                reason = None
            else:
                status = "modified"
                divergence_count += 1
                reasons = []
                if not same_type:
                    reasons.append(f"Step type changed from {s1.step_type.value} to {s2.step_type.value}")
                if not same_tool:
                    reasons.append(f"Tool changed from {s1.tool} to {s2.tool}")
                if not same_output:
                    reasons.append(f"Output changed from {s1.output!r:.40} to {s2.output!r:.40}")
                if not same_error:
                    reasons.append(f"Error state changed (s1 error: {s1.has_error}, s2 error: {s2.has_error})")
                reason = "; ".join(reasons)

            pairs.append(AlignedStepPair(
                index=i,
                left_step=s1,
                right_step=s2,
                status=status,
                divergence_reason=reason
            ))
        elif s1 is not None:
            divergence_count += 1
            pairs.append(AlignedStepPair(
                index=i,
                left_step=s1,
                right_step=None,
                status="left_only",
                divergence_reason="Step only exists in left trace"
            ))
        else:
            divergence_count += 1
            pairs.append(AlignedStepPair(
                index=i,
                left_step=None,
                right_step=s2,
                status="right_only",
                divergence_reason="Step only exists in right trace"
            ))

    is_compatible = (t1.task_type == t2.task_type) or (t1.task_description == t2.task_description)
    return TraceAlignment(
        left_run_id=t1.run_id,
        right_run_id=t2.run_id,
        pairs=pairs,
        is_compatible=is_compatible,
        match_count=match_count,
        divergence_count=divergence_count
    )
