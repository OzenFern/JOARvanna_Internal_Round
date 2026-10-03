"""
blackbox/explain/contrast.py
────────────────────────────
Contrastive explanation engine.
Compares a failed trace against a successful reference execution to highlight the turning point.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from blackbox.capture.schema import AgentTrace
from blackbox.compare.divergence import find_divergence


@dataclass
class ContrastiveExplanation:
    has_reference: bool
    reference_run_id: str | None
    turning_point_step: int | None
    what_failed: str
    what_succeeded: str
    explanation: str


def generate_contrastive_explanation(
    failed_trace: AgentTrace,
    reference_trace: AgentTrace | None = None
) -> ContrastiveExplanation:
    """
    Generates a contrastive explanation contrasting the failed run with a reference success run.
    """
    if reference_trace is None:
        # Generate synthetic reference contrast based on expected output
        turning_point = failed_trace.fault_step if failed_trace.fault_step is not None else 1
        return ContrastiveExplanation(
            has_reference=False,
            reference_run_id=None,
            turning_point_step=turning_point,
            what_failed=f"Produced output '{failed_trace.final_output}' (failed verification)",
            what_succeeded=f"Target output was '{failed_trace.expected_output}'",
            explanation=(
                f"In this run, execution deviated around Step {turning_point}. "
                f"A successful run would have computed/retrieved '{failed_trace.expected_output}', "
                f"whereas this run yielded '{failed_trace.final_output}'."
            )
        )

    div = find_divergence(failed_trace, reference_trace)
    tp = div.earliest_step_index

    if tp is not None and tp < len(failed_trace.steps) and tp < len(reference_trace.steps):
        s_fail = failed_trace.steps[tp]
        s_ref = reference_trace.steps[tp]
        what_failed = f"Step {tp} ({s_fail.name}) produced: {s_fail.output!r:.50}"
        what_succeeded = f"Step {tp} ({s_ref.name}) produced: {s_ref.output!r:.50}"
        explanation = (
            f"Execution diverged at Step {tp} ({div.divergence_type}). "
            f"The failed run output {s_fail.output!r:.40} while the reference run produced {s_ref.output!r:.40}. "
            f"This cascading error resulted in final output mismatch."
        )
    else:
        what_failed = str(failed_trace.final_output)
        what_succeeded = str(reference_trace.final_output)
        explanation = "Both traces followed the same execution path but diverged at final evaluation."

    return ContrastiveExplanation(
        has_reference=True,
        reference_run_id=reference_trace.run_id,
        turning_point_step=tp,
        what_failed=what_failed,
        what_succeeded=what_succeeded,
        explanation=explanation
    )
