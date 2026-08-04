"""
ML Risk Engine - Phase 5.2

Loads the three trained artifacts (feature column order, label encoder,
XGBoost model) ONCE at import time, exposes predict_risk() for turning
one student's raw feature dict into a risk tier + probabilities, and
explain_prediction()/build_ml_explanation() for SHAP-based reasoning
behind that prediction.

Feature order is critical: XGBoost was trained on features in the exact
order stored in edguard_feature_columns.joblib. Passing them in any
other order would silently produce wrong predictions - this module
always builds the feature vector in that exact confirmed order:
['moodle_login_count', 'attendance_pct', 'attendance_trend',
 'tut_completion_pct', 'tut_trend', 'assessment_avg_pct']

Label encoder classes, confirmed: ['high_risk', 'low_risk', 'safe']
(alphabetical, NOT the natural safe->low->high order) - predictions are
always decoded via encoder.inverse_transform(), never assumed by index
position, so this ordering quirk can never cause a silent mislabel.

SHAP note: TreeExplainer on this multiclass XGBoost model returns shape
(n_samples, n_features, n_classes) - confirmed empirically, not assumed.
The class axis order matches the model's own class order, so the
predicted label's SHAP values are looked up via the SAME label encoder,
never a hardcoded index.
"""

import joblib
import pandas as pd
import shap
from dataclasses import dataclass
from pathlib import Path

ARTIFACT_DIR = Path(__file__).resolve().parent.parent / "ml" / "artifacts"

_feature_columns = joblib.load(ARTIFACT_DIR / "edguard_feature_columns.joblib")
_label_encoder = joblib.load(ARTIFACT_DIR / "edguard_label_encoder.joblib")
_model = joblib.load(ARTIFACT_DIR / "edguard_risk_model.joblib")
_explainer = shap.TreeExplainer(_model)

# Human-readable labels for each feature, used in explanations shown to lecturers.
FEATURE_LABELS = {
    "moodle_login_count": "Moodle activity",
    "attendance_pct": "attendance",
    "attendance_trend": "attendance trend",
    "tut_completion_pct": "tutorial completion",
    "tut_trend": "tutorial completion trend",
    "assessment_avg_pct": "assessment average",
}


@dataclass
class MLEngineResult:
    tier: str
    probabilities: dict[str, float]


def _build_feature_row(features: dict) -> pd.DataFrame:
    """Shared helper: reorders + casts a feature dict to match training,
    always as float (never object dtype - see predict_risk docstring)."""
    row = {}
    for col in _feature_columns:
        value = features.get(col, None)
        row[col] = float(value) if value is not None else float("nan")
    return pd.DataFrame([row], columns=_feature_columns).astype(float)


def predict_risk(features: dict) -> MLEngineResult:
    """
    features: dict keyed by feature name (any order - reordered here to
    match training). Missing keys or None values become NaN.
    """
    df = _build_feature_row(features)

    predicted_index = _model.predict(df)[0]
    predicted_label = _label_encoder.inverse_transform([predicted_index])[0]

    proba = _model.predict_proba(df)[0]
    probabilities = {cls: float(p) for cls, p in zip(_label_encoder.classes_, proba)}

    return MLEngineResult(tier=predicted_label, probabilities=probabilities)


def explain_prediction(features: dict, predicted_label: str, top_n: int = 3) -> list[dict]:
    """
    Returns the top_n features (by absolute SHAP value) driving the
    prediction toward predicted_label specifically - not just overall
    importance, but importance FOR THIS class on THIS student.
    """
    df = _build_feature_row(features)

    class_index = list(_label_encoder.classes_).index(predicted_label)
    shap_values = _explainer.shap_values(df)  # shape: (1, n_features, n_classes)
    feature_shap = shap_values[0, :, class_index]

    contributions = [
        {"feature": col, "value": df[col].iloc[0], "shap_value": float(feature_shap[i])}
        for i, col in enumerate(_feature_columns)
    ]
    contributions.sort(key=lambda c: abs(c["shap_value"]), reverse=True)
    return contributions[:top_n]


def describe_contribution(contrib: dict) -> str:
    """Turns one SHAP contribution into a plain-language phrase."""
    label = FEATURE_LABELS.get(contrib["feature"], contrib["feature"])
    value = contrib["value"]
    value_str = "no data" if value != value else f"{value:.1f}"  # value != value checks NaN
    direction = "increasing" if contrib["shap_value"] > 0 else "decreasing"
    return f"{label} ({value_str}) - {direction} likelihood"


def build_ml_explanation(features: dict, predicted_label: str, top_n: int = 3) -> str:
    """Full plain-language explanation string for storage on RiskScore.explanation."""
    contributions = explain_prediction(features, predicted_label, top_n)
    if not contributions:
        return "ML model: no significant contributing factors identified."
    parts = [describe_contribution(c) for c in contributions]
    return "ML model (SHAP): " + "; ".join(parts) + "."