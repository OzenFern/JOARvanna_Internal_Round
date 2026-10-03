"""
blackbox/features/embeddings.py
────────────────────────────────
Creates semantic embeddings for textual portions of the trace.
For simplicity and speed without a GPU, we use a basic TF-IDF
approach here instead of a heavy Transformer model.
"""
from __future__ import annotations

import json
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
from blackbox.capture.schema import AgentTrace

class TraceEmbedder:
    def __init__(self, max_features: int = 128):
        self.vectorizer = TfidfVectorizer(max_features=max_features, stop_words="english")
        self.is_fitted = False
        
    def _step_to_text(self, step) -> str:
        return f"{step.tool or step.step_type} {step.name} {json.dumps(step.inputs)[:200]} {str(step.output)[:200]}"
        
    def fit(self, traces: list[AgentTrace]) -> None:
        texts = []
        for t in traces:
            for s in t.steps:
                texts.append(self._step_to_text(s))
        if not texts:
            texts = ["empty"]
        self.vectorizer.fit(texts)
        self.is_fitted = True
        
    def transform_trace(self, trace: AgentTrace) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Embedder not fitted")
        texts = [self._step_to_text(s) for s in trace.steps]
        return self.vectorizer.transform(texts).toarray()
