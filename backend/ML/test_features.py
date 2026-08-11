from ML.feature_builder import build_student_features



features = build_student_features(
    student_id=5,
    subject_code="BSYS301",
)

print("Generated ML features:")
print(features)