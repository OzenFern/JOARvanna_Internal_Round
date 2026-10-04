"""
scripts/train_local.py
──────────────────────
CLI tool to train the LocalAttributionModel on stored traces and ground-truth labels.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blackbox.capture.store import TraceStore
from blackbox.paths import ARTIFACTS_DIR, TRACES_DIR
from blackbox.faults.labels import LabelStore
from blackbox.attribution.model import LocalAttributionModel
from blackbox.evaluate.localization import eval_localization


def train(traces_dir: Path = TRACES_DIR, labels_file: Path = ARTIFACTS_DIR / "labels.json", output_model: Path = ARTIFACTS_DIR / "model.pkl"):
    store = TraceStore(traces_dir)
    traces = store.load_all()
    if not traces:
        print(f"Error: No traces found in {traces_dir}. Run `python scripts/generate_traces.py` first.")
        sys.exit(1)

    labels = LabelStore(labels_file)
    if not labels_file.exists():
        for t in traces:
            if t.fault_step is not None:
                labels.set(t.run_id, t.fault_step, t.fault_type)

    print(f"Training LocalAttributionModel on {len(traces)} traces...")
    t0 = time.perf_counter()

    model = LocalAttributionModel()
    model.fit(traces, labels)
    model.save(output_model)
    elapsed = (time.perf_counter() - t0) * 1000

    metrics = eval_localization(traces, model)

    print("=" * 50)
    print("Model Training Results:")
    print(f"  • Training Samples: {len(traces)}")
    print(f"  • Training Latency: {elapsed:.1f} ms")
    print(f"  • Top-1 Accuracy:   {metrics.top1_accuracy:.1%}")
    print(f"  • Top-3 Accuracy:   {metrics.top3_accuracy:.1%}")
    print(f"  • MRR:              {metrics.mrr:.3f}")
    print(f"  • Saved Model to:   {output_model.resolve()}")
    print("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train local attribution ML model.")
    parser.add_argument("-t", "--traces", type=Path, default=TRACES_DIR, help="Traces dir")
    parser.add_argument("-l", "--labels", type=Path, default=ARTIFACTS_DIR / "labels.json", help="Labels JSON")
    parser.add_argument("-o", "--out", type=Path, default=ARTIFACTS_DIR / "model.pkl", help="Model output")
    args = parser.parse_args()
    train(args.traces, args.labels, args.out)
