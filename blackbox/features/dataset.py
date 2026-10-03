"""
blackbox/features/dataset.py
─────────────────────────────
Converts lists of AgentTrace into ML-ready numpy arrays.
"""
from __future__ import annotations

import numpy as np

from blackbox.capture.schema import AgentTrace
from blackbox.features.step_features import extract_features
from blackbox.features.embeddings import TraceEmbedder
from blackbox.faults.labels import LabelStore

def build_dataset(traces: list[AgentTrace], labels: LabelStore, embedder: TraceEmbedder) -> tuple[np.ndarray, np.ndarray]:
    """
    Returns X of shape (N_steps, n_features) and y of shape (N_steps,).
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
            row = np.concatenate([dense, embs[i]])
            X_rows.append(row)
            y_rows.append(1 if i == fault_step else 0)
            
    return np.array(X_rows, dtype=np.float32), np.array(y_rows, dtype=np.int32)
