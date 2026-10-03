"""
blackbox/attribution/baselines/gbm.py
──────────────────────────────────────
Traditional ML baseline using only dense features (no embeddings).
"""
from __future__ import annotations
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from blackbox.capture.schema import AgentTrace
from blackbox.features.step_features import extract_features

class GBMModel:
    def __init__(self):
        self.clf = GradientBoostingClassifier(n_estimators=100, max_depth=3)
        
    def fit(self, traces: list[AgentTrace], labels: dict[str, int]) -> None:
        X, y = [], []
        for t in traces:
            fault_idx = labels.get(t.run_id, -1)
            n = len(t.steps)
            for i, s in enumerate(t.steps):
                X.append(extract_features(s, n))
                y.append(1 if i == fault_idx else 0)
        if not X: return
        self.clf.fit(np.array(X), np.array(y))
        
    def predict(self, trace: AgentTrace) -> dict[int, float]:
        n = len(trace.steps)
        X = [extract_features(s, n) for s in trace.steps]
        probs = self.clf.predict_proba(np.array(X))[:, 1]
        mx = probs.max() + 1e-9
        return {i: p / mx for i, p in enumerate(probs)}
