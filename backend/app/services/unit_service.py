"""
Unit-domain service functions: lecturer assignment lifecycle and the
archive-vs-delete decision for Units.

These functions never call db.commit() or db.rollback() - the calling
route owns the transaction boundary. Every function here only stages
changes; the route decides when those changes actually become permanent.
"""

from sqlalchemy.orm import Session

from app.models.unit import Unit
from app.models.criteria import Criteria
from app.models.rule_version import RuleVersion
from app.models.enrollment import Enrollment
from app.models.assessment_event import AssessmentEvent
from app.models.risk_score import RiskScore


def assign_lecturer(db: Session, unit: Unit, lecturer_id: int) -> None:
    """Overwrites directly - no unassign-first step required."""
    unit.lecturer_id = lecturer_id
    unit.status = "ASSIGNED"


def unassign_lecturer(db: Session, unit: Unit) -> None:
    """lecturer_id and status are always changed together here, so they
    can never disagree with each other."""
    unit.lecturer_id = None
    unit.status = "UNASSIGNED"


def delete_or_archive_unit(db: Session, unit: Unit) -> str:
    """
    Returns "deleted" or "archived" so the route can report which
    happened. A unit with real academic data attached gets archived
    (is_active = False) instead of destroyed; an empty unit is
    hard-deleted along with its Criteria/RuleVersions (pure
    configuration, no student data, safe to remove together).
    """
    has_real_data = (
        db.query(Enrollment).filter(Enrollment.unit_id == unit.id).first() is not None
        or db.query(AssessmentEvent).filter(AssessmentEvent.unit_id == unit.id).first() is not None
        or db.query(RiskScore).filter(RiskScore.unit_id == unit.id).first() is not None
    )

    if has_real_data:
        unit.is_active = False
        return "archived"

    db.query(Criteria).filter(Criteria.unit_id == unit.id).delete()
    db.query(RuleVersion).filter(RuleVersion.unit_id == unit.id).delete()
    db.delete(unit)
    return "deleted"