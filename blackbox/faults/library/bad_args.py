"""blackbox/faults/library/bad_args.py
Agent calls a tool with wrong argument types or values.
Example: calculator receives a string instead of an expression,
or search receives an empty / irrelevant query.
"""
from __future__ import annotations
import random
from typing import Any

def inject(true_output: Any, step_plan: dict, rng: random.Random) -> Any:
    tool = step_plan.get("tool", "")

    if tool == "calculator":
        # Pass a mangled expression (wrong operator, wrong number)
        expr = step_plan.get("expression", "1+1")
        scale = rng.choice([0.5, 2.0, 10.0, 0.1])
        try:
            from blackbox.agents.tools.calculator import calculator
            return round(calculator(expr) * scale, 4)
        except Exception:
            return 0.0

    if tool == "search":
        # Use a wrong / irrelevant query → bad search results → wrong answer
        bad_queries = ["asdfghjkl", "nothing relevant", "xyz123", ""]
        return rng.choice(bad_queries)

    if tool == "execute_sql":
        # Wrong SQL (wrong table or wrong column)
        return []  # empty result from bad query

    if tool == "retrieve":
        # Wrong document ID
        wrong_ids = ["d99", "d00", "wrong"]
        return rng.choice(wrong_ids)

    # For LLM steps: return a plausible but wrong value
    if isinstance(true_output, (int, float)):
        return round(float(true_output) * rng.choice([0.5, 1.5, 2.0, 0.3]), 4)
    if isinstance(true_output, str):
        return true_output[:max(1, len(true_output)//2)]  # truncate
    return true_output
