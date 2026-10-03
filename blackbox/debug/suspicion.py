"""
blackbox/debug/suspicion.py
────────────────────────────
Handles suspicion distribution.
"""
from __future__ import annotations

def rank_suspicion(scores: dict[int, float]) -> list[tuple[int, float]]:
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
