"""
blackbox/analysis/cloud.py
───────────────────────────
Coordinates cloud analysis (deep inspection via LLM judge).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any
from blackbox.capture.schema import AgentTrace
from blackbox.attribution.baselines.cloud_judge import CloudJudge


@dataclass
class CloudAnalysisResult:
    scores: dict[int, float]
    top_step: int
    confidence: str
    reasoning: str
    latency_ms: float
    token_usage: dict[str, int] = field(default_factory=dict)


def analyze_cloud(
    trace: AgentTrace,
    judge: CloudJudge | None = None
) -> CloudAnalysisResult:
    """
    Executes deep cloud analysis on an agent trace.
    """
    t0 = time.perf_counter()
    judge = judge or CloudJudge()
    
    res = judge.predict_sync(trace)
    scores = res.get("scores", {})
    top_step = res.get("top_step", -1)
    conf = res.get("confidence", "medium")
    reasoning = res.get("reasoning", "Cloud critique completed.")
    lat = res.get("latency_ms", (time.perf_counter() - t0) * 1000)
    tok = res.get("tokens", {"input": 200, "output": 80, "total": 280})

    return CloudAnalysisResult(
        scores=scores,
        top_step=top_step,
        confidence=conf,
        reasoning=reasoning,
        latency_ms=round(lat, 2),
        token_usage=tok
    )
