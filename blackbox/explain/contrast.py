"""
blackbox/explain/contrast.py
────────────────────────────
Compares the failed execution against successful executions.
"""
from __future__ import annotations
from blackbox.capture.schema import AgentTrace

def contrast_traces(failed: AgentTrace, successful: AgentTrace) -> dict[str, str]:
    """Returns a dict mapping step index -> difference description."""
    diffs = {}
    n = min(len(failed.steps), len(successful.steps))
    for i in range(n):
        s_fail = failed.steps[i]
        s_succ = successful.steps[i]
        
        if s_fail.tool != s_succ.tool:
            diffs[i] = f"Tool mismatch: {s_fail.tool} vs {s_succ.tool}"
            continue
            
        # Very simple diff for strings
        if str(s_fail.output) != str(s_succ.output):
            diffs[i] = "Output differs significantly."
            
    if len(failed.steps) > len(successful.steps):
        diffs[n] = "Failed trace has extra steps."
    elif len(failed.steps) < len(successful.steps):
        diffs[n] = "Failed trace terminated early."
        
    return diffs
