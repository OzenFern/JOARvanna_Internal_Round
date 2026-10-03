"""
blackbox/intervene/branch.py
────────────────────────────
Creates counterfactual branches from an existing trace with applied interventions.
"""
from __future__ import annotations

import uuid
from blackbox.capture.schema import AgentTrace
from blackbox.intervene.patch import StepPatch
from blackbox.replay.resume import resume_from_step


def create_branch(trace: AgentTrace, patch: StepPatch, branch_name: str | None = None) -> AgentTrace:
    """
    Creates an alternative execution branch by applying `patch` at `patch.step_index`
    and resuming downstream execution.
    """
    child_id = branch_name or f"{trace.run_id}-branch-{patch.step_index}-{uuid.uuid4().hex[:4]}"
    
    branched_trace = resume_from_step(
        trace=trace,
        step_index=patch.step_index,
        patched_output=patch.new_output,
        patched_inputs=patch.new_inputs if patch.new_inputs else None,
        new_run_id=child_id
    )

    branched_trace.meta["branch_patch"] = {
        "step_index": patch.step_index,
        "patch_kind": patch.patch_kind,
        "description": patch.description,
        "rationale": patch.rationale
    }

    return branched_trace
