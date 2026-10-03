"""
blackbox/analysis/local.py
───────────────────────────
Coordinates local analysis: features -> model -> confidence.
"""
from __future__ import annotations
import time
from dataclasses import dataclass
from blackbox.capture.schema import AgentTrace
from blackbox.attribution.model import LocalAttributionModel
from blackbox.attribution.confidence import compute_confidence

@dataclass
class LocalAnalysisResult:
    scores: dict[int, float]
    top_step: int
    confidence: str
    latency_ms: float

def analyze_local(trace: AgentTrace, model: LocalAttributionModel) -> LocalAnalysisResult:
    t0 = time.perf_counter()
    scores = model.predict_trace(trace)
    top_step = max(scores, key=scores.get) if scores else -1
    conf = compute_confidence(scores)
    lat = (time.perf_counter() - t0) * 1000
    return LocalAnalysisResult(scores, top_step, conf, lat)
