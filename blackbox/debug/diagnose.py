"""
blackbox/debug/diagnose.py
───────────────────────────
Combines exception + suspected step + confidence + evidence into a structured diagnosis.
"""
from __future__ import annotations
from dataclasses import dataclass
from blackbox.capture.schema import AgentTrace
from blackbox.analysis.consensus import ConsensusResult
from blackbox.explain.rationale import generate_rationale

@dataclass
class Diagnosis:
    failure_mode: str
    likely_source: int
    suspicion: float
    confidence: str
    rationale: str

def create_diagnosis(trace: AgentTrace, consensus: ConsensusResult) -> Diagnosis:
    if trace.error:
        f_mode = f"{trace.error.error_type}: {trace.error.message}"
    elif not trace.success:
        f_mode = "Silent failure (wrong answer)"
    else:
        f_mode = "Success"
        
    top = consensus.top_step
    score = consensus.scores.get(top, 0.0)
    conf = "high" if score > 0.8 else "medium" if score > 0.5 else "low"
    
    rat = generate_rationale(trace, top, conf)
    
    return Diagnosis(f_mode, top, score, conf, rat)
