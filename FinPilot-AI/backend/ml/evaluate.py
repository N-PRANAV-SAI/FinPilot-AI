"""Model evaluation metrics."""
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)


def evaluate_model(model, X, y) -> dict:
    """Evaluate a classifier and return a metrics dictionary.
    
    Includes accuracy, precision, recall, f1, roc_auc, and confusion_matrix.
    """
    pred = model.predict(X)
    prob = model.predict_proba(X)[:, 1] if hasattr(model, "predict_proba") else pred.astype(float)

    try:
        auc = float(roc_auc_score(y, prob))
    except Exception:
        auc = float("nan")

    cm = confusion_matrix(y, pred)

    return {
        "accuracy": float(accuracy_score(y, pred)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "roc_auc": auc,
        "confusion_matrix": cm.tolist(),
    }
