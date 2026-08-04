from pathlib import Path
from typing import Any

import joblib
import pandas as pd


MODEL_PATH = Path(__file__).with_name("student_risk_model.joblib")

artifacts: dict[str, Any] = joblib.load(MODEL_PATH)

model = artifacts["model"]
feature_names: list[str] = artifacts["feature_names"]
label_encoder = artifacts["label_encoder"]
model_version: str = artifacts.get("model_version", "unknown")


def predict_risk(features: dict[str, float]) -> dict:
    missing_features = [
        feature
        for feature in feature_names
        if feature not in features
    ]

    if missing_features:
        raise ValueError(
            f"Missing model features: {missing_features}"
        )

    model_input = pd.DataFrame([features]).reindex(
        columns=feature_names
    )

    prediction_encoded = model.predict(model_input)
    probabilities = model.predict_proba(model_input)[0]

    prediction_label = label_encoder.inverse_transform(
        prediction_encoded.astype(int)
    )[0]

    probability_map = {
        str(label): float(probabilities[index])
        for index, label in enumerate(label_encoder.classes_)
    }

    return {
        "prediction": str(prediction_label),
        "confidence": float(max(probabilities)),
        "probabilities": probability_map,
        "model_version": model_version,
    }