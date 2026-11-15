"""SHAP-based model explainability for financial predictions."""
import logging
import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


def explain(model, X_background: pd.DataFrame, X_row: pd.DataFrame, feature_names: list[str]) -> dict:
    """Generate SHAP feature attributions for a model's prediction.
    
    Args:
        model: Fitted scikit-learn Pipeline or estimator.
        X_background: Background historical data sample for baseline reference.
        X_row: The single feature observation row being explained.
        feature_names: List of input feature names.
        
    Returns:
        Dict with feature_names, shap_values, base_value, and sorted importances.
    """
    import shap

    if not hasattr(model, "named_steps"):
        raise ValueError("Expected an sklearn Pipeline with preprocessing steps.")

    final_estimator = model.steps[-1][1]
    transformer = model[:-1]

    # Transform features through imputer/scaler
    bg_transformed = transformer.transform(X_background)
    row_transformed = transformer.transform(X_row)

    # Get feature names matching transformed matrix dimension
    n_features = bg_transformed.shape[1]
    if n_features == len(feature_names):
        transformed_names = list(feature_names)
    else:
        # If SimpleImputer(add_indicator=True) added missing indicators
        transformed_names = list(feature_names) + [
            f"{feature_names[i % len(feature_names)]}_isna"
            for i in range(n_features - len(feature_names))
        ]
        transformed_names = transformed_names[:n_features]

    shap_values = None
    base_value = 0.5
    estimator_type = type(final_estimator).__name__

    # 1. Try TreeExplainer for tree models (RandomForest, ExtraTrees, XGBoost)
    if any(tree_name in estimator_type for tree_name in ("Forest", "Tree", "XGB", "GradientBoosting")):
        try:
            explainer = shap.TreeExplainer(final_estimator)
            raw_shap = explainer.shap_values(row_transformed)

            if isinstance(raw_shap, list):
                # Binary classification: index 1 represents positive class
                shap_values = raw_shap[1][0] if len(raw_shap) > 1 else raw_shap[0][0]
            elif isinstance(raw_shap, np.ndarray) and raw_shap.ndim == 3:
                # Shape (1, features, classes)
                shap_values = raw_shap[0, :, 1]
            elif isinstance(raw_shap, np.ndarray) and raw_shap.ndim == 2:
                shap_values = raw_shap[0]
            else:
                shap_values = np.array(raw_shap).flatten()

            expected = explainer.expected_value
            if isinstance(expected, (list, np.ndarray)):
                base_value = float(expected[1] if len(expected) > 1 else expected[0])
            else:
                base_value = float(expected)

            log.info("Computed SHAP values using TreeExplainer for %s.", estimator_type)
        except Exception as exc:
            log.warning("TreeExplainer failed (%s); trying fallback explainer.", exc)

    # 2. Try LinearExplainer for LogisticRegression
    elif "Logistic" in estimator_type or "Linear" in estimator_type:
        try:
            # Use background sample for LinearExplainer
            bg_sample = bg_transformed[:min(100, len(bg_transformed))]
            explainer = shap.LinearExplainer(final_estimator, bg_sample)
            raw_shap = explainer.shap_values(row_transformed)

            if isinstance(raw_shap, list):
                shap_values = raw_shap[1][0] if len(raw_shap) > 1 else raw_shap[0][0]
            elif isinstance(raw_shap, np.ndarray) and raw_shap.ndim == 2:
                shap_values = raw_shap[0]
            else:
                shap_values = np.array(raw_shap).flatten()

            expected = explainer.expected_value
            if isinstance(expected, (list, np.ndarray)):
                base_value = float(expected[1] if len(expected) > 1 else expected[0])
            else:
                base_value = float(expected)

            log.info("Computed SHAP values using LinearExplainer for %s.", estimator_type)
        except Exception as exc:
            log.warning("LinearExplainer failed (%s); trying KernelExplainer.", exc)

    # 3. Fallback: KernelExplainer
    if shap_values is None:
        try:
            bg_summary = shap.kmeans(bg_transformed, min(20, len(bg_transformed)))
            predict_fn = lambda x: final_estimator.predict_proba(x)[:, 1]
            explainer = shap.KernelExplainer(predict_fn, bg_summary)
            raw_shap = explainer.shap_values(row_transformed, nsamples=60)
            shap_values = raw_shap[0] if isinstance(raw_shap, list) else raw_shap.flatten()
            base_value = float(explainer.expected_value)
            log.info("Computed SHAP values using KernelExplainer fallback.")
        except Exception as exc:
            log.error("All SHAP explainers failed: %s", exc)
            raise RuntimeError(f"SHAP explanation failed: {exc}") from exc

    # Ensure 1D array of correct length
    shap_values = np.asarray(shap_values).flatten()[:len(transformed_names)]
    values_list = [float(v) for v in shap_values]

    # Sort features by absolute contribution
    importances = sorted(
        zip(transformed_names, values_list),
        key=lambda pair: abs(pair[1]),
        reverse=True,
    )

    top_positive = [{"feature": f, "contribution": v} for f, v in importances if v > 0][:7]
    top_negative = [{"feature": f, "contribution": v} for f, v in importances if v < 0][:7]

    return {
        "values": values_list,
        "feature_names": transformed_names,
        "base_value": base_value,
        "importances": [{"feature": f, "contribution": v} for f, v in importances],
        "top_positive": top_positive,
        "top_negative": top_negative,
        "estimator_type": estimator_type,
    }
