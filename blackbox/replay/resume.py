"""
blackbox/replay/resume.py
─────────────────────────
Allows resuming from a step instead of rerunning everything.
"""
from __future__ import annotations
from blackbox.capture.schema import AgentTrace

def resume_from_step(trace: AgentTrace, step_index: int, patched_output=None):
    # This is a stub for the complex resume logic
    return trace
