"""
blackbox/replay/checkpoint.py
──────────────────────────────
Stores the agent state at important points.
"""
from __future__ import annotations
from blackbox.capture.schema import Checkpoint

# Stubs for checkpoint management
def save_checkpoint(cp: Checkpoint) -> None:
    pass

def load_checkpoint(cp_id: str) -> Checkpoint | None:
    return None
