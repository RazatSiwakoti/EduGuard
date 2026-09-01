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
- Student demographic fields (name/email/program/gender/age) are never
  overwritten by ingestion, even if the upload disagrees with what's on
  file - a mismatch is reported as a warning only.
- Disabled Criteria still accept and store data - "enabled" is an
  analysis-time filter for Phase 5, not an ingestion-time gate.
- Weekly Attendance/Tutorial cells (from bulk CSV columns OR manual
  entry's weekly_scores) are aggregated into ONE percentage AND one
  trend value before storage - raw weekly values are never persisted
  separately. A blank/unrecognised weekly cell counts as absent/
  not_submitted (0 credit for that week), consistent with the
  project-wide rule that unsubmitted work is always a real 0.
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
    gender: Optional[str] = None, age: Optional[int] = None,
) -> tuple[Student, Optional[str]]:
    """
    Matches by student_number - the only reliable identifier across
    uploads. If found, existing name/email/program/gender/age are NEVER
    overwritten; a mismatch just produces a warning string for the
    caller to report. If not found, a new Student is created - name is
    required in this case since Student.name is NOT NULL at the DB level.
    """
    student_number = str(student_number).strip()
    student = db.query(Student).filter(Student.student_number == student_number).first()

    if student:
        mismatches = []
        if name and student.name != name:
            mismatches.append(f"name ('{student.name}' on file vs '{name}' uploaded)")
        if email and student.email and student.email != email:
            mismatches.append(f"email ('{student.email}' on file vs '{email}' uploaded)")
        if program and student.program and student.program != program:
            mismatches.append(f"program ('{student.program}' on file vs '{program}' uploaded)")
        if gender and student.gender and student.gender != gender:
            mismatches.append(f"gender ('{student.gender}' on file vs '{gender}' uploaded)")
        if age is not None and student.age is not None and student.age != age:
            mismatches.append(f"age ('{student.age}' on file vs '{age}' uploaded)")

        warning = None
        if mismatches:
            warning = (
                f"Student {student_number} details differ from upload: "
                f"{', '.join(mismatches)} - record was NOT updated."
            )
        return student, warning

    if not name:
        raise ValueError(f"Cannot create new student '{student_number}': name is required")

    student = Student(
        student_number=student_number, name=name, email=email,
        program=program, gender=gender, age=age,
    )
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
    weekly_values: Optional[list] = None,
) -> AssessmentEvent:
    """Stages one immutable raw data point. Never call this to 'fix' an
    existing row - always creates a new one. trend_value and
    weekly_values are only ever set for Attendance/Weekly Tut events;
    None for everything else.

    weekly_values carries the NORMALISED cells the score was aggregated
    from, so the per-week detail survives instead of being thrown away
    (Phase 7.6b). It stays on this row, which means a corrected event
    carries its own weekly list and the old one is superseded rather
    than mutated - the same immutability every other field here has."""
    return AssessmentEvent(
        student_id=student.id,
        unit_id=unit_id,
        criteria_id=criteria.id,
        score=score,
        trend_value=trend_value,
        weekly_values=weekly_values,
        source=source,
        created_by=created_by,
        batch_id=batch_id,
    )


# ---------------------------------------------------------------------------
# Weekly cell parsing (Attendance / Weekly Tut only) - shared by both
# bulk CSV columns and manual entry's weekly_scores
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
    stages both on one AssessmentEvent row.

    Since Phase 7.6b the NORMALISED weekly cells are also stored on that
    row (weekly_values), so the student card can draw a real week-by-week
    chart. The aggregate remains what every engine reads - nothing about
    scoring changed, this is an additional record of the input.

    Used identically by bulk upload (values from CSV columns) and
    manual entry (values typed directly) - same function, same result,
    regardless of how the raw values arrived.

    Expects weekly_raw_values in strict week order:
    - Attendance: exactly 7 values (weeks 1-7)
    - Weekly Tut: exactly 6 values (weeks 2-7)
    A different length still produces a valid percentage, but trend
    comes back None rather than erroring (see rule_engine.py's trend
    functions - they require the exact expected length).
    """
    if criteria.category == CriteriaCategory.ATTENDANCE:
        weekly_bools = [parse_attendance_cell(v) for v in weekly_raw_values]
        score = calculate_attendance_pct(weekly_bools)
        trend = calculate_attendance_trend(weekly_bools)
        # The NORMALISED cells, not the raw ones. "Y", "yes" and "1" all
        # mean the same thing to the engines, so storing the parsed form
        # keeps the chart consistent no matter how the file was written.
        normalised = weekly_bools
    elif criteria.category == CriteriaCategory.WEEKLY_TUT:
        weekly_statuses = [parse_tutorial_cell(v) for v in weekly_raw_values]
        score = calculate_tutorial_completion_pct(weekly_statuses)
        trend = calculate_tutorial_completion_trend(weekly_statuses)
        normalised = weekly_statuses
    else:
        raise ValueError(
            f"build_weekly_criterion_event called with unsupported category: {criteria.category}"
        )

    return build_assessment_event(
        student,
        unit_id,
        criteria,
        score,
        source,
        created_by,
        batch_id,
        trend_value=trend,
        weekly_values=normalised,
    )


def _parse_age(raw_value) -> Optional[int]:
    """Best-effort int parse for age from a CSV cell (which may arrive
    as '20', '20.0', or similar). Malformed values are silently ignored
    (treated as not provided) rather than failing the whole row over a
    non-critical demographic field."""
    if raw_value in (None, ""):
        return None
    try:
        return int(float(raw_value))
    except (TypeError, ValueError):
        return None


def process_bulk_upload(
    db: Session, unit_id: int, lecturer_id: int, filename: str, rows: list[dict],
    student_number_col: str, name_col: str,
    email_col: Optional[str], program_col: Optional[str],
    criteria_column_map: dict[int, str],
    weekly_criteria_column_map: Optional[dict[int, list[str]]] = None,
    gender_col: Optional[str] = None,
    age_col: Optional[str] = None,
) -> tuple[IngestionBatch, list[dict], list[dict], set[int]]:
    """
    rows: one dict per CSV/Excel row, keyed by the file's original column
    headers.
    criteria_column_map: {criteria_id: column_name} - single-value criteria.
    weekly_criteria_column_map: {criteria_id: [column_name, ...]} - weekly criteria.

    Returns the set of student.id values that had at least one
    AssessmentEvent successfully created in this batch, so the caller
    knows which students need re-analysis.
    """
    weekly_criteria_column_map = weekly_criteria_column_map or {}

    all_criteria_ids = list(criteria_column_map.keys()) + list(weekly_criteria_column_map.keys())
    criteria_lookup = get_unit_criteria_map(db, unit_id, all_criteria_ids)

    batch = IngestionBatch(
        unit_id=unit_id, lecturer_id=lecturer_id, filename=filename, total_rows=len(rows)
    )
    db.add(batch)
    db.flush()

    errors: list[dict] = []
    warnings: list[dict] = []
    success_count = 0
    touched_student_ids: set[int] = set()

    for row_number, row in enumerate(rows, start=1):
        student_number = row.get(student_number_col)
        name = row.get(name_col)
        email = row.get(email_col) if email_col else None
        program = row.get(program_col) if program_col else None
        gender = row.get(gender_col) if gender_col else None
        age = _parse_age(row.get(age_col)) if age_col else None

        if not student_number:
            errors.append({"row": row_number, "reason": "Missing student_number - row skipped"})
            continue

        try:
            student, warning = resolve_or_create_student(
                db, student_number, name, email, program, gender, age
            )
        except ValueError as e:
            errors.append({"row": row_number, "student_number": student_number, "reason": str(e)})
            continue

        if warning:
            warnings.append({"row": row_number, "student_number": student_number, "message": warning})

        resolve_or_create_enrollment(db, student.id, unit_id)

        for criteria_id, column_name in criteria_column_map.items():
            raw_value = row.get(column_name)
            if raw_value in (None, ""):
                continue

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
            touched_student_ids.add(student.id)

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
            touched_student_ids.add(student.id)

    batch.values_stored = success_count
    batch.values_failed = len(errors)

    return batch, errors, warnings, touched_student_ids


def process_manual_entry(
    db: Session, unit_id: int, lecturer_id: int, student_number: str,
    name: Optional[str], email: Optional[str], program: Optional[str],
    gender: Optional[str], age: Optional[int],
        scores: dict[int, float],
    weekly_scores: Optional[dict[int, list]] = None,
) -> tuple[list[AssessmentEvent], list[dict], list[dict], bool, bool]:
    """
    Same validation path as bulk upload, minus the IngestionBatch -
    there's no file to group a single manual entry under, so batch_id
    stays None on these events.

    scores handles single-value criteria (Assessment, Moodle).
    weekly_scores handles Attendance/Weekly Tut, using the SAME
    aggregation logic as bulk upload - a lecturer typing 7 weekly
    values manually gets an identical percentage + trend calculation
    to a CSV column doing the same thing.

    Returns (events, errors, warnings, student_created, enrollment_created).

    The two booleans exist because resolve_or_create_* are deliberately
    silent about which branch they took - reusing an existing student is
    the CORRECT behaviour, not a warning-worthy event. But a caller
    showing a lecturer "student added" when the student already existed
    and was merely given new scores is telling them something false.
    Only the caller knows whether that distinction matters, so the fact
    is reported rather than acted on here.
    """
    weekly_scores = weekly_scores or {}
    all_criteria_ids = list(scores.keys()) + list(weekly_scores.keys())
    criteria_lookup = get_unit_criteria_map(db, unit_id, all_criteria_ids)

    errors: list[dict] = []
    warnings: list[dict] = []

    # Checked BEFORE resolve_or_create_* runs, since afterwards a
    # created row and a pre-existing one are indistinguishable. Two
    # cheap indexed lookups; deliberately not folded into the shared
    # helpers, which bulk upload also calls on a per-row hot path.
    student_existed = (
        db.query(Student).filter(Student.student_number == student_number).first()
        is not None
    )

    try:
        student, warning = resolve_or_create_student(
            db, student_number, name, email, program, gender, age
        )
    except ValueError as e:
        return [], [{"reason": str(e)}], [], False, False

    if warning:
        warnings.append({"student_number": student_number, "message": warning})

    enrollment_existed = (
        db.query(Enrollment)
        .filter(Enrollment.student_id == student.id, Enrollment.unit_id == unit_id)
        .first()
        is not None
    )

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

    for criteria_id, weekly_raw_values in weekly_scores.items():
        criteria = criteria_lookup[criteria_id]

        try:
            event = build_weekly_criterion_event(
                student, unit_id, criteria, weekly_raw_values,
                EventSource.MANUAL, lecturer_id, None,
            )
        except ValueError as e:
            errors.append({"student_number": student_number, "criteria": criteria.name, "reason": str(e)})
            continue

        range_error = validate_score(criteria, event.score)
        if range_error:
            errors.append({"student_number": student_number, "criteria": criteria.name, "reason": range_error})
            continue

        db.add(event)
        created_events.append(event)

    return (
        created_events,
        errors,
        warnings,
        not student_existed,
        not enrollment_existed,
    )


