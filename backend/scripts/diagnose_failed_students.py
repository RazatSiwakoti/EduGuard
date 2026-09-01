"""
Why did N students fail to score?

READ-ONLY. This writes nothing, stages nothing and commits nothing. It
re-runs the analysis pipeline inside a transaction that is rolled back
at the end, purely to capture the exception text the API currently
throws away.

Save as  backend/scripts/diagnose_failed_students.py  and run from the
backend/ directory:

    python scripts/diagnose_failed_students.py
    python scripts/diagnose_failed_students.py --unit 3

No PYTHONPATH needed - the sys.path line below matches the convention
already used by seed_dev_users.py and the other scripts in this folder.
It reads DATABASE_URL from your .env exactly as the API does, so it
looks at the same database the app does.

WHY THIS SCRIPT HAS TO EXIST. `run_analysis_for_students` collects a
per-student `errors` list with the real reason. The route drops it, the
response schema has no field for it, and the button shows a hardcoded
sentence - "usually because required data is missing" - that is a guess
nobody verified. So the one fact needed to fix the problem is currently
unreachable from the UI. This gets it out.
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

# Same line seed_dev_users.py uses: makes `app.*` importable when this is
# run as `python scripts/...` from the backend/ directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.database import SessionLocal
import app.models  # noqa: F401 - registers every mapper
from app.models.criteria import Criteria
from app.models.enrollment import Enrollment
from app.models.student import Student
from app.models.unit import Unit
from app.services.analysis_service import run_analysis_for_students


def check_bad_max_scores(db) -> list[Criteria]:
    """
    Criteria that will divide by zero in the ML feature builder.

    `rule_score_service.normalise_to_percentage` and
    `report_service` both guard `max_score` explicitly. `ml_score_service`
    does not, so an assessment whose max_score is 0 raises
    "float division by zero" for every student who HAS a mark for it -
    and passes for every student who does not.
    """
    rows = db.execute(select(Criteria)).scalars().all()
    return [
        criterion for criterion in rows
        if criterion.max_score is None or criterion.max_score <= 0
    ]


def check_schema_drift(db) -> list[str]:
    """
    Columns the models declare that the database does not have.

    THE LEADING SUSPECT WHEN *EVERY* STUDENT FAILS. `select(RiskScore)`
    asks for every column the MODEL declares, so a database one
    migration behind makes the query itself blow up - identically, for
    every student, before any of their data is even looked at. That
    presents as "10 of 10 could not be scored" and reads like a data
    problem, which is what makes it worth ruling out first.
    """
    from sqlalchemy import inspect

    from app.models.assessment_event import AssessmentEvent
    from app.models.final_verdicts import FinalVerdict
    from app.models.risk_score import RiskScore

    inspector = inspect(db.get_bind())
    existing_tables = set(inspector.get_table_names())

    problems: list[str] = []
    for model in (RiskScore, FinalVerdict, Criteria, Unit, Student, AssessmentEvent):
        table = model.__tablename__
        if table not in existing_tables:
            problems.append(f"table '{table}' does not exist in the database")
            continue
        actual = {column["name"] for column in inspector.get_columns(table)}
        declared = {column.name for column in model.__table__.columns}
        for name in sorted(declared - actual):
            problems.append(
                f"{table}.{name} is declared by the model but MISSING from the "
                "database - run `alembic upgrade head`"
            )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unit", type=int, default=None, help="Limit to one unit id")
    parser.add_argument("--week", type=int, default=8, help="Checkpoint week")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        # ---------------- schema drift, checked FIRST ------------------
        drift = check_schema_drift(db)
        if drift:
            print("SCHEMA DRIFT - this alone can fail every student identically")
            for problem in drift:
                print(f"  {problem}")
            print(
                "\nSTOPPING HERE. Running the pipeline against a drifted schema\n"
                "only produces the same error repeated once per student, and\n"
                "this script would hit it too. Fix the drift, then re-run.\n"
            )
            return 1
        else:
            print("No schema drift: every model column exists in the database.\n")

        # ---------------- static check, no pipeline needed -------------
        suspicious = check_bad_max_scores(db)
        if suspicious:
            print("CRITERIA WITH A ZERO OR MISSING max_score")
            print("These divide by zero in ml_score_service for any student")
            print("who has a mark for them.\n")
            for criterion in suspicious:
                unit = db.get(Unit, criterion.unit_id)
                code = getattr(unit, "full_code", None) or getattr(unit, "unit_code", "?")
                print(
                    f"  unit {criterion.unit_id} ({code})  "
                    f"criteria {criterion.id} '{criterion.name}'  "
                    f"category={criterion.category}  max_score={criterion.max_score!r}"
                )
            print()
        else:
            print("No criteria have a zero or missing max_score.\n")

        # ---------------- live check, rolled back ----------------------
        unit_query = select(Unit)
        if args.unit:
            unit_query = unit_query.where(Unit.id == args.unit)
        units = db.execute(unit_query).scalars().all()

        grand_total = 0
        reason_tally: Counter = Counter()

        for unit in units:
            student_ids = list(
                db.execute(
                    select(Enrollment.student_id).where(Enrollment.unit_id == unit.id)
                ).scalars()
            )
            if not student_ids:
                continue

            outcome = run_analysis_for_students(db, unit.id, student_ids, args.week)
            if not outcome["errors"]:
                continue

            code = getattr(unit, "full_code", None) or unit.unit_code
            print(f"UNIT {unit.id} ({code}) - {outcome['failed']} of "
                  f"{outcome['total_students']} could not be scored")
            for error in outcome["errors"]:
                student = db.get(Student, error["student_id"])
                who = f"{student.student_number} {student.name}" if student else error["student_id"]
                print(f"   {who}")
                print(f"      {error['reason']}")
                reason_tally[error["reason"]] += 1
            grand_total += outcome["failed"]
            print()

        print("=" * 60)
        if not grand_total:
            print("No students failed. Every enrolled student scored.")
        else:
            print(f"{grand_total} student(s) failed, grouped by reason:\n")
            for reason, count in reason_tally.most_common():
                print(f"  {count:>4}  {reason}")
        return 0
    finally:
        # Nothing this script did is kept. The pipeline stages rows in
        # the session; rolling back discards every one of them.
        db.rollback()
        db.close()


if __name__ == "__main__":
    sys.exit(main())
    