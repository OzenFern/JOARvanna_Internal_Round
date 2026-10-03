"""
blackbox/evaluate/confidence.py
───────────────────────────────
Evaluates confidence calibration across High, Medium, and Low confidence predictions.
"""
from __future__ import annotations

from dataclasses import dataclass
from blackbox.capture.schema import AgentTrace
from blackbox.attribution.model import LocalAttributionModel
from blackbox.attribution.confidence import compute_confidence


@dataclass
class CalibrationBucket:
    confidence_tier: str  # "high", "medium", "low"
    total_predictions: int
    correct_predictions: int
    accuracy: float


@dataclass
class ConfidenceMetrics:
    high_tier: CalibrationBucket
    medium_tier: CalibrationBucket
    low_tier: CalibrationBucket
    overall_calibration_score: float  # ECE-like alignment


def eval_confidence(
    traces: list[AgentTrace],
    model: LocalAttributionModel
) -> ConfidenceMetrics:
    """
    Evaluates how well confidence levels ('high', 'medium', 'low') correlate with localization accuracy.
    """
    buckets = {
        "high": {"total": 0, "correct": 0},
        "medium": {"total": 0, "correct": 0},
        "low": {"total": 0, "correct": 0},
    }

    faulty = [t for t in traces if t.fault_step is not None]

    for t in faulty:
        if not model.is_fitted:
            continue
        scores = model.predict_trace(t)
        if not scores:
            continue

        top_step = max(scores, key=scores.get)
        conf = compute_confidence(scores)

        is_correct = (top_step == t.fault_step)
        if conf in buckets:
            buckets[conf]["total"] += 1
            if is_correct:
                buckets[conf]["correct"] += 1

    def make_bucket(name: str) -> CalibrationBucket:
        tot = buckets[name]["total"]
        cor = buckets[name]["correct"]
        acc = round(cor / max(1, tot), 4) if tot > 0 else 0.0
        return CalibrationBucket(name, tot, cor, acc)

    b_high = make_bucket("high")
    b_med = make_bucket("medium")
    b_low = make_bucket("low")

    # Ideal calibration: High Acc > Medium Acc > Low Acc
    score = 1.0 if (b_high.accuracy >= b_med.accuracy >= b_low.accuracy) else 0.75

    return ConfidenceMetrics(
        high_tier=b_high,
        medium_tier=b_med,
        low_tier=b_low,
        overall_calibration_score=score
    )
