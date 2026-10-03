"""
blackbox/evaluate/localization.py
─────────────────────────────────
Measures fault localization accuracy (Top-1, Top-3, Top-5, and MRR).
Evaluates models against ground truth faulty runs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from blackbox.capture.schema import AgentTrace
from blackbox.attribution.model import LocalAttributionModel


@dataclass
class LocalizationMetrics:
    total_samples: int
    faulty_samples: int
    top1_accuracy: float
    top3_accuracy: float
    top5_accuracy: float
    mrr: float  # Mean Reciprocal Rank
    exact_matches: int
    top3_matches: int
    per_fault_accuracy: dict[str, float]


def eval_localization(
    traces: list[AgentTrace],
    model: LocalAttributionModel | None = None
) -> LocalizationMetrics:
    """
    Evaluates localization performance against ground-truth fault_step labels.
    """
    faulty_traces = [t for t in traces if t.fault_step is not None and not t.success]
    if not faulty_traces:
        return LocalizationMetrics(
            total_samples=len(traces),
            faulty_samples=0,
            top1_accuracy=0.0,
            top3_accuracy=0.0,
            top5_accuracy=0.0,
            mrr=0.0,
            exact_matches=0,
            top3_matches=0,
            per_fault_accuracy={}
        )

    exact = 0
    top3 = 0
    top5 = 0
    reciprocal_ranks: list[float] = []
    fault_counts: dict[str, int] = {}
    fault_correct: dict[str, int] = {}

    for t in faulty_traces:
        gt = t.fault_step
        ftype = t.fault_type or "unknown"
        fault_counts[ftype] = fault_counts.get(ftype, 0) + 1

        if model and model.is_fitted:
            scores = model.predict_trace(t)
            ranked = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
        else:
            # Heuristic ranking if no model fitted
            ranked = sorted(
                range(len(t.steps)),
                key=lambda i: (t.steps[i].has_error, t.steps[i].latency_ms),
                reverse=True
            )

        # Compute rank of gt
        if gt in ranked:
            rank = ranked.index(gt) + 1
            reciprocal_ranks.append(1.0 / rank)
            if rank == 1:
                exact += 1
                fault_correct[ftype] = fault_correct.get(ftype, 0) + 1
            if rank <= 3:
                top3 += 1
            if rank <= 5:
                top5 += 1
        else:
            reciprocal_ranks.append(0.0)

    n = len(faulty_traces)
    per_fault = {
        k: round(fault_correct.get(k, 0) / max(1, fault_counts[k]), 4)
        for k in fault_counts
    }

    return LocalizationMetrics(
        total_samples=len(traces),
        faulty_samples=n,
        top1_accuracy=round(exact / n, 4),
        top3_accuracy=round(top3 / n, 4),
        top5_accuracy=round(top5 / n, 4),
        mrr=round(sum(reciprocal_ranks) / n, 4),
        exact_matches=exact,
        top3_matches=top3,
        per_fault_accuracy=per_fault
    )
