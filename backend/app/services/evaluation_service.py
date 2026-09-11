"""Outcome-grounded model evaluation.

All joins deliberately exclude NULL outcomes at SQL level.  Metrics are
suppressed below 30 resolved enrolments: small samples make apparently
perfect precision/recall misleading.  Always display the base rate beside
metrics; accuracy alone is especially deceptive when failures are rare.
Withdrawal is an actual positive because leaving in week nine is precisely
the event an early-warning system should catch.
"""
from collections import defaultdict
from sqlalchemy.orm import Session, aliased
from app.models.enrollment import Enrollment
from app.models.final_verdicts import FinalVerdict
from app.models.risk_score import RiskScore
from app.models.unit import Unit

POSITIVE_TIERS = {"high_risk", "low_risk"}
POSITIVE_OUTCOMES = {"failed", "withdrawn"}
MIN_N = 30


def _rows(db: Session, unit_ids, checkpoint_week):
    ids = list(unit_ids)
    rule_score = aliased(RiskScore)
    ml_score = aliased(RiskScore)
    q = (
        db.query(Enrollment, FinalVerdict, rule_score, ml_score)
        .join(FinalVerdict, (FinalVerdict.student_id == Enrollment.student_id) &
              (FinalVerdict.unit_id == Enrollment.unit_id))
        .join(rule_score, rule_score.id == FinalVerdict.rule_score_id)
        .join(ml_score, ml_score.id == FinalVerdict.ml_score_id)
        .filter(Enrollment.final_outcome.isnot(None),
                FinalVerdict.checkpoint_week == checkpoint_week)
    )
    if ids:
        q = q.filter(Enrollment.unit_id.in_(ids))
    return q.all()


def coverage(db: Session, unit_ids):
    q = db.query(Enrollment).filter(Enrollment.final_outcome.isnot(None))
    total = db.query(Enrollment)
    ids = list(unit_ids)
    if ids:
        q, total = q.filter(Enrollment.unit_id.in_(ids)), total.filter(Enrollment.unit_id.in_(ids))
    all_count = total.count()
    resolved = q.count()
    return {"resolved": resolved, "total": all_count,
            "percentage": resolved / all_count if all_count else 0.0}


def _counts(rows, tier_getter):
    tp = fp = tn = fn = 0
    grid = {tier: {outcome: 0 for outcome in ("passed", "failed", "withdrawn")}
            for tier in ("safe", "low_risk", "high_risk")}
    for enrollment, verdict, rule, ml in rows:
        tier = tier_getter(verdict, rule, ml)
        outcome = enrollment.final_outcome
        predicted = tier in POSITIVE_TIERS
        actual = outcome in POSITIVE_OUTCOMES
        if predicted and actual: tp += 1
        elif predicted: fp += 1
        elif actual: fn += 1
        else: tn += 1
        if tier in grid and outcome in grid[tier]:
            grid[tier][outcome] += 1
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn, "tier_vs_outcome": grid}


def confusion_matrix(db: Session, unit_ids, checkpoint_week=8):
    return _counts(_rows(db, unit_ids, checkpoint_week),
                   lambda verdict, rule, ml: verdict.final_tier or "safe")


def _metric_dict(counts):
    n = counts["tp"] + counts["fp"] + counts["tn"] + counts["fn"]
    base_rate = (counts["tp"] + counts["fn"]) / n if n else 0.0
    if n < MIN_N:
        return {"suppressed": True, "reason": f"Only {n} resolved enrolments; at least {MIN_N} are required.", "base_rate": base_rate, "n": n}
    tp, fp, tn, fn = (counts[k] for k in ("tp", "fp", "tn", "fn"))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    accuracy = (tp + tn) / n
    return {"suppressed": False, "n": n, "base_rate": base_rate,
            "precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
            "specificity": specificity, "accuracy": accuracy}


def metrics(db: Session, unit_ids, checkpoint_week=8):
    return _metric_dict(confusion_matrix(db, unit_ids, checkpoint_week))


def per_engine_metrics(db: Session, unit_ids, checkpoint_week=8):
    rows = _rows(db, unit_ids, checkpoint_week)
    getters = {
        "rule": lambda v, r, m: r.risk_level,
        "ml": lambda v, r, m: m.risk_level,
        "hybrid": lambda v, r, m: v.final_tier or "safe",
    }
    return {name: _metric_dict(_counts(rows, getter)) for name, getter in getters.items()}


def lead_time(db: Session, unit_ids, checkpoint_week=8):
    """Return warning weeks for true positives; trimester end is week 12."""
    rows = _rows(db, unit_ids, checkpoint_week)
    return [12 - checkpoint_week for e, v, r, m in rows
            if e.final_outcome in POSITIVE_OUTCOMES and (v.final_tier in POSITIVE_TIERS)]


def calibration(db: Session, unit_ids, checkpoint_week=8):
    """Probability calibration is unavailable until probabilities are persisted."""
    return []
