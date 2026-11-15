"""Model selection utilities based on validation performance."""
import numpy as np


def select_best(results: dict, metric: str = "roc_auc") -> str:
    """Select the best model name based on validation metric.
    
    Never uses test set metrics for selection.
    """
    return max(
        results,
        key=lambda name: (
            results[name]["validation"].get(metric, float("-inf"))
            if np.isfinite(results[name]["validation"].get(metric, float("-inf")))
            else -1
        ),
    )
