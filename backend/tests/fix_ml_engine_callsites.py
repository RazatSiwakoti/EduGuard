"""
Rewrites the ml_engine.py call sites for lazy artifact loading.

Run from the `backend/` folder AFTER you have added the ARTIFACTS dict,
MLModelUnavailable, _load_artifacts() and model_is_available():

    python3 fix_ml_engine_callsites.py

Safe to run twice - it reports "already done" rather than double-applying.

WHY A SCRIPT AND NOT FIND-AND-REPLACE. The strings "_model." and
"_label_encoder." also appear INSIDE the artifact filenames
("edguard_risk_model.joblib", "edguard_label_encoder.joblib"). A blanket
replace corrupts those and the file stops parsing. Every rule below
matches a full, unambiguous line instead.
"""

import ast
import sys
from pathlib import Path

TARGET = Path("app/services/ml_engine.py")

# (exact source fragment, replacement). Full expressions, never bare
# identifiers, so a filename string can never match.
RULES = [
    ('for col in _feature_columns:',
     'for col in _load_artifacts()["feature_columns"]:'),

    ('columns=_feature_columns)',
     'columns=_load_artifacts()["feature_columns"])'),

    ('for i, col in enumerate(_feature_columns)',
     'for i, col in enumerate(_load_artifacts()["feature_columns"])'),

    ('_model.predict(df)',
     '_load_artifacts()["model"].predict(df)'),

    ('_model.predict_proba(df)',
     '_load_artifacts()["model"].predict_proba(df)'),

    ('_label_encoder.inverse_transform(',
     '_load_artifacts()["label_encoder"].inverse_transform('),

    ('zip(_label_encoder.classes_,',
     'zip(_load_artifacts()["label_encoder"].classes_,'),

    ('list(_label_encoder.classes_)',
     'list(_load_artifacts()["label_encoder"].classes_)'),

    ('_explainer.shap_values(df)',
     '_load_artifacts()["explainer"].shap_values(df)'),
]


def main() -> int:
    if not TARGET.exists():
        print(f"ERROR: {TARGET} not found. Run this from the backend/ folder.")
        return 1

    source = TARGET.read_text()

    if "_load_artifacts" not in source:
        print("ERROR: _load_artifacts() is not in the file yet.")
        print("       Do part 1 of the guide first (ARTIFACTS, MLModelUnavailable,")
        print("       _load_artifacts, model_is_available), then run this.")
        return 1

    applied, skipped = [], []
    for old, new in RULES:
        if new in source:
            skipped.append(old)
        elif old in source:
            source = source.replace(old, new)
            applied.append(old)
        else:
            print(f"WARNING: could not find -> {old}")
            print("         Your file may differ from the guide. Apply that one by hand.")

    # Never write a file that does not parse.
    try:
        ast.parse(source)
    except SyntaxError as exc:
        print(f"ABORTED: the result would not parse (line {exc.lineno}: {exc.msg})")
        print("         Nothing was written.")
        return 1

    # The corruption check: the filenames must survive intact.
    for filename in ("edguard_risk_model.joblib",
                     "edguard_label_encoder.joblib",
                     "edguard_feature_columns.joblib"):
        if filename not in source:
            print(f"ABORTED: the artifact filename {filename} was damaged.")
            print("         Nothing was written.")
            return 1

    TARGET.write_text(source)
    print(f"Applied {len(applied)} change(s).")
    if skipped:
        print(f"{len(skipped)} were already done.")
    print("\nNow verify with:")
    print("  grep -n '_load_artifacts()\\[' app/services/ml_engine.py")
    print("  -> expect exactly 9 lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())