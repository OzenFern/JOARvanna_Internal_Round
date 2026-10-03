"""blackbox/faults/library/poisoned_context.py
Agent's context (e.g. retrieved document, database schema) is subtly altered.
"""
from __future__ import annotations
import random
from typing import Any

def inject(true_output: Any, step_plan: dict, rng: random.Random) -> Any:
    tool = step_plan.get("tool", "")

    if tool == "retrieve":
        # Modify the document content
        content = str(true_output)
        if not content: return ""
        # Insert a contradictory fact
        poison = rng.choice([
            " Actually, this is incorrect.",
            " Recent studies have disproven this.",
            " NOT ",
        ])
        idx = rng.randint(0, len(content) // 2)
        return content[:idx] + poison + content[idx:]

    if tool == "get_schema":
        # Corrupt the schema definition
        schema = dict(true_output) if isinstance(true_output, dict) else {}
        if not schema: return {}
        # Rename a random column
        tbl = rng.choice(list(schema.keys()))
        if schema[tbl]:
            col_idx = rng.randint(0, len(schema[tbl]) - 1)
            schema[tbl][col_idx] += "_xyz"
        return schema
    
    if tool == "search":
        # Return wrong search results
        results = list(true_output) if isinstance(true_output, list) else []
        if results:
            for r in results:
                if isinstance(r, dict) and "title" in r:
                    r["title"] = "IRRELEVANT: " + r["title"]
        return results

    # Fallback for LLM steps: inject hallucination
    if isinstance(true_output, str):
        return f"{true_output} However, {rng.randint(100, 999)} is also a valid answer."
    
    return true_output
