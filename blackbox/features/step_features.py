"""
blackbox/features/step_features.py
───────────────────────────────────
Extracts numeric features from a single AgentStep.
"""
from __future__ import annotations

import math
from typing import Any

from blackbox.capture.schema import AgentStep, StepType

# List of known tools for one-hot encoding
_TOOLS = ["calculator", "search", "retrieve", "execute_sql", "get_schema", ""]

def _safe_len(obj: Any) -> int:
    if isinstance(obj, str): return len(obj)
    if isinstance(obj, list): return len(obj)
    if isinstance(obj, dict): return len(obj)
    return 1

def _shannon_entropy(text: str) -> float:
    if not text: return 0.0
    counts = {}
    for c in text:
        counts[c] = counts.get(c, 0) + 1
    L = len(text)
    ent = 0.0
    for count in counts.values():
        p = count / L
        ent -= p * math.log2(p)
    return ent

def extract_features(step: AgentStep, total_steps: int) -> list[float]:
    """Returns a fixed-length feature vector for the step."""
    # 1. Position
    rel_pos = step.step_index / max(1, total_steps - 1)
    
    # 2. Step type (one-hot)
    is_llm = float(step.step_type == StepType.LLM_CALL)
    is_tool = float(step.step_type == StepType.TOOL_CALL)
    
    # 3. Tool (one-hot)
    tool_name = step.tool or ""
    tool_feats = [float(tool_name == t) for t in _TOOLS]
    
    # 4. Content length and entropy
    in_str  = str(step.inputs)
    out_str = str(step.output)
    in_len  = math.log1p(len(in_str))
    out_len = math.log1p(len(out_str))
    
    out_ent = _shannon_entropy(out_str[:1000]) # cap for performance
    
    # 5. Latency & Errors
    lat = math.log1p(step.latency_ms)
    has_err = float(step.has_error)
    
    # 6. Tokens
    tok_in = math.log1p(step.tokens.input_tokens) if step.tokens else 0.0
    tok_out = math.log1p(step.tokens.output_tokens) if step.tokens else 0.0
    
    return [
        rel_pos, is_llm, is_tool,
        in_len, out_len, out_ent,
        lat, has_err, tok_in, tok_out
    ] + tool_feats

def feature_names() -> list[str]:
    return [
        "rel_pos", "is_llm", "is_tool",
        "in_len_log", "out_len_log", "out_entropy",
        "latency_log", "has_error", "tok_in_log", "tok_out_log"
    ] + [f"tool_{t or 'none'}" for t in _TOOLS]
