"""
blackbox/explain/rationale.py
──────────────────────────────
Creates a concise evidence-based explanation.
"""
from __future__ import annotations
from blackbox.capture.schema import AgentTrace

def generate_rationale(trace: AgentTrace, step_index: int, confidence: str) -> str:
    """Generates a rationale string."""
    if step_index < 0 or step_index >= len(trace.steps):
        return "Invalid step index."
        
    step = trace.steps[step_index]
    
    reasons = []
    if step.has_error:
        reasons.append(f"It explicitly raised an error: {step.error.message}")
    if step.tool:
        reasons.append(f"The `{step.tool}` tool call might have returned unexpected results.")
    else:
        reasons.append("The LLM reasoning might have drifted here.")
        
    base = f"Step {step_index} ({step.name}) is suspicious ({confidence} confidence)."
    return base + "\n\nWhy:\n- " + "\n- ".join(reasons)
