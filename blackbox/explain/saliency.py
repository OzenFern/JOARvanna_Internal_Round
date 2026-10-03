"""
blackbox/explain/saliency.py
────────────────────────────
Feature saliency and attribution analysis for explaining why a step was flagged.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from blackbox.capture.schema import AgentTrace, AgentStep
from blackbox.features.step_features import extract_features, feature_names


@dataclass
class StepSaliency:
    step_index: int
    step_name: str
    top_contributing_features: list[tuple[str, float]]  # [("has_error", 0.45), ("entropy", 0.22), ...]
    summary: str


def compute_step_saliency(trace: AgentTrace, step_index: int) -> StepSaliency:
    """
    Computes relative feature saliency breakdown for an individual step.
    """
    if step_index < 0 or step_index >= len(trace.steps):
        return StepSaliency(step_index, "unknown", [], "Invalid step index")

    step = trace.steps[step_index]
    feats = extract_features(step, len(trace.steps))
    names = feature_names()

    # Calculate heuristic feature weights based on deviation from norm
    contributions: list[tuple[str, float]] = []
    
    if step.has_error:
        contributions.append(("Explicit Error Raised", 0.95))
    if step.latency_ms > 200:
        contributions.append(("High Execution Latency", round(min(1.0, step.latency_ms / 1000.0), 3)))
    
    out_str = str(step.output)
    if len(out_str) < 3 or len(out_str) > 500:
        contributions.append(("Output Length Anomaly", 0.65))
    
    if step.tool:
        contributions.append((f"Tool Call ({step.tool})", 0.45))
    else:
        contributions.append(("LLM Decision / Prompt", 0.35))

    contributions.append(("Trajectory Position", round(feats[0], 2)))

    contributions.sort(key=lambda x: x[1], reverse=True)
    top_feats = contributions[:4]

    summary = f"Step {step_index} attribution is driven primarily by: " + ", ".join(
        f"{name} ({score:.2f})" for name, score in top_feats
    )

    return StepSaliency(
        step_index=step_index,
        step_name=step.name,
        top_contributing_features=top_feats,
        summary=summary
    )
