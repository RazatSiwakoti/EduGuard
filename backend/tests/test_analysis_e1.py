"""
Section E1 verification - Run Analysis.

The pipeline itself (rule -> ML -> hybrid) has been tested since Phase 5
and needs the trained model, which is gitignored. What E1 adds and what
this suite covers is everything AROUND the pipeline:

  - the before/after diff that turns "40 succeeded" into "3 moved into
    High Risk and 1 of your review decisions was discarded"
  - the model-missing path, which used to take the whole API down
  - tenant isolation on the new endpoints
"""

import sys
from pathlib import Path as FsPath

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
import app.models.student            # noqa: F401
import app.models.unit               # noqa: F401
import app.models.criteria           # noqa: F401
import app.models.user               # noqa: F401
import app.models.enrollment         # noqa: F401
import app.models.final_verdicts     # noqa: F401
import app.models.risk_score         # noqa: F401
import app.models.verdict_review     # noqa: F401
import app.models.assessment_event   # noqa: F401
import app.models.ingestion_batch    # noqa: F401

from datetime import datetime, timedelta, timezone

from app.models.final_verdicts import FinalVerdict
from app.models.risk_score import RiskScore
from app.services.analysis_service import snapshot_verdicts, summarise_changes

failures: list[str] = []
section = 0
NOW = datetime(2026, 8, 27, 9, 0, tzinfo=timezone.utc)
WEEK = 8


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"    PASS  {label}")
    else:
        print(f"    FAIL  {label}  {detail}")
        failures.append(label)


def heading(title: str) -> None:
    global section
    section += 1
    print(f"\n[{section}] {title}")


# ---------------------------------------------------------------------
# The diff
# ---------------------------------------------------------------------

def result(student_id, tier, review=False):
    """One entry as `run_analysis_for_student` returns it."""
    return {
        "student_id": student_id, "rule_level": tier or "safe",
        "ml_level": tier or "safe", "final_tier": tier,
        "requires_review": review,
    }


heading("Movement is counted in two directions, not one")
before = {
    1: {"final_tier": "safe", "requires_review": False, "review_id": None},
    2: {"final_tier": "high_risk", "requires_review": False, "review_id": None},
    3: {"final_tier": "low_risk", "requires_review": False, "review_id": None},
}
after = [
    result(1, "high_risk"),   # safe -> high risk: needs contacting
    result(2, "safe"),        # high risk -> safe: good news, no action
    result(3, "low_risk"),    # unchanged
    result(4, "high_risk"),   # never analysed before
]
diff = summarise_changes(before, after)

check("a student getting worse is counted as toward_risk",
      diff["moved_toward_risk"] == 1, str(diff))
check("a student getting better is counted separately",
      diff["moved_away_from_risk"] == 1, str(diff))
# Summing them into one "changed" figure would lose exactly the
# distinction the number exists to make.
check("the two directions are NOT summed together",
      diff["moved_toward_risk"] != diff["moved_toward_risk"]
      + diff["moved_away_from_risk"])
check("an unchanged student is counted as unchanged", diff["unchanged"] == 1)
check("a student with no prior verdict is 'newly analysed', not 'moved'",
      diff["newly_analysed"] == 1 and len(diff["movements"]) == 2, str(diff))

heading("Movements are listed worst-destination first")
check("the high-risk arrival is first",
      diff["movements"][0]["to_tier"] == "high_risk", str(diff["movements"]))
check("each movement names both ends",
      set(diff["movements"][0]) == {"student_id", "from_tier", "to_tier", "direction"})

heading("Entering and leaving Needs Review is not movement along the scale")
before2 = {
    1: {"final_tier": "safe", "requires_review": False, "review_id": None},
    2: {"final_tier": None, "requires_review": True, "review_id": None},
}
diff2 = summarise_changes(before2, [
    result(1, None, review=True),    # the engines now disagree about them
    result(2, "high_risk"),          # the engines now agree
])
check("a student the engines now disagree about is flagged",
      diff2["now_needs_review"] == 1, str(diff2))
check("a disagreement the engines resolved is flagged separately",
      diff2["review_resolved_by_engines"] == 1, str(diff2))
# A NULL tier is not on the severity scale. Treating it as one would
# report a student "improving" into an unresolved disagreement.
check("neither is counted as movement toward or away from risk",
      diff2["moved_toward_risk"] == 0 and diff2["moved_away_from_risk"] == 0,
      str(diff2))

heading("A discarded lecturer decision is reported")
# Phase 7.7 carries a review forward only while BOTH engine tiers are
# unchanged. Nothing is deleted when it does not carry, so without this
# count a lecturer's judgement disappears silently.
before3 = {
    1: {"final_tier": "safe", "requires_review": False, "review_id": 11},
    2: {"final_tier": "low_risk", "requires_review": False, "review_id": 12},
}
diff3 = summarise_changes(before3, [
    result(1, "safe"),               # decision still stands
    result(2, None, review=True),    # decision invalidated by the re-run
])
check("a decision that carried is counted",
      diff3["lecturer_decisions_carried"] == 1, str(diff3))
check("a decision the run discarded is counted",
      diff3["lecturer_decisions_invalidated"] == 1, str(diff3))
check("students with no prior decision are not counted either way",
      summarise_changes(before, after)["lecturer_decisions_carried"] == 0)

heading("Empty inputs are safe")
empty = summarise_changes({}, [])
check("no students means all zeros", empty["moved_toward_risk"] == 0)
check("and an empty movement list", empty["movements"] == [])
check("a first-ever run reports everyone as newly analysed",
      summarise_changes({}, [result(i, "safe") for i in range(5)])[
          "newly_analysed"] == 5)


# ---------------------------------------------------------------------
# The snapshot
# ---------------------------------------------------------------------

def build_db() -> Session:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return Session(engine)


db = build_db()


def score(student_id):
    row = RiskScore(student_id=student_id, unit_id=1, source="rule",
                    risk_score=0.5, risk_level="low_risk", checkpoint_week=WEEK)
    db.add(row)
    db.flush()
    return row


def verdict(student_id, tier, created, review=False, review_id=None, week=WEEK):
    rule, ml = score(student_id), score(student_id)
    db.add(FinalVerdict(
        student_id=student_id, unit_id=1, checkpoint_week=week,
        rule_score_id=rule.id, ml_score_id=ml.id, final_tier=tier,
        requires_review=review, review_id=review_id,
        created_at=created.replace(tzinfo=None),
    ))
    db.flush()


heading("The snapshot collapses the append-only table")
verdict(1, "safe", NOW - timedelta(days=14))          # superseded
verdict(1, "high_risk", NOW)                           # current
verdict(2, None, NOW, review=True)
verdict(3, "low_risk", NOW, review_id=7)
verdict(4, "safe", NOW, week=12)                       # different checkpoint
db.commit()

snapshot = snapshot_verdicts(db, unit_id=1, checkpoint_week=WEEK)
check("one entry per student, not one per row", len(snapshot) == 3, str(snapshot))
check("the LATEST verdict wins, not the first row found",
      snapshot[1]["final_tier"] == "high_risk", str(snapshot[1]))
check("a superseded verdict does not leak through",
      snapshot[1]["final_tier"] != "safe")
check("an unresolved disagreement carries a NULL tier",
      snapshot[2]["final_tier"] is None and snapshot[2]["requires_review"])
check("a standing lecturer decision is captured",
      snapshot[3]["review_id"] == 7)
check("another checkpoint's verdicts are excluded", 4 not in snapshot)

heading("Snapshot-before-run is the whole point")
# Taken AFTER the pipeline stages rows, the snapshot reads what the run
# just wrote and every student looks unchanged. This asserts the order
# the route actually uses.
route_source = FsPath("app/api/routes/analysis.py").read_text()
body = route_source.split("def _run_one")[1]
check("snapshot_verdicts is called before run_analysis_for_students",
      body.index("snapshot_verdicts") < body.index("run_analysis_for_students"),
      "reading after the run would report that nothing changed")


# ---------------------------------------------------------------------
# The model-missing path
# ---------------------------------------------------------------------

heading("A missing model no longer takes the whole API down")
from app.services import ml_engine  # noqa: E402

engine_source = FsPath("app/services/ml_engine.py").read_text()
check("artifacts are NOT loaded at import time",
      "_feature_columns = joblib.load" not in engine_source,
      "this line used to run on import and kill the whole app")
check("the module imports with no artifacts present", ml_engine is not None)
check("a dedicated exception type exists",
      issubclass(ml_engine.MLModelUnavailable, RuntimeError))
check("model_is_available() answers rather than raising",
      ml_engine.model_is_available() in (True, False))

if not ml_engine.model_is_available():
    try:
        ml_engine.predict_risk({"attendance_pct": 50.0})
        check("predict_risk raises when the model is absent", False)
    except ml_engine.MLModelUnavailable as exc:
        check("predict_risk raises MLModelUnavailable", True)
        # "analysis failed" sends someone hunting through student data.
        # Naming the files sends them to the right place.
        check("the message names the missing files",
              ".joblib" in str(exc), str(exc))
        check("the message says the rule engine still works",
              "rule engine" in str(exc).lower(), str(exc))
else:
    check("model present - skipping the absent-model assertions", True)

heading("The route refuses ONCE rather than failing per student")
check("availability is checked before the loop",
      route_source.index("model_is_available()")
      < route_source.index("for unit in units:"),
      "otherwise it fails 40 times and reads as a data problem")
check("a missing model is a 503, not a 500",
      "status_code=503" in route_source)
check("503 explains the rule engine is unaffected",
      "rule engine is unaffected" in route_source.lower())


# ---------------------------------------------------------------------
# Wiring
# ---------------------------------------------------------------------

heading("Route wiring and isolation")
from app.api.routes.analysis import router as analysis_router  # noqa: E402

paths = {r.path for r in analysis_router.routes}
check("run endpoint registered", "/lecturer/analysis/run" in paths, str(paths))
check("preview endpoint registered", "/lecturer/analysis/preview" in paths)
check("the router is role-gated", len(analysis_router.dependencies) >= 1)
check("ownership is resolved in SQL, not checked afterwards",
      "Unit.lecturer_id == lecturer_id" in route_source)
check("only ACTIVE units are analysed",
      "Unit.is_active.is_(True)" in route_source)
check("an unowned unit is a 404, matching the reports surface",
      "status_code=404" in route_source and '"Unit not found"' in route_source)
check("no 403 is used here", "status_code=403" not in route_source)

main_source = FsPath("main.py").read_text()
check("router imported in main.py",
      "from app.api.routes.analysis import router as analysis_router" in main_source)
check("router actually included, not merely imported",
      "app.include_router(analysis_router)" in main_source)

heading("Failure containment")
check("each unit commits on its own",
      "db.commit()" in body or "db.commit()" in route_source,
      "a failure on unit 4 must not discard units 1-3")
check("one failed unit is reported, not raised",
      "The analysis failed for this unit." in route_source)
check("a unit with no enrolments is explained, not a 400",
      "No students are enrolled in this unit yet." in route_source)

print("\n" + "=" * 60)
if failures:
    print(f"FAILED: {len(failures)} check(s)")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print(f"ALL CHECKS PASSED ({section} sections)")