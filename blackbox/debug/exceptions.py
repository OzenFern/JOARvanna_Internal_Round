"""
blackbox/debug/exceptions.py
─────────────────────────────
Classifies errors.
"""
from __future__ import annotations

def classify_error(err_type: str, err_msg: str) -> str:
    err_type = err_type.lower()
    msg = err_msg.lower()
    
    if "timeout" in err_type or "timeout" in msg:
        return "TimeoutError"
    if "db" in err_type or "sql" in msg:
        return "DatabaseError"
    if "tool" in err_type:
        return "ToolError"
    return "UnknownError"
