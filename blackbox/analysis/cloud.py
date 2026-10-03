"""
blackbox/analysis/cloud.py
───────────────────────────
Coordinates cloud analysis (optional deeper inspection).
"""
from __future__ import annotations
import time
from dataclasses import dataclass
from blackbox.capture.schema import AgentTrace
from blackbox.attribution.baselines.cloud_judge import CloudJudge

@dataclass
class CloudAnalysisResult:
    scores: dict[int, float]
    top_step: int
    latency_ms: float

async def analyze_cloud(trace: AgentTrace, judge: CloudJudge) -> CloudAnalysisResult:
    t0 = time.perf_counter()
    try:
        scores = await judge.predict(trace)
        top_step = max(scores, key=scores.get) if scores else -1
    except Exception:
        scores = {}
        top_step = -1
    lat = (time.perf_counter() - t0) * 1000
    return CloudAnalysisResult(scores, top_step, lat)
