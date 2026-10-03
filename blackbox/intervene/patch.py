"""
blackbox/intervene/patch.py
───────────────────────────
Defines step patch specifications for counterfactual intervention.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from blackbox.capture.schema import AgentTrace, AgentStep


@dataclass
class StepPatch:
    step_index: int
    patch_kind: str = "override_output"  # "override_output" | "modify_args" | "retry" | "clear_error"
    new_output: Any = None
    new_inputs: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    rationale: str = ""


def apply_patch(step: AgentStep, patch: StepPatch) -> AgentStep:
    """Applies a patch specification in-place to an AgentStep."""
    if patch.patch_kind in ("override_output", "retry"):
        step.output = patch.new_output
        if step.has_error:
            step.error = None
    elif patch.patch_kind == "modify_args":
        step.inputs.update(patch.new_inputs)
        if step.tool_call:
            step.tool_call.arguments.update(patch.new_inputs)
    elif patch.patch_kind == "clear_error":
        step.error = None

    step.metadata["patched"] = True
    step.metadata["patch_kind"] = patch.patch_kind
    return step
