"""blackbox/faults/library/truncation.py
Agent's output is abruptly cut off, simulating context limit or max_tokens hit.
"""
from __future__ import annotations
import random
from typing import Any

def inject(true_output: Any, step_plan: dict, rng: random.Random) -> Any:
    if isinstance(true_output, str):
        L = len(true_output)
        if L <= 2:
            return ""
        # Cut off somewhere in the middle
        idx = rng.randint(L // 4, L * 3 // 4)
        return true_output[:idx]
    
    if isinstance(true_output, list):
        L = len(true_output)
        if L == 0:
            return []
        idx = max(1, rng.randint(1, max(1, L // 2)))
        return true_output[:idx]
    
    if isinstance(true_output, dict):
        keys = list(true_output.keys())
        if not keys: return {}
        idx = max(1, rng.randint(1, max(1, len(keys) // 2)))
        return {k: true_output[k] for k in keys[:idx]}
        
    return true_output
