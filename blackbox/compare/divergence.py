"""
blackbox/compare/divergence.py
──────────────────────────────
Identifies the earliest divergence point between two execution traces
and provides material difference explanations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from blackbox.capture.schema import AgentTrace
from blackbox.compare.align import align_traces, TraceAlignment, AlignedStepPair


@dataclass
class DivergenceResult:
    has_divergence: bool
    earliest_step_index: int | None
    divergence_type: str | None  # "output_mismatch", "error_mismatch", "tool_mismatch", "length_mismatch", "none"
    explanation: str
    alignment: TraceAlignment
    left_outcome_success: bool
    right_outcome_success: bool
    left_final_output: Any
    right_final_output: Any
    diff_details: dict[str, Any] = field(default_factory=dict)


def find_divergence(t1: AgentTrace, t2: AgentTrace) -> DivergenceResult:
    """
    Finds the earliest step where two traces diverge and describes the material impact.
    """
    alignment = align_traces(t1, t2)
    
    for pair in alignment.pairs:
        if pair.status != "match":
            s1 = pair.left_step
            s2 = pair.right_step
            
            diff_details: dict[str, Any] = {}
            if s1 and s2:
                if s1.step_type != s2.step_type:
                    div_type = "step_type_mismatch"
                elif s1.tool != s2.tool:
                    div_type = "tool_mismatch"
                elif s1.has_error != s2.has_error:
                    div_type = "error_mismatch"
                else:
                    div_type = "output_mismatch"

                diff_details = {
                    "step_index": pair.index,
                    "left_step_name": s1.name,
                    "right_step_name": s2.name,
                    "left_output": s1.output,
                    "right_output": s2.output,
                    "left_inputs": s1.inputs,
                    "right_inputs": s2.inputs,
                    "left_error": s1.error.message if s1.error else None,
                    "right_error": s2.error.message if s2.error else None,
                    "left_latency_ms": s1.latency_ms,
                    "right_latency_ms": s2.latency_ms,
                }
            elif s1:
                div_type = "length_mismatch"
                diff_details = {"missing_in": "right", "step_index": pair.index, "left_step_name": s1.name}
            else:
                div_type = "length_mismatch"
                diff_details = {"missing_in": "left", "step_index": pair.index, "right_step_name": s2.name}

            explanation = (
                f"Earliest divergence detected at Step {pair.index} ({div_type}): "
                f"{pair.divergence_reason or 'Steps differ in output or configuration.'}"
            )
            
            return DivergenceResult(
                has_divergence=True,
                earliest_step_index=pair.index,
                divergence_type=div_type,
                explanation=explanation,
                alignment=alignment,
                left_outcome_success=t1.success,
                right_outcome_success=t2.success,
                left_final_output=t1.final_output,
                right_final_output=t2.final_output,
                diff_details=diff_details
            )

    # If no step-level divergence
    outcome_match = (t1.success == t2.success) and (str(t1.final_output) == str(t2.final_output))
    return DivergenceResult(
        has_divergence=not outcome_match,
        earliest_step_index=None if outcome_match else len(t1.steps) - 1,
        divergence_type="none" if outcome_match else "outcome_only",
        explanation="Both traces executed identical step sequences and outputs." if outcome_match else "Steps match, but final evaluation differ.",
        alignment=alignment,
        left_outcome_success=t1.success,
        right_outcome_success=t2.success,
        left_final_output=t1.final_output,
        right_final_output=t2.final_output,
        diff_details={}
    )
