"""
scripts/run_eval.py
───────────────────
CLI tool to run the full benchmark evaluation suite across localization accuracy,
generalization, confidence calibration, latency, and replay savings.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blackbox.capture.store import TraceStore
from blackbox.attribution.model import LocalAttributionModel
from blackbox.evaluate.localization import eval_localization
from blackbox.evaluate.confidence import eval_confidence
from blackbox.evaluate.latency import eval_latency
from blackbox.evaluate.counterfactual import eval_counterfactual_repairs
from blackbox.paths import ARTIFACTS_DIR, TRACES_DIR


def evaluate(traces_dir: Path = TRACES_DIR, model_path: Path = ARTIFACTS_DIR / "model.pkl"):
    store = TraceStore(traces_dir)
    traces = store.load_all()
    if not traces:
        print(f"Error: No traces found in {traces_dir}.")
        sys.exit(1)

    model = LocalAttributionModel()
    if model_path.exists():
        model.load(model_path)
    else:
        print("Warning: Model weights not found. Evaluating with calibrated heuristic baseline.")

    print(f"Evaluating Black Box Diagnostic System on {len(traces)} traces...\n")

    loc_metrics = eval_localization(traces, model)
    conf_metrics = eval_confidence(traces, model)
    lat_metrics = eval_latency(traces, model)
    cf_metrics = eval_counterfactual_repairs([t for t in traces if not t.success])

    print("=" * 60)
    print("1. LOCALIZATION ACCURACY & CALIBRATION")
    print("=" * 60)
    print(f"  • Total Evaluated Traces:       {loc_metrics.total_samples}")
    print(f"  • Faulty Traces Analyzed:       {loc_metrics.faulty_samples}")
    print(f"  • Top-1 Fault Localization Acc: {loc_metrics.top1_accuracy:.1%}")
    print(f"  • Top-3 Fault Localization Acc: {loc_metrics.top3_accuracy:.1%}")
    print(f"  • Mean Reciprocal Rank (MRR):   {loc_metrics.mrr:.3f}")
    print(f"  • High-Confidence Accuracy:     {conf_metrics.high_tier.accuracy:.1%}")
    print(f"  • Medium-Confidence Accuracy:   {conf_metrics.medium_tier.accuracy:.1%}")

    print("\n" + "=" * 60)
    print("2. PERFORMANCE & REPLAY SAVINGS")
    print("=" * 60)
    print(f"  • Mean Diagnosis Latency:       {lat_metrics.mean_local_latency_ms:.2f} ms")
    print(f"  • P95 Diagnosis Latency:        {lat_metrics.p95_local_latency_ms:.2f} ms")
    print(f"  • Sub-50ms SLA Met:             {'YES' if lat_metrics.target_met else 'NO'}")
    print(f"  • Counterfactual Repair Success:{cf_metrics.repair_success_rate:.1f}%")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run benchmark evaluation.")
    parser.add_argument("-t", "--traces", type=Path, default=TRACES_DIR, help="Traces dir")
    parser.add_argument("-m", "--model", type=Path, default=ARTIFACTS_DIR / "model.pkl", help="Model path")
    args = parser.parse_args()
    evaluate(args.traces, args.model)
