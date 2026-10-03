"""
blackbox/attribution/model.py
──────────────────────────────
The core local attribution model.
Uses Gradient Boosting over dense features + TF-IDF embeddings.
(A full BiGRU/Transformer would require PyTorch, which is omitted here
for simplicity and speed, relying on Scikit-Learn instead).
"""
from __future__ import annotations
import pickle
import numpy as np
from pathlib import Path
from sklearn.ensemble import GradientBoostingClassifier
from blackbox.capture.schema import AgentTrace
from blackbox.features.dataset import build_dataset
from blackbox.features.embeddings import TraceEmbedder
from blackbox.faults.labels import LabelStore

class LocalAttributionModel:
    def __init__(self):
        self.embedder = TraceEmbedder(max_features=128)
        self.clf = GradientBoostingClassifier(
            n_estimators=150, max_depth=5, learning_rate=0.05
        )
        self.is_fitted = False
        
    def fit(self, traces: list[AgentTrace], labels: LabelStore) -> None:
        self.embedder.fit(traces)
        X, y = build_dataset(traces, labels, self.embedder)
        if len(X) == 0: return
        self.clf.fit(X, y)
        self.is_fitted = True
        
    def predict_trace(self, trace: AgentTrace) -> dict[int, float]:
        if not self.is_fitted:
            raise RuntimeError("Model not fitted")
        # Build dataset for 1 trace
        class DummyLabels:
            def get(self, _): return None
        X, _ = build_dataset([trace], DummyLabels(), self.embedder)
        probs = self.clf.predict_proba(X)[:, 1] if X.shape[0] > 0 else np.array([])
        mx = probs.max() + 1e-9 if probs.size > 0 else 1.0
        return {i: float(p / mx) for i, p in enumerate(probs)}

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"embedder": self.embedder, "clf": self.clf}, f)
            
    def load(self, path: Path) -> None:
        with open(path, "rb") as f:
            state = pickle.load(f)
            self.embedder = state["embedder"]
            self.clf = state["clf"]
            self.is_fitted = True
