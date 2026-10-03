"""
blackbox/analysis/consensus.py
───────────────────────────────
Combines local and cloud diagnostic results into a unified consensus.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from blackbox.analysis.local import LocalAnalysisResult
from blackbox.analysis.cloud import CloudAnalysisResult


@dataclass
class ConsensusResult:
    top_step: int
    scores: dict[int, float]
    agreement: bool = True
    status: str = "local_only"
    final_confidence: str = "medium"


def build_consensus(local: LocalAnalysisResult, cloud: CloudAnalysisResult | None = None) -> ConsensusResult:
    if not cloud or cloud.top_step == -1:
        return ConsensusResult(
            top_step=local.top_step,
            scores=local.scores,
            agreement=True,
            status="local_only",
            final_confidence=local.confidence
        )

    agreement = (local.top_step == cloud.top_step)

    merged_scores = {}
    all_keys = set(local.scores.keys()) | set(cloud.scores.keys())
    for k in all_keys:
        merged_scores[k] = round((local.scores.get(k, 0.0) + cloud.scores.get(k, 0.0)) / 2.0, 4)

    top_step = max(merged_scores, key=merged_scores.get) if merged_scores else -1
    status = "agreed" if agreement else "disagreed_merged"
    conf = "high" if agreement and local.confidence in ("high", "medium") else "medium"

    return ConsensusResult(
        top_step=top_step,
        scores=merged_scores,
        agreement=agreement,
        status=status,
        final_confidence=conf
    )
