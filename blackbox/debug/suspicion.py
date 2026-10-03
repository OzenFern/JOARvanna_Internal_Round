"""
blackbox/debug/suspicion.py
───────────────────────────
Data structures and utilities for step suspicion scoring and ranking.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from blackbox.capture.schema import AgentTrace, AgentStep


@dataclass
class SuspiciousStep:
    index: int
    name: str
    tool: str | None
    suspicion_score: float  # 0.0 to 1.0
    confidence: str         # "high" | "medium" | "low"
    evidence: str
    is_top_suspect: bool = False
    suggested_patch: dict[str, Any] = field(default_factory=dict)


def rank_step_suspicions(trace: AgentTrace, scores: dict[int, float]) -> list[SuspiciousStep]:
    """
    Ranks all steps in a trace by suspicion score descending.
    """
    if not trace.steps:
        return []

    ranked_indices = sorted(scores.keys(), key=lambda idx: scores[idx], reverse=True)
    top_idx = ranked_indices[0] if ranked_indices else -1
    top_score = scores.get(top_idx, 0.0)
    second_score = scores.get(ranked_indices[1], 0.0) if len(ranked_indices) > 1 else 0.0

    result: list[SuspiciousStep] = []
    for idx in ranked_indices:
        if idx >= len(trace.steps):
            continue
        step = trace.steps[idx]
        score = scores[idx]

        # Determine confidence for this step
        if idx == top_idx:
            if top_score > 0.8 or (top_score - second_score) > 0.3:
                conf = "high"
            elif top_score > 0.4:
                conf = "medium"
            else:
                conf = "low"
        else:
            conf = "medium" if score > 0.5 else "low"

        # Construct evidence description
        evidence_items = []
        if step.has_error:
            evidence_items.append(f"Explicit {step.error.error_type}: {step.error.message}")
        if step.latency_ms > 500:
            evidence_items.append(f"High latency spike: {step.latency_ms:.1f}ms")
        if step.tool:
            evidence_items.append(f"Tool `{step.tool}` execution output anomaly")
        else:
            evidence_items.append("LLM reasoning / decision divergence")

        ev_str = "; ".join(evidence_items)

        result.append(SuspiciousStep(
            index=idx,
            name=step.name,
            tool=step.tool,
            suspicion_score=round(score, 4),
            confidence=conf,
            evidence=ev_str,
            is_top_suspect=(idx == top_idx)
        ))

    return result
