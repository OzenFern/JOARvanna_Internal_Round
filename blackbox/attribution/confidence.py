"""
blackbox/attribution/confidence.py
──────────────────────────────────
Computes a confidence score for the model's prediction.
"""
from __future__ import annotations

def compute_confidence(scores: dict[int, float]) -> str:
    """Returns 'high', 'medium', or 'low' based on the score margin."""
    if len(scores) < 2:
        return "high"
    sorted_scores = sorted(scores.values(), reverse=True)
    top, second = sorted_scores[0], sorted_scores[1]
    
    if top > 2.0 * second + 1e-9:
        return "high"
    if top > 1.3 * second + 1e-9:
        return "medium"
    return "low"
