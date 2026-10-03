"""
blackbox/features/embeddings.py
────────────────────────────────
Creates semantic embeddings for textual portions of the trace.
Supports Scikit-Learn TF-IDF when available, with pure Python n-gram bag-of-words fallback.
"""
from __future__ import annotations

import json
import math
from typing import Any
from blackbox.capture.schema import AgentTrace

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    import numpy as np
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    np = None


class TraceEmbedder:
    def __init__(self, max_features: int = 128):
        self.max_features = max_features
        self.is_fitted = False
        self.vocab: dict[str, int] = {}
        if HAS_SKLEARN:
            self.vectorizer = TfidfVectorizer(max_features=max_features, stop_words="english")
        else:
            self.vectorizer = None

    def _step_to_text(self, step) -> str:
        return f"{step.tool or step.step_type} {step.name} {json.dumps(step.inputs)[:200]} {str(step.output)[:200]}"

    def fit(self, traces: list[AgentTrace]) -> None:
        texts = []
        for t in traces:
            for s in t.steps:
                texts.append(self._step_to_text(s))
        if not texts:
            texts = ["empty"]

        if HAS_SKLEARN:
            self.vectorizer.fit(texts)
        else:
            # Simple pure Python frequency vocabulary
            word_counts: dict[str, int] = {}
            for txt in texts:
                for w in txt.lower().split():
                    if len(w) > 2:
                        word_counts[w] = word_counts.get(w, 0) + 1
            sorted_words = sorted(word_counts.keys(), key=lambda w: word_counts[w], reverse=True)
            self.vocab = {w: i for i, w in enumerate(sorted_words[:self.max_features])}

        self.is_fitted = True

    def transform_trace(self, trace: AgentTrace) -> list[list[float]] | Any:
        texts = [self._step_to_text(s) for s in trace.steps]
        if HAS_SKLEARN and self.vectorizer is not None:
            return self.vectorizer.transform(texts).toarray()

        # Pure Python fallback
        vectors = []
        dim = max(1, len(self.vocab))
        for txt in texts:
            vec = [0.0] * dim
            words = txt.lower().split()
            for w in words:
                if w in self.vocab:
                    vec[self.vocab[w]] += 1.0
            # Normalize vector
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            vectors.append([round(v / norm, 4) for v in vec])
        return vectors
