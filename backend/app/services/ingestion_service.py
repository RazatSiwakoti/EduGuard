"""
Ingestion-domain service functions: resolving/creating Students and
Enrollments, validating raw scores against Criteria bounds, and building
AssessmentEvent rows for both bulk uploads and manual entry.

Like unit_service.py, these functions never call db.commit() or
db.rollback() - the calling route owns the transaction boundary.
db.flush() is used where a generated id (student.id, batch.id) is needed
before the transaction commits - flush is not a commit, it's safe here.

Core invariants enforced here:
- AssessmentEvent is INSERT-only. Nothing in this file ever UPDATEs an
  existing AssessmentEvent row - a correction is just a new row.
- Student demographic fields (name/email/program) are never overwritten
  by ingestion, even if the upload disagrees with what's on file - a
  mismatch is reported as a warning only.
- Disabled Criteria still accept and store data - "enabled" is an
  analysis-time filter for Phase 5, not an ingestion-time gate.
"""

from typing import Optional
from sqlalchemy.orm import Session

from app.models.student import Student
from app.models.enrollment import Enrollment
from app.models.criteria import Criteria
from app.models.assessment_event import AssessmentEvent
from app.models.ingestion_batch import IngestionBatch
from app.models.enums import EventSource


def resolve_or_create_student(
    db: Session, student_number: str, name: Optional[str],
    email: Optional[str] = None, program: Optional[str] = None,
) -> tuple[Student, Optional[str]]:
    """
    Matches by student_number - the only reliable identifier across
    uploads. If found, existing name/email/program are NEVER overwritten;
    a mismatch just produces a warning string for the caller to report.
    If not found, a new Student is created - name is required in this
    case since Student.name is NOT NULL at the DB level.
    """
    student = db.query(Student).filter(Student.student_number == student_number).first()

    if student:
        mismatches = []
        if name and student.name != name:
            mismatches.append(f"name ('{student.name}' on file vs '{name}' uploaded)")
        if email and student.email and student.email != email:
            mismatches.append(f"email ('{student.email}' on file vs '{email}' uploaded)")
        if program and student.program and student.program != program:
            mismatches.append(f"program ('{student.program}' on file vs '{program}' uploaded)")

        warning = None
        if mismatches:
            warning = (
                f"Student {student_number} details differ from upload: "
                f"{', '.join(mismatches)} - record was NOT updated."
            )
        return student, warning

    if not name:
        raise ValueError(f"Cannot create new student '{student_number}': name is required")

    student = Student(student_number=student_number, name=name, email=email, program=program)
    db.add(student)
    db.flush()  # need student.id for enrollment/event creation below
    return student, None


def resolve_or_create_enrollment(db: Session, student_id: int, unit_id: int) -> Enrollment:
    """Auto-creates an Enrollment the first time a student's data appears
    for a unit - a lecturer never has to pre-register enrollment manually."""
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.student_id == student_id, Enrollment.unit_id == unit_id)
        .first()
    )
    if enrollment:
        return enrollment

    enrollment = Enrollment(student_id=student_id, unit_id=unit_id)
    db.add(enrollment)
    db.flush()
    return enrollment


def get_unit_criteria_map(db: Session, unit_id: int, criteria_ids) -> dict[int, Criteria]:
    """
    Fetches Criteria belonging to this unit, restricted to the requested
    ids. A criteria_id that doesn't belong to this unit is a mapping
    config error, not a per-row data error - it fails the whole request
    up front rather than silently skipping or attaching to the wrong unit.
    """
    criteria_ids = list(criteria_ids)
    found = db.query(Criteria).filter(
        Criteria.unit_id == unit_id, Criteria.id.in_(criteria_ids)
    ).all()

    found_ids = {c.id for c in found}
    missing = set(criteria_ids) - found_ids
    if missing:
        raise ValueError(f"Criteria ID(s) {missing} do not belong to unit {unit_id}")

    return {c.id: c for c in found}


def validate_score(criteria: Criteria, score: float) -> Optional[str]:
    """Range check only - Phase 4's entire job for this function is
    answering 'is this a structurally valid number for this criterion'."""
    if score < 0 or score > criteria.max_score:
        return f"Score {score} out of range for '{criteria.name}' (valid range 0-{criteria.max_score})"
    return None


def build_assessment_event(
    student: Student, unit_id: int, criteria: Criteria, score: float,
    source: EventSource, created_by: int, batch_id: Optional[int] = None,
) -> AssessmentEvent:
    """Stages one immutable raw data point. Never call this to 'fix' an
    existing row - always creates a new one."""
    return AssessmentEvent(
        student_id=student.id,
        unit_id=unit_id,
        criteria_id=criteria.id,
        score=score,
        source=source,
        created_by=created_by,
        batch_id=batch_id,
    )


def process_bulk_upload(
    db: Session, unit_id: int, lecturer_id: int, filename: str, rows: list[dict],
    student_number_col: str, name_col: str,
    email_col: Optional[str], program_col: Optional[str],
    criteria_column_map: dict[int, str],
) -> tuple[IngestionBatch, list[dict], list[dict]]:
    """
    rows: one dict per CSV/Excel row, keyed by the file's original column
    headers (e.g. {"StudentID": "S1001", "Quiz1": "18", ...}).
    criteria_column_map: {criteria_id: column_name}.

    Validation is per-cell, not per-row: if a row has 3 criteria columns
    and only 1 is invalid, the other 2 are still stored - "accept valid
    rows, report invalid ones" is applied at the finest useful grain
    rather than discarding a whole row over one bad cell.
    """
    criteria_lookup = get_unit_criteria_map(db, unit_id, criteria_column_map.keys())

    batch = IngestionBatch(
        unit_id=unit_id, lecturer_id=lecturer_id, filename=filename, total_rows=len(rows)
    )
    db.add(batch)
    db.flush()  # need batch.id to attach to events below

    errors: list[dict] = []
    warnings: list[dict] = []
    success_count = 0

    for row_number, row in enumerate(rows, start=1):
        student_number = row.get(student_number_col)
        name = row.get(name_col)
        email = row.get(email_col) if email_col else None
        program = row.get(program_col) if program_col else None

        if not student_number:
            errors.append({"row": row_number, "reason": "Missing student_number - row skipped"})
            continue

        try:
            student, warning = resolve_or_create_student(db, student_number, name, email, program)
        except ValueError as e:
            errors.append({"row": row_number, "student_number": student_number, "reason": str(e)})
            continue

        if warning:
            warnings.append({"row": row_number, "student_number": student_number, "message": warning})

        resolve_or_create_enrollment(db, student.id, unit_id)

        for criteria_id, column_name in criteria_column_map.items():
            raw_value = row.get(column_name)
            if raw_value in (None, ""):
                continue  # no value submitted for this criterion in this row - not an error

            criteria = criteria_lookup[criteria_id]

            try:
                score = float(raw_value)
            except (TypeError, ValueError):
                errors.append({
                    "row": row_number, "student_number": student_number,
                    "criteria": criteria.name, "reason": f"'{raw_value}' is not a valid number",
                })
                continue

            range_error = validate_score(criteria, score)
            if range_error:
                errors.append({
                    "row": row_number, "student_number": student_number,
                    "criteria": criteria.name, "reason": range_error,
                })
                continue

            event = build_assessment_event(
                student, unit_id, criteria, score, EventSource.BULK_UPLOAD, lecturer_id, batch.id
            )
            db.add(event)
            success_count += 1

    batch.values_stored = success_count
    batch.values_failed = len(errors)

    return batch, errors, warnings


def process_manual_entry(
    db: Session, unit_id: int, lecturer_id: int, student_number: str,
    name: Optional[str], email: Optional[str], program: Optional[str],
    scores: dict[int, float],
) -> tuple[list[AssessmentEvent], list[dict], list[dict]]:
    """Same validation path as bulk upload, minus the IngestionBatch -
    there's no file to group a single manual entry under, so batch_id
    stays None on these events."""
    criteria_lookup = get_unit_criteria_map(db, unit_id, scores.keys())

    errors: list[dict] = []
    warnings: list[dict] = []

    try:
        student, warning = resolve_or_create_student(db, student_number, name, email, program)
    except ValueError as e:
        return [], [{"reason": str(e)}], []

    if warning:
        warnings.append({"student_number": student_number, "message": warning})

    resolve_or_create_enrollment(db, student.id, unit_id)

    created_events: list[AssessmentEvent] = []
    for criteria_id, score in scores.items():
        criteria = criteria_lookup[criteria_id]
        range_error = validate_score(criteria, score)
        if range_error:
            errors.append({"student_number": student_number, "criteria": criteria.name, "reason": range_error})
            continue

        event = build_assessment_event(
            student, unit_id, criteria, score, EventSource.MANUAL, lecturer_id, None
        )
        db.add(event)
        created_events.append(event)

    return created_events, errors, warnings