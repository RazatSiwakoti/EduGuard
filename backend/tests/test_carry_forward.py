"""
Carry-forward behaviour, exercised against a real SQLite database.

The whole point of Phase 7.7 is that a lecturer's decision survives
"Run Analysis". These assertions are that claim, made testable.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # registers every model on Base.metadata
from app.models.base import Base
from app.models.user import User
from app.models.unit import Unit
from app.models.student import Student
from app.models.risk_score import RiskScore
from app.models.final_verdicts import FinalVerdict
from app.models.verdict_review import VerdictReview
from app.services import final_verdict_service as svc

engine = create_engine("sqlite://")
Base.metadata.create_all(engine)
db = sessionmaker(bind=engine)()

lecturer = User(email="l@koi.edu.au", full_name="Dr Rana", role="lecturer",
                hashed_password="x", is_active=True)
db.add(lecturer); db.flush()
unit = Unit(unit_code="BSYS401", unit_name="Advanced Systems", lecturer_id=lecturer.id)
student = Student(student_number="KOI-2025-005", name="Aroha Ngata")
db.add_all([unit, student]); db.flush()

def stage_scores(rule_tier, ml_tier):
    """One analysis run's worth of engine output."""
    r = RiskScore(student_id=student.id, unit_id=unit.id, source="rule_based",
                  risk_score=0.4, risk_level=rule_tier, checkpoint_week=8,
                  explanation="rule")
    m = RiskScore(student_id=student.id, unit_id=unit.id, source="ml_model",
                  risk_score=0.9, risk_level=ml_tier, checkpoint_week=8,
                  explanation="ml")
    db.add_all([r, m]); db.flush()
    return r, m

failures = []
def check(label, actual, expected):
    ok = actual == expected
    print(f"  {'PASS' if ok else 'FAIL'}  {label}: {actual!r}")
    if not ok:
        failures.append(f"{label}: expected {expected!r}, got {actual!r}")

print("\n1. Engines disagree safe vs high_risk -> needs review")
stage_scores("safe", "high_risk")
v1 = svc.compute_and_stage_final_verdict(db, student.id, unit.id, 8); db.flush()
check("requires_review", v1.requires_review, True)
check("final_tier", v1.final_tier, None)

print("\n2. Lecturer resolves it as safe, with a comment")
svc.submit_review_decision(db, v1.id, lecturer.id, "safe", "Approved leave, attendance is misleading.")
db.flush()
check("requires_review", v1.requires_review, False)
check("final_tier", v1.final_tier, "safe")
check("review_id set", v1.review_id is not None, True)
review = db.query(VerdictReview).one()
check("review.rule_tier", review.rule_tier, "safe")
check("review.ml_tier", review.ml_tier, "high_risk")
check("comment stored", review.comment, "Approved leave, attendance is misleading.")

print("\n3. Run Analysis again, SAME disagreement -> decision carries forward")
stage_scores("safe", "high_risk")
v2 = svc.compute_and_stage_final_verdict(db, student.id, unit.id, 8); db.flush()
check("is a NEW verdict row", v2.id != v1.id, True)
check("requires_review", v2.requires_review, False)
check("final_tier", v2.final_tier, "safe")
check("carries the same review", v2.review_id, review.id)
check("no duplicate review row", db.query(VerdictReview).count(), 1)

print("\n4. Run Analysis again, ML MOVED (high_risk -> low_risk) -> back in the queue")
stage_scores("safe", "low_risk")
v3 = svc.compute_and_stage_final_verdict(db, student.id, unit.id, 8); db.flush()
# safe vs low_risk is auto-resolvable, so this one is not a review case at all.
check("requires_review", v3.requires_review, False)
check("review NOT applied", v3.review_id, None)
check("tier came from the engines", v3.final_tier, "low_risk")

print("\n5. A genuinely different disagreement -> NOT carried forward")
stage_scores("high_risk", "safe")
v4 = svc.compute_and_stage_final_verdict(db, student.id, unit.id, 8); db.flush()
check("requires_review", v4.requires_review, True)
check("review NOT applied", v4.review_id, None)
check("final_tier", v4.final_tier, None)

print("\n6. Lecturer changes their mind -> new row, old one preserved")
svc.submit_review_decision(db, v4.id, lecturer.id, "high_risk", None)
db.flush()
check("review rows", db.query(VerdictReview).count(), 2)
check("verdict tier", v4.final_tier, "high_risk")
latest = svc.get_latest_review(db, student.id, unit.id, 8)
check("latest is the new decision", latest.decision, "high_risk")
check("empty comment stored as NULL", latest.comment, None)
check("first decision still on record",
      db.query(VerdictReview).order_by(VerdictReview.id).first().decision, "safe")

print("\n7. Re-review the SAME verdict again (the old code raised here)")
svc.submit_review_decision(db, v4.id, lecturer.id, "low_risk", "Reconsidered.")
db.flush()
check("verdict tier updated", v4.final_tier, "low_risk")
check("review rows", db.query(VerdictReview).count(), 3)

print("\n8. Engines AGREE -> a stale human decision must not override them")
stage_scores("high_risk", "high_risk")
v5 = svc.compute_and_stage_final_verdict(db, student.id, unit.id, 8); db.flush()
check("requires_review", v5.requires_review, False)
check("no review applied", v5.review_id, None)
check("tier came from the engines", v5.final_tier, "high_risk")

print("\n" + ("ALL CHECKS PASSED" if not failures else f"{len(failures)} FAILURE(S)"))
for f in failures:
    print("  !", f)
sys.exit(1 if failures else 0)