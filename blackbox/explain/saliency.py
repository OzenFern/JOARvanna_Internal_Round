"""
blackbox/explain/saliency.py
────────────────────────────
Identifies important features.
"""
from __future__ import annotations
import numpy as np

def compute_saliency(features: np.ndarray, clf) -> list[tuple[str, float]]:
    """Placeholder for SHAP or feature importance."""
    # Since we use scikit-learn GradientBoosting, we can use feature_importances_
    # But for a specific step's prediction, it's more complex.
    # Just returning global importances for now.
    names = [f"f_{i}" for i in range(features.shape[1])]
    try:
        imps = clf.feature_importances_
        return sorted(zip(names, imps), key=lambda x: x[1], reverse=True)[:5]
    except Exception:
        return []
