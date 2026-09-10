"""Retention and right-to-erasure operations.

Audit rows are intentionally not deleted: they contain the minimum
accountability record without retaining the erased student's data.
"""
from calendar import monthrange
from datetime import date

from sqlalchemy.orm import Session

from app.models.assessment_event import AssessmentEvent
from app.models.email_message import EmailMessage
from app.models.enrollment import Enrollment
from app.models.final_verdicts import FinalVerdict
from app.models.risk_score import RiskScore
from app.models.student import Student
from app.models.student_note import StudentNote
from app.models.verdict_review import VerdictReview
from app.models.unit import Unit


def _add_months(value: date, months: int) -> date:
    month = value.month - 1 + months
    year, month = value.year + month // 12, month % 12 + 1
    return value.replace(year=year, month=month, day=min(value.day, monthrange(year, month)[1]))


def find_expired(db: Session) -> list[Enrollment]:
    rows = (
        db.query(Enrollment)
        .join(Unit, Enrollment.unit_id == Unit.id)
        .filter(Unit.start_date.isnot(None))
        .all()
    )
    today = date.today()
    return [row for row in rows if _add_months(row.unit.start_date, row.unit.retention_months) <= today]


def purge_enrolment(db: Session, enrollment_id: int) -> dict:
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if enrollment is None:
        return {"enrollment_id": enrollment_id, "student_id": None, "deleted": False}
    student_id, unit_id = enrollment.student_id, enrollment.unit_id
    for model in (AssessmentEvent, RiskScore, FinalVerdict, VerdictReview, StudentNote):
        db.query(model).filter(model.student_id == student_id, model.unit_id == unit_id).delete(
            synchronize_session=False
        )
    db.query(EmailMessage).filter(
        EmailMessage.student_id == student_id, EmailMessage.unit_id == unit_id
    ).update({EmailMessage.body: "[content purged under retention policy]"}, synchronize_session=False)
    db.delete(enrollment)
    db.flush()
    if db.query(Enrollment).filter(Enrollment.student_id == student_id).count() == 0:
        for model in (AssessmentEvent, RiskScore, FinalVerdict, VerdictReview, StudentNote):
            db.query(model).filter(model.student_id == student_id).delete(synchronize_session=False)
        db.query(EmailMessage).filter(EmailMessage.student_id == student_id).update(
            {EmailMessage.body: "[content purged under erasure request]"}, synchronize_session=False
        )
        db.delete(db.query(Student).filter(Student.id == student_id).one())
    return {"enrollment_id": enrollment_id, "student_id": student_id, "unit_id": unit_id, "deleted": True}
