"""
blackbox/analysis/consensus.py
───────────────────────────────
Combines local and cloud results.
"""
from __future__ import annotations
from dataclasses import dataclass
from blackbox.analysis.local import LocalAnalysisResult
from blackbox.analysis.cloud import CloudAnalysisResult

@dataclass
class ConsensusResult:
    top_step: int
    scores: dict[int, float]
    agreement: bool
    status: str

def build_consensus(local: LocalAnalysisResult, cloud: CloudAnalysisResult | None) -> ConsensusResult:
    if not cloud or cloud.top_step == -1:
        return ConsensusResult(local.top_step, local.scores, True, "local_only")
        
    agreement = (local.top_step == cloud.top_step)
    
    # Simple strategy: if cloud disagrees, we average the scores
    merged_scores = {}
    all_keys = set(local.scores.keys()) | set(cloud.scores.keys())
    for k in all_keys:
        merged_scores[k] = (local.scores.get(k, 0.0) + cloud.scores.get(k, 0.0)) / 2.0
        
    top_step = max(merged_scores, key=merged_scores.get) if merged_scores else -1
    status = "agreed" if agreement else "disagreed_merged"
    
    return ConsensusResult(top_step, merged_scores, agreement, status)
