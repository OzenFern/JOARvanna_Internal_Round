"""
blackbox/debug/suggestions.py
──────────────────────────────
Generates possible remediation actions.
"""
from __future__ import annotations
from dataclasses import dataclass
from blackbox.capture.schema import AgentTrace

@dataclass
class Suggestion:
    action: str
    detail: str

def generate_suggestions(trace: AgentTrace, suspect_step: int) -> list[Suggestion]:
    if suspect_step < 0 or suspect_step >= len(trace.steps):
        return []
        
    step = trace.steps[suspect_step]
    suggs = []
    
    if step.tool == "execute_sql":
        suggs.append(Suggestion("Modify SQL", "Check syntax and table names in the query."))
    elif step.tool == "calculator":
        suggs.append(Suggestion("Check Expression", "Ensure numeric types and valid operators are used."))
    elif step.tool == "search":
        suggs.append(Suggestion("Refine Query", "Make the search query more specific."))
        
    suggs.append(Suggestion("Replay from Checkpoint", f"Patch the output of Step {suspect_step} and replay."))
    
    return suggs
