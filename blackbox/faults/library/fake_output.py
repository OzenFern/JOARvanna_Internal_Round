"""blackbox/faults/library/fake_output.py
Agent completely fabricates a result without doing the work.
"""
from __future__ import annotations
import random
from typing import Any

def inject(true_output: Any, step_plan: dict, rng: random.Random) -> Any:
    tool = step_plan.get("tool", "")
    
    if tool == "calculator":
        return round(rng.uniform(-1000, 1000), 2)
        
    if tool == "execute_sql":
        return [{"fake_column": "fake_data", "amount": 999.99}]
        
    if tool == "search":
        return [{"doc_id": "d_fake", "title": "Fake Document", "score": 1.0}]
        
    if isinstance(true_output, str):
        return rng.choice([
            "I'm sorry, I cannot fulfill this request.",
            "Based on my calculations, the answer is 42.",
            "Error: service unavailable.",
            "The data indicates otherwise.",
        ])
        
    if isinstance(true_output, (int, float)):
        return 0.0
        
    return None
