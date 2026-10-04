"""
scripts/run_analysis.py
───────────────────────
CLI tool to inspect and diagnose an individual trace file.
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
from blackbox.analysis.local import analyze_local
from blackbox.analysis.cloud import analyze_cloud
from blackbox.paths import ARTIFACTS_DIR, TRACES_DIR
from blackbox.debug.diagnose import create_diagnosis
from blackbox.debug.suggestions import generate_suggestions
from blackbox.analysis.consensus import ConsensusResult


def analyze(run_id: str, traces_dir: Path = TRACES_DIR, model_path: Path = ARTIFACTS_DIR / "model.pkl", with_cloud: bool = False):
    store = TraceStore(traces_dir)
    try:
        trace = store.load(run_id)
    except Exception as e:
        print(f"Error: Failed to load trace {run_id}: {e}")
        sys.exit(1)

    model = LocalAttributionModel()
    if model_path.exists():
        model.load(model_path)

    print(f"\nAnalyzing Run: {run_id} ({trace.task_type.value.upper()})")
    print(f"Task: {trace.task_description}")
    print(f"Outcome: {'SUCCESS' if trace.success else 'FAILED'}")

    local_res = analyze_local(trace, model)
    consensus = ConsensusResult(
        scores=local_res.scores,
        top_step=local_res.top_step,
        agreement=True,
        final_confidence=local_res.confidence
    )
    diagnosis = create_diagnosis(trace, consensus)

    print("\n" + "=" * 60)
    print("STEP SUSPICION ATTRIBUTION:")
    print("=" * 60)
    for i, s in enumerate(trace.steps):
        score = local_res.scores.get(i, 0.0)
        is_top = (i == local_res.top_step)
        flag = " [CULPRIT]" if is_top else ""
        print(f"  Step {i:02d} | {s.name:<18} | Suspicion: {score:.3f}{flag:<10} | Out: {str(s.output)[:35]}")

    print("\n" + "=" * 60)
    print("DIAGNOSIS VERDICT:")
    print("=" * 60)
    culprit_name = trace.steps[diagnosis.likely_source].name if diagnosis.likely_source < len(trace.steps) else 'unknown'
    print(f"  • Primary Culprit: Step {diagnosis.likely_source} ({culprit_name})")
    print(f"  • Confidence:      {diagnosis.confidence.upper()}")
    print(f"  • Rationale:       {diagnosis.rationale}")

    sugs = generate_suggestions(trace, diagnosis.likely_source)
    if sugs:
        print("\nActionable Remediation Suggestions:")
        for s in sugs:
            print(f"  • [{s.action_type.upper()}] {s.title}: {s.description}")

    if with_cloud:
        print("\nRunning Cloud Verifier...")
        cloud_res = analyze_cloud(trace)
        print(f"  • Cloud Suspect: Step {cloud_res.top_step}")
        print(f"  • Cloud Reasoning: {cloud_res.reasoning}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze an agent trace.")
    parser.add_argument("run_id", help="Trace run ID to analyze")
    parser.add_argument("-t", "--traces", type=Path, default=TRACES_DIR, help="Traces dir")
    parser.add_argument("-m", "--model", type=Path, default=ARTIFACTS_DIR / "model.pkl", help="Model path")
    parser.add_argument("-c", "--cloud", action="store_true", help="Run cloud LLM verification")
    args = parser.parse_args()
    analyze(args.run_id, args.traces, args.model, args.cloud)
