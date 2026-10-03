"""
blackbox/features/dataset.py
─────────────────────────────
Converts lists of AgentTrace into ML-ready matrices.
Supports Numpy when available, with clean native Python lists fallback.
"""
from __future__ import annotations

from typing import Any
from blackbox.capture.schema import AgentTrace
from blackbox.features.step_features import extract_features
from blackbox.features.embeddings import TraceEmbedder
from blackbox.faults.labels import LabelStore

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None


def build_dataset(traces: list[AgentTrace], labels: LabelStore, embedder: TraceEmbedder) -> tuple[Any, Any]:
    """
    Returns (X, y) matrices.
    """
    X_rows = []
    y_rows = []

    for trace in traces:
        lbl = labels.get(trace.run_id)
        fault_step = lbl.fault_step if lbl else -1

        n = len(trace.steps)
        embs = embedder.transform_trace(trace)

        for i, step in enumerate(trace.steps):
            dense = extract_features(step, n)
            emb_vec = embs[i] if (embs is not None and i < len(embs)) else []
            if hasattr(emb_vec, "tolist"):
                emb_vec = emb_vec.tolist()
            row = list(dense) + list(emb_vec)
            X_rows.append(row)
            y_rows.append(1 if i == fault_step else 0)

    if HAS_NUMPY:
        return np.array(X_rows, dtype=np.float32), np.array(y_rows, dtype=np.int32)
    return X_rows, y_rows
