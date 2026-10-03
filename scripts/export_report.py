"""
scripts/export_report.py
────────────────────────
Exports diagnostic reports in Markdown and JSON formats for audit and post-mortems.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blackbox.capture.store import TraceStore
from blackbox.attribution.model import LocalAttributionModel
from blackbox.analysis.local import analyze_local
from blackbox.debug.diagnose import create_diagnosis
from blackbox.debug.suggestions import generate_suggestions
from blackbox.analysis.consensus import ConsensusResult


def export(run_id: str, traces_dir: Path = Path("data/traces"), output_file: Path = Path("data/reports/report.md")):
    store = TraceStore(traces_dir)
    trace = store.load(run_id)

    model = LocalAttributionModel()
    model_p = Path("data/artifacts/model.pkl")
    if model_p.exists():
        model.load(model_p)

    local_res = analyze_local(trace, model)
    consensus = ConsensusResult(
        scores=local_res.scores,
        top_step=local_res.top_step,
        agreement=True,
        final_confidence=local_res.confidence
    )
    diag = create_diagnosis(trace, consensus)
    sugs = generate_suggestions(trace, diag.likely_source)

    output_file.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Black Box Root-Cause Post-Mortem Report",
        f"**Run ID:** `{trace.run_id}` | **Task Domain:** `{trace.task_type.value.upper()}` | **Status:** `{'SUCCESS' if trace.success else 'FAILED'}`",
        f"**Task Description:** {trace.task_description}",
        f"**Expected Output:** `{trace.expected_output}` | **Actual Output:** `{trace.final_output}`",
        "",
        f"## 1. Executive Summary & Root Cause Diagnosis",
        f"- **Primary Suspect:** Step {diag.likely_source} (`{trace.steps[diag.likely_source].name if diag.likely_source < len(trace.steps) else 'unknown'}`)",
        f"- **Confidence Level:** `{diag.confidence.upper()}` (Suspicion Score: {diag.suspicion:.3f})",
        f"- **Rationale:** {diag.rationale}",
        "",
        f"## 2. Step Execution Timeline & Suspicion Scores",
        "| Step | Name | Type | Latency (ms) | Suspicion | Output Summary |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |"
    ]

    for i, s in enumerate(trace.steps):
        score = local_res.scores.get(i, 0.0)
        marker = " ⚠️ **[CULPRIT]**" if i == diag.likely_source else ""
        out_prev = str(s.output).replace("\n", " ")[:40]
        lines.append(f"| {i} | `{s.name}` | {s.step_type.value} | {s.latency_ms:.1f} | {score:.3f}{marker} | `{out_prev}` |")

    lines.extend([
        "",
        "## 3. Actionable Remediation Suggestions",
    ])
    for s in sugs:
        lines.append(f"### • {s.title} ({s.action_type.upper()})")
        lines.append(f"- **Description:** {s.description}")
        lines.append(f"- **Patch Payload:** `{json.dumps(s.patch_payload)}`")
        lines.append("")

    content = "\n".join(lines)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Diagnostic report exported to: {output_file.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export diagnostic report.")
    parser.add_argument("run_id", help="Trace run ID")
    parser.add_argument("-t", "--traces", type=Path, default=Path("data/traces"), help="Traces dir")
    parser.add_argument("-o", "--out", type=Path, default=Path("data/reports/report.md"), help="Report output file")
    args = parser.parse_args()
    export(args.run_id, args.traces, args.out)
