from pathlib import Path

import joblib
import pandas as pd

MODEL_PATH = Path(__file__).with_name("student_risk_model.joblib")

artifacts = joblib.load(MODEL_PATH)

model = artifacts["model"]
feature_names = artifacts["feature_names"]
label_encoder = artifacts["label_encoder"]

print("Features:", feature_names)
print("Classes:", list(label_encoder.classes_))

import pandas as pd

sample_values = {
    "moodle_login_count": 12,
    "attendance_pct": 72.0,
    "attendance_trend": -5.0,
    "tut_completion_pct": 80.0,
    "tut_trend": 0.0,
    "assessment_avg_pct": 68.0,
}

sample = pd.DataFrame([sample_values]).reindex(
    columns=feature_names
)

prediction_encoded = model.predict(sample)
probabilities = model.predict_proba(sample)

prediction_label = label_encoder.inverse_transform(
    prediction_encoded.astype(int)
)

print("Prediction:", prediction_label[0])
print("Probabilities:", probabilities[0])