"""
blackbox/analysis/router.py
────────────────────────────
Decides if we need cloud verification.
"""
from __future__ import annotations
from blackbox.analysis.local import LocalAnalysisResult

def should_route_to_cloud(local_result: LocalAnalysisResult, always_cloud: bool = False) -> bool:
    """Returns True if the local model is uncertain, or if overridden."""
    if always_cloud: return True
    return local_result.confidence in ("low", "medium")
