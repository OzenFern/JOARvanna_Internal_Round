"""
blackbox/attribution/model.py
──────────────────────────────
The core local attribution model.
Uses Gradient Boosting over dense features + TF-IDF embeddings when Scikit-Learn is installed,
and a discriminative statistical anomaly classifier in pure Python environments.
"""
from __future__ import annotations

import math
import pickle
from pathlib import Path
from typing import Any

from blackbox.capture.schema import AgentTrace
from blackbox.features.dataset import build_dataset
from blackbox.features.embeddings import TraceEmbedder
from blackbox.faults.labels import LabelStore

try:
    from sklearn.ensemble import GradientBoostingClassifier
    import numpy as np
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    np = None


class LocalAttributionModel:
    def __init__(self):
        self.embedder = TraceEmbedder(max_features=128)
        self.is_fitted = False
        self.feature_weights: list[float] = []
        self.feature_means: list[float] = []
        self.feature_stds: list[float] = []
        if HAS_SKLEARN:
            self.clf = GradientBoostingClassifier(n_estimators=150, max_depth=5, learning_rate=0.05)
        else:
            self.clf = None

    def fit(self, traces: list[AgentTrace], labels: LabelStore) -> None:
        if not traces:
            return
        self.embedder.fit(traces)
        X, y = build_dataset(traces, labels, self.embedder)

        if HAS_SKLEARN and self.clf is not None:
            if len(X) > 0 and len(np.unique(y)) >= 2:
                self.clf.fit(X, y)
                self.is_fitted = True
                return

        # Pure Python learning with standardized features and discriminative weights
        if X and y and len(X) > 0:
            n_samples = len(X)
            n_features = len(X[0])

            # 1. Compute means and standard deviations
            means = [0.0] * n_features
            for row in X:
                for j in range(n_features):
                    means[j] += row[j]
            means = [m / n_samples for m in means]

            stds = [0.0] * n_features
            for row in X:
                for j in range(n_features):
                    diff = row[j] - means[j]
                    stds[j] += diff * diff
            stds = [max(1e-4, math.sqrt(s / n_samples)) for s in stds]

            self.feature_means = means
            self.feature_stds = stds

            # 2. Compute discriminative weight (difference in means between positive and negative classes)
            pos_count = sum(y)
            neg_count = n_samples - pos_count

            if pos_count > 0 and neg_count > 0:
                pos_means = [0.0] * n_features
                neg_means = [0.0] * n_features

                for i in range(n_samples):
                    target = pos_means if y[i] == 1 else neg_means
                    for j in range(n_features):
                        target[j] += (X[i][j] - means[j]) / stds[j]

                pos_means = [pm / pos_count for pm in pos_means]
                neg_means = [nm / neg_count for nm in neg_means]

                # Weight is normalized effect size (Cohen's d)
                weights = [(pos_means[j] - neg_means[j]) for j in range(n_features)]
                self.feature_weights = weights
                self.is_fitted = True

    def predict_trace(self, trace: AgentTrace) -> dict[int, float]:
        if not trace.steps:
            return {}

        if self.is_fitted and HAS_SKLEARN and self.clf is not None:
            try:
                class DummyLabels:
                    def get(self, _): return None
                X, _ = build_dataset([trace], DummyLabels(), self.embedder)
                if len(X) > 0:
                    probs = self.clf.predict_proba(X)[:, 1]
                    mx = probs.max() + 1e-9 if probs.size > 0 else 1.0
                    return {i: round(float(p / mx), 4) for i, p in enumerate(probs)}
            except Exception:
                pass

        if self.is_fitted and self.feature_weights:
            class DummyLabels:
                def get(self, _): return None
            X, _ = build_dataset([trace], DummyLabels(), self.embedder)
            raw_scores = []
            for i, row in enumerate(X):
                # Standardize and compute dot product
                score = 0.0
                for j in range(min(len(row), len(self.feature_weights))):
                    std_val = (row[j] - self.feature_means[j]) / self.feature_stds[j] if self.feature_stds else row[j]
                    score += std_val * self.feature_weights[j]
                
                # Bonus if step explicitly has error or tool anomaly
                step = trace.steps[i]
                if step.has_error:
                    score += 5.0
                if step.latency_ms > 200:
                    score += 1.0
                raw_scores.append(score)

            # Earliest anomaly boost: if multiple steps look bad, the earliest one is usually the root cause!
            for i in range(len(raw_scores)):
                raw_scores[i] += (len(raw_scores) - i) * 0.2

            mx = max(raw_scores) if raw_scores else 1.0
            mn = min(raw_scores) if raw_scores else 0.0
            rng = max(1e-4, mx - mn)

            return {i: round(max(0.05, min(1.0, (s - mn) / rng)), 4) for i, s in enumerate(raw_scores)}

        # Heuristic scoring fallback
        return self._heuristic_scores(trace)

    def _heuristic_scores(self, trace: AgentTrace) -> dict[int, float]:
        scores: dict[int, float] = {}
        n = len(trace.steps)
        if n == 0:
            return scores

        for i, step in enumerate(trace.steps):
            score = 0.1
            if step.has_error:
                score += 0.8
            if step.latency_ms > 200:
                score += 0.2
            if step.tool:
                score += 0.15
            # Earliest root cause prior
            score += (1.0 - (i / max(1, n))) * 0.2
            scores[i] = round(min(1.0, score), 3)

        mx = max(scores.values()) if scores else 1.0
        return {i: round(s / mx, 3) for i, s in scores.items()}

    def save(self, path: Path | str) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb") as f:
            state = {
                "embedder": self.embedder,
                "clf": self.clf,
                "feature_weights": self.feature_weights,
                "feature_means": self.feature_means,
                "feature_stds": self.feature_stds,
                "is_fitted": self.is_fitted
            }
            pickle.dump(state, f)

    def load(self, path: Path | str) -> None:
        p = Path(path)
        if not p.exists():
            return
        with open(p, "rb") as f:
            state = pickle.load(f)
            self.embedder = state.get("embedder", self.embedder)
            self.clf = state.get("clf")
            self.feature_weights = state.get("feature_weights", [])
            self.feature_means = state.get("feature_means", [])
            self.feature_stds = state.get("feature_stds", [])
            self.is_fitted = state.get("is_fitted", True)
