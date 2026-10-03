"""
blackbox/attribution/baselines/first_error.py
─────────────────────────────────────────────
Naive baseline: flags the first step that explicitly raised an error.
"""
from __future__ import annotations
from blackbox.capture.schema import AgentTrace

def predict(trace: AgentTrace) -> dict[int, float]:
    """Returns {step_index: score}. Score is 1.0 for first error, 0 for rest."""
    scores = {s.step_index: 0.0 for s in trace.steps}
    for s in trace.steps:
        if s.has_error:
            scores[s.step_index] = 1.0
            break
    return scores
