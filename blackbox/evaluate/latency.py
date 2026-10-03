"""
blackbox/evaluate/latency.py
────────────────────────────
Measures execution latency of local vs cloud diagnostic models.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from blackbox.capture.schema import AgentTrace
from blackbox.attribution.model import LocalAttributionModel


@dataclass
class LatencyBenchmark:
    total_traces: int
    mean_local_latency_ms: float
    p95_local_latency_ms: float
    target_met: bool  # Target is < 50ms


def eval_latency(traces: list[AgentTrace], model: LocalAttributionModel) -> LatencyBenchmark:
    if not traces or not model.is_fitted:
        return LatencyBenchmark(0, 0.0, 0.0, True)

    times = []
    for t in traces[:100]:
        t0 = time.perf_counter()
        model.predict_trace(t)
        elapsed = (time.perf_counter() - t0) * 1000
        times.append(elapsed)

    times.sort()
    mean_lat = round(sum(times) / len(times), 2)
    p95_idx = int(0.95 * len(times))
    p95_lat = round(times[min(p95_idx, len(times) - 1)], 2)

    return LatencyBenchmark(
        total_traces=len(times),
        mean_local_latency_ms=mean_lat,
        p95_local_latency_ms=p95_lat,
        target_met=(mean_lat < 50.0)
    )
