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
- Weekly Attendance/Tutorial cells are aggregated into ONE percentage
  AND one trend value before storage - raw weekly values are never
  persisted separately. The trend value mirrors the ML training
  notebook's formula exactly, since the ML model needs it as a feature
  and there would otherwise be nowhere to reconstruct it from later.
  A blank/unrecognised weekly cell counts as absent/not_submitted (0
  credit for that week), consistent with the project-wide rule that
  unsubmitted work is always a real 0, never silently skipped.
"""

from typing import Optional
from sqlalchemy.orm import Session

from app.models.student import Student
from app.models.enrollment import Enrollment
from app.models.criteria import Criteria
from app.models.assessment_event import AssessmentEvent
from app.models.ingestion_batch import IngestionBatch
from app.models.enums import EventSource, CriteriaCategory

from app.services.rule_engine import (
    calculate_attendance_pct,
    calculate_attendance_trend,
    calculate_tutorial_completion_pct,
    calculate_tutorial_completion_trend,
)


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
    trend_value: Optional[float] = None,
) -> AssessmentEvent:
    """Stages one immutable raw data point. Never call this to 'fix' an
    existing row - always creates a new one. trend_value is only ever
    set for Attendance/Weekly Tut events; None for everything else."""
    return AssessmentEvent(
        student_id=student.id,
        unit_id=unit_id,
        criteria_id=criteria.id,
        score=score,
        trend_value=trend_value,
        source=source,
        created_by=created_by,
        batch_id=batch_id,
    )


# ---------------------------------------------------------------------------
# Weekly cell parsing (Attendance / Weekly Tut only)
# ---------------------------------------------------------------------------

def parse_attendance_cell(raw_value) -> bool:
    """
    Normalises one week's raw attendance cell into True (attended) or
    False (absent). A blank/unrecognised cell is treated as absent,
    consistent with the project-wide rule: unmarked = 0, never silently
    excluded (structural absence is handled at the Criteria level, not
    per-cell).
    """
    if raw_value is None:
        return False
    text = str(raw_value).strip().lower()
    return text in ("1", "true", "yes", "y", "present")


def parse_tutorial_cell(raw_value) -> str:
    """
    Normalises one week's raw tutorial cell into a status string matching
    TUTORIAL_STATUS_CREDIT's keys. A blank/unrecognised cell is treated
    as not_submitted (0 credit) - same reasoning as parse_attendance_cell.
    """
    if raw_value is None:
        return "not_submitted"
    text = str(raw_value).strip().lower()
    if text in ("submitted", "yes", "y", "1"):
        return "submitted"
    if text == "late":
        return "late"
    return "not_submitted"


def build_weekly_criterion_event(
    student: Student, unit_id: int, criteria: Criteria,
    weekly_raw_values: list, source: EventSource, created_by: int,
    batch_id: Optional[int] = None,
) -> AssessmentEvent:
    """
    Aggregates a student's raw weekly cells (Attendance or Weekly Tut)
    into ONE completion percentage AND one trend value, using the exact
    same functions the rule engine and ML training notebook use, then
    stages both on one AssessmentEvent row. Raw weekly values are NOT
    persisted separately - only score and trend_value.

    Expects weekly_raw_values in strict week order:
    - Attendance: exactly 7 values (weeks 1-7)
    - Weekly Tut: exactly 6 values (weeks 2-7)
    """
    if criteria.category == CriteriaCategory.ATTENDANCE:
        weekly_bools = [parse_attendance_cell(v) for v in weekly_raw_values]
        score = calculate_attendance_pct(weekly_bools)
        trend = calculate_attendance_trend(weekly_bools)
    elif criteria.category == CriteriaCategory.WEEKLY_TUT:
        weekly_statuses = [parse_tutorial_cell(v) for v in weekly_raw_values]
        score = calculate_tutorial_completion_pct(weekly_statuses)
        trend = calculate_tutorial_completion_trend(weekly_statuses)
    else:
        raise ValueError(
            f"build_weekly_criterion_event called with unsupported category: {criteria.category}"
        )

    return build_assessment_event(
        student, unit_id, criteria, score, source, created_by, batch_id, trend_value=trend
    )


def process_bulk_upload(
    db: Session, unit_id: int, lecturer_id: int, filename: str, rows: list[dict],
    student_number_col: str, name_col: str,
    email_col: Optional[str], program_col: Optional[str],
    criteria_column_map: dict[int, str],
    weekly_criteria_column_map: Optional[dict[int, list[str]]] = None,
) -> tuple[IngestionBatch, list[dict], list[dict]]:
    """
    rows: one dict per CSV/Excel row, keyed by the file's original column
    headers (e.g. {"StudentID": "S1001", "Quiz1": "18", ...}).
    criteria_column_map: {criteria_id: column_name} - for criteria that
        are already a single value per student (Assessment, Moodle).
    weekly_criteria_column_map: {criteria_id: [column_name, ...]} - for
        Attendance/Weekly Tut, where the file has one raw column per week.

    Validation is per-cell, not per-row: if a row has 3 criteria columns
    and only 1 is invalid, the other 2 are still stored - "accept valid
    rows, report invalid ones" is applied at the finest useful grain
    rather than discarding a whole row over one bad cell.
    """
    weekly_criteria_column_map = weekly_criteria_column_map or {}

    all_criteria_ids = list(criteria_column_map.keys()) + list(weekly_criteria_column_map.keys())
    criteria_lookup = get_unit_criteria_map(db, unit_id, all_criteria_ids)

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

        # --- Single-value criteria: Assessment, Moodle ---
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

        # --- Weekly criteria: Attendance, Weekly Tut ---
        for criteria_id, weekly_columns in weekly_criteria_column_map.items():
            criteria = criteria_lookup[criteria_id]
            weekly_raw_values = [row.get(col) for col in weekly_columns]

            try:
                event = build_weekly_criterion_event(
                    student, unit_id, criteria, weekly_raw_values,
                    EventSource.BULK_UPLOAD, lecturer_id, batch.id,
                )
            except ValueError as e:
                errors.append({
                    "row": row_number, "student_number": student_number,
                    "criteria": criteria.name, "reason": str(e),
                })
                continue

            range_error = validate_score(criteria, event.score)
            if range_error:
                errors.append({
                    "row": row_number, "student_number": student_number,
                    "criteria": criteria.name, "reason": range_error,
                })
                continue

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
    stays None on these events. Manual entry is always a single final
    value per criterion (including Attendance/Tutorial) - a lecturer
    typing in one number, not raw weekly cells - so trend_value stays
    None for these events; trend is only ever computed from real weekly
    bulk-upload data."""
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