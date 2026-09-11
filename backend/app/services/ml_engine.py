"""
ML Risk Engine - Phase 5.2

Loads the three trained artifacts (feature column order, label encoder,
XGBoost model) once, ON FIRST USE - not at import time. Exposes
predict_risk() for turning one student's raw feature dict into a risk
tier + probabilities, and explain_prediction()/build_ml_explanation()
for SHAP-based reasoning behind that prediction.

The artifacts are excluded from the repository by .gitignore, so on a
machine that does not have them this module still imports and the rest
of the API still runs - only prediction raises MLModelUnavailable. It
used to load at import, which meant one missing file stopped the whole
application from starting.

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

ARTIFACTS = {
    "feature_columns": "edguard_feature_columns.joblib",
    "label_encoder": "edguard_label_encoder.joblib",
    "model": "edguard_risk_model.joblib",
}


class MLModelUnavailable(RuntimeError):
    """
    The trained model is not installed on this machine.

    A distinct exception type so callers can tell "the model is missing"
    from "the model ran and something went wrong". They are different
    problems with different fixes, and collapsing them into one generic
    failure is how a lecturer gets told "analysis failed" when the real
    answer is "nobody copied the .joblib files onto the server".
    """


#: Loaded once, on FIRST USE rather than at import.
#:
#: WHY LAZY. These three files are excluded from the repository by
#: `.gitignore` (`*.joblib`), so a fresh clone does not have them. Loading
#: at import time meant `main.py` -> risk router -> ml_score_service ->
#: this module -> FileNotFoundError, and the ENTIRE API failed to boot -
#: login, dashboards, reports, everything - because one optional artifact
#: was missing.
#:
#: Deferring the load turns that into a single feature reporting itself
#: unavailable, which is the honest failure and the recoverable one.
_artifacts: dict | None = None


def _load_artifacts() -> dict:
    global _artifacts
    if _artifacts is not None:
        return _artifacts

    missing = [
        name for name in ARTIFACTS.values()
        if not (ARTIFACT_DIR / name).exists()
    ]
    if missing:
        raise MLModelUnavailable(
            "The trained risk model is not installed on this server. "
            f"Missing from {ARTIFACT_DIR}: {', '.join(missing)}. "
            "The rule engine still works; hybrid verdicts need the model."
        )

    try:
        model = joblib.load(ARTIFACT_DIR / ARTIFACTS["model"])
        loaded = {
            "feature_columns": joblib.load(
                ARTIFACT_DIR / ARTIFACTS["feature_columns"]
            ),
            "label_encoder": joblib.load(
                ARTIFACT_DIR / ARTIFACTS["label_encoder"]
            ),
            "model": model,
            # Building the explainer is the slow part, so it is built
            # once here alongside the model rather than per prediction.
            "explainer": shap.TreeExplainer(model),
        }
    except MLModelUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001 - re-typed deliberately
        # A corrupt or version-mismatched artifact is still "the model
        # is not usable here", not a bug in the caller.
        raise MLModelUnavailable(
            f"The risk model could not be loaded: {exc}"
        ) from exc

    _artifacts = loaded
    return _artifacts


def model_is_available() -> bool:
    """True when a prediction would work. Used by the API to report the
    feature as unavailable instead of failing mid-run."""
    try:
        _load_artifacts()
        return True
    except MLModelUnavailable:
        return False

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
    for col in _load_artifacts()["feature_columns"]:
        value = features.get(col, None)
        row[col] = float(value) if value is not None else float("nan")
    return pd.DataFrame([row], columns=_load_artifacts()["feature_columns"]).astype(float)


def predict_risk(features: dict) -> MLEngineResult:
    """
    features: dict keyed by feature name (any order - reordered here to
    match training). Missing keys or None values become NaN.
    """
    df = _build_feature_row(features)

    predicted_index = _load_artifacts()["model"].predict(df)[0]
    predicted_label = _load_artifacts()["label_encoder"].inverse_transform([predicted_index])[0]

    proba = _load_artifacts()["model"].predict_proba(df)[0]
    probabilities = {cls: float(p) for cls, p in zip(_load_artifacts()["label_encoder"].classes_, proba)}

    return MLEngineResult(tier=predicted_label, probabilities=probabilities)


def explain_prediction(features: dict, predicted_label: str, top_n: int = 3) -> list[dict]:
    """
    Returns the top_n features (by absolute SHAP value) driving the
    prediction toward predicted_label specifically - not just overall
    importance, but importance FOR THIS class on THIS student.
    """
    df = _build_feature_row(features)

    class_index = list(_load_artifacts()["label_encoder"].classes_).index(predicted_label)
    shap_values = _load_artifacts()["explainer"].shap_values(df)  # shape: (1, n_features, n_classes)
    feature_shap = shap_values[0, :, class_index]

    contributions = [
        {"feature": col, "value": df[col].iloc[0], "shap_value": float(feature_shap[i])}
        for i, col in enumerate(_load_artifacts()["feature_columns"])
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