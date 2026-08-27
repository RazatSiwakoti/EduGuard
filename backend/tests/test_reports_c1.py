"""
Section C1 verification - report aggregation service + route.

The cohort lives in `report_test_fixture.py`, shared with C2 so the PDF
is proved against the same edge cases the aggregation was.

Each section prints PASS/FAIL and the script exits non-zero on any
failure, so it can be run unattended.
"""

import sys
from datetime import timedelta

from tests.report_test_fixture import NOW, WEEK, build_db
from app.services.report_service import build_unit_report

failures: list[str] = []
section = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    """One assertion, reported rather than raised, so later sections still run."""
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
# Sections
# ---------------------------------------------------------------------

db = build_db()
report = build_unit_report(
    db, lecturer_id=db.lecturer_id, unit_id=db.unit_id,
    checkpoint_week=WEEK, now=NOW,
)

heading("Tenant isolation")
check("own unit returns a report", report is not None)
check(
    "another lecturer's unit returns None (route renders 404)",
    build_unit_report(db, lecturer_id=db.lecturer_id,
                      unit_id=db.foreign_unit_id, now=NOW) is None,
)
check(
    "a unit that does not exist returns None",
    build_unit_report(db, lecturer_id=db.lecturer_id,
                      unit_id=99999, now=NOW) is None,
)
check(
    "the other lecturer cannot read MY unit",
    build_unit_report(db, lecturer_id=db.other_id,
                      unit_id=db.unit_id, now=NOW) is None,
)

assert report is not None

heading("Header")
check("unit code", report["unit_code"] == "ICT101", report["unit_code"])
check("lecturer name", report["lecturer_name"] == "Dr Mine")
check("checkpoint week echoed", report["checkpoint_week"] == WEEK)
check("enrolled counts everyone", report["enrolled_count"] == 5,
      str(report["enrolled_count"]))
check("analysed excludes the never-scored student", report["analysed_count"] == 4,
      str(report["analysed_count"]))
check("not-analysed is reported, not hidden", report["not_analysed_count"] == 1)

heading("Latest-per-group collapsing")
distribution = {row["bucket"]: row["count"] for row in report["distribution"]}
check("Ben counted once despite a superseded verdict",
      distribution["low_risk"] == 1, str(distribution))
check("no student counted into two tiers",
      sum(distribution.values()) == 5, str(distribution))
check("high risk = Amy only", distribution["high_risk"] == 1)
check("needs review = Dan only", distribution["needs_review"] == 1)
check("not analysed = Eve only", distribution["not_analysed"] == 1)

heading("Percentages divide by ANALYSED, not by everyone")
high = next(r for r in report["distribution"] if r["bucket"] == "high_risk")
check("1 of 4 analysed = 25.0%, not 20.0%", high["percent_of_analysed"] == 25.0,
      str(high["percent_of_analysed"]))

heading("Bucket ordering and labels")
check("worst tier first",
      [r["bucket"] for r in report["distribution"]][0] == "high_risk")
check("labels match the frontend's BUCKET_LABELS",
      high["label"] == "High Risk", high["label"])

heading("Criteria normalisation")
criteria = {row["category"]: row for row in report["criteria"]}
check("uncategorised criterion excluded from the category list",
      set(criteria) <= {"attendance", "weekly_tut", "assessment", "moodle"},
      str(set(criteria)))
# Amy quiz + Amy essay + Ben quiz + Cara quiz + Cara essay = 5.
# A sixth would mean the disabled "Old Test" mark leaked in.
check("disabled criterion contributes nothing",
      criteria["assessment"]["sample_size"] == 5,
      str(criteria["assessment"]["sample_size"]))
# Attendance: Amy 30, Ben 55, Cara 92, Dan 60 against a threshold of 50.
check("attendance average uses the LATEST event only",
      criteria["attendance"]["average_score"] == 59.2,
      str(criteria["attendance"]["average_score"]))
check("attendance % of threshold = 118.5",
      criteria["attendance"]["percent_of_threshold"] == 118.5,
      str(criteria["attendance"]["percent_of_threshold"]))
check("students below their own attendance threshold = 1 (Amy)",
      criteria["attendance"]["below_threshold"] == 1)
# Moodle: 2, 9, 30, 6 against 10 -> 20 + 90 + 300 + 60 = 470 / 4 = 117.5
check("moodle counts normalise against a count threshold",
      criteria["moodle"]["percent_of_threshold"] == 117.5,
      str(criteria["moodle"]["percent_of_threshold"]))
check("declining counted where a trend exists",
      criteria["attendance"]["declining_count"] == 2,
      str(criteria["attendance"]["declining_count"]))
check("declining is None where the question is meaningless",
      criteria["assessment"]["declining_count"] is None,
      str(criteria["assessment"]["declining_count"]))

heading("The max_score bug at COHORT level")
# Found by rendering the PDF, not by these tests - the original version of
# this suite asserted the student rows and took the cohort figures on
# trust. Marks: Amy 4/20 and 35/100, Ben 11/20, Cara 18/20 and 80/100.
#
# As percentages: 20, 35, 55, 90, 80 -> mean 56, and 2 of 5 sit below the
# 45% bar. Averaged RAW it is (4+35+11+18+80)/5 = 29.6 against a
# threshold of 45, and 4 of 5 look like failures - a mark out of 20 added
# to a mark out of 100 and compared against a percentage.
check("assessment average is normalised, not a raw mean",
      criteria["assessment"]["average_score"] == 56.0,
      str(criteria["assessment"]["average_score"]))
check("the raw mean is NOT what is reported",
      criteria["assessment"]["average_score"] != 29.6)
check("percent of threshold reflects the normalised marks",
      criteria["assessment"]["percent_of_threshold"] == 124.4,
      str(criteria["assessment"]["percent_of_threshold"]))
check("below-threshold counts marks below 45%, not below a raw 45",
      criteria["assessment"]["below_threshold"] == 2,
      str(criteria["assessment"]["below_threshold"]))
check("average score and average threshold are on the SAME scale",
      criteria["assessment"]["average_score"] >
      criteria["assessment"]["average_threshold"])
# Moodle is a login COUNT. Dividing it by max_score would be the same
# mistake in the opposite direction.
check("moodle counts are NOT divided by max_score",
      criteria["moodle"]["average_score"] == 11.8,
      str(criteria["moodle"]["average_score"]))
check("attendance percentages are left alone",
      criteria["attendance"]["average_score"] == 59.2,
      str(criteria["attendance"]["average_score"]))

# The cohort figure and the per-student figure must come from one code
# path, or they will drift apart exactly as they just did.
_marks = [r["assessment_avg_pct"] for r in report["at_risk"]
          if r["assessment_avg_pct"] is not None]
check("student rows and the cohort average use the same normalisation",
      all(0 <= m <= 100 for m in _marks), str(_marks))

heading("At-risk list")
at_risk = report["at_risk"]
check("safe students excluded", all(r["name"] != "Cara Safe" for r in at_risk))
check("never-analysed students excluded",
      all(r["name"] != "Eve Unscored" for r in at_risk))
check("unresolved review INCLUDED - the one who most needs a human",
      any(r["name"] == "Dan Review" for r in at_risk))
check("three at-risk rows", len(at_risk) == 3, str(len(at_risk)))
check("sorted worst first", at_risk[0]["name"] == "Amy High", at_risk[0]["name"])

amy_row = next(r for r in at_risk if r["name"] == "Amy High")
ben_row = next(r for r in at_risk if r["name"] == "Ben Low")
dan_row = next(r for r in at_risk if r["name"] == "Dan Review")

heading("The max_score bug that has been reintroduced twice")
# Amy: quiz 4/20 = 20%, essay 35/100 = 35%. Mean 27.5.
# A raw mean would be (4 + 35) / 2 = 19.5, which is a different claim.
check("assessment average normalised by max_score",
      amy_row["assessment_avg_pct"] == 27.5,
      str(amy_row["assessment_avg_pct"]))
check("raw marks are NOT averaged", amy_row["assessment_avg_pct"] != 19.5)
check("assessments marked counts marks on record",
      (ben_row["assessments_marked"], ben_row["assessments_total"]) == (1, 2),
      str((ben_row["assessments_marked"], ben_row["assessments_total"])))
check("Ben's single mark normalised: 11/20 = 55%",
      ben_row["assessment_avg_pct"] == 55.0,
      str(ben_row["assessment_avg_pct"]))

heading("Missing data is None, never zero")
check("Dan has no tutorial data -> None, not 0",
      dan_row["tutorial_pct"] is None, str(dan_row["tutorial_pct"]))
check("thresholds still reported for criteria with no data",
      dan_row["tutorial_threshold"] == 60.0, str(dan_row["tutorial_threshold"]))
check("Dan has no assessment marks -> avg is None",
      dan_row["assessment_avg_pct"] is None)
check("Dan's assessment total still shows what was expected",
      dan_row["assessments_total"] == 2, str(dan_row["assessments_total"]))
check("Amy's attendance is the latest 30, not the superseded 99",
      amy_row["attendance_pct"] == 30.0, str(amy_row["attendance_pct"]))
check("Amy's trend is the latest -25, not the superseded +50",
      amy_row["attendance_trend"] == -25.0, str(amy_row["attendance_trend"]))

heading("Provenance flags")
check("incomplete engine input surfaces on the row",
      amy_row["is_incomplete"] is True)
check("a complete score is not flagged", ben_row["is_incomplete"] is False)
check("Dan is flagged as awaiting a human", dan_row["requires_review"] is True)
check("Dan carries no tier", dan_row["risk_tier"] is None)
check("Dan still gets a readable label",
      dan_row["risk_label"] == "Needs Review", dan_row["risk_label"])
check("nobody here was decided by a lecturer",
      all(r["decided_by_lecturer"] is False for r in at_risk))

heading("Intervention record - alerts feature present")
intervention = report["intervention"]
check("alerts feature detected as present", intervention["available"] is True)
check("every alert counted", intervention["alerts_total"] == 4,
      str(intervention["alerts_total"]))
check("sent counted", intervention["alerts_sent"] == 2, str(intervention["alerts_sent"]))
check("failed counted separately from sent",
      intervention["alerts_failed"] == 1, str(intervention["alerts_failed"]))
check("still-queued counted separately from sent",
      intervention["alerts_queued"] == 1, str(intervention["alerts_queued"]))
check("automatic vs manual split",
      (intervention["alerts_automatic"], intervention["alerts_manual"]) == (2, 2),
      str((intervention["alerts_automatic"], intervention["alerts_manual"])))
# Amy was emailed twice. Counting alerts as people would overstate reach.
check("students contacted is DISTINCT students, not alerts sent",
      intervention["students_contacted"] == 2,
      str(intervention["students_contacted"]))
check("per-student alert count reaches the row",
      amy_row["alerts_sent"] == 2, str(amy_row["alerts_sent"]))
check("last alert is the most recent one, not the first",
      amy_row["last_alert_at"] is not None
      and amy_row["last_alert_at"].day == NOW.day,
      str(amy_row["last_alert_at"]))
check("a never-contacted at-risk student shows zero, not None",
      dan_row["alerts_sent"] == 0 and dan_row["last_alert_at"] is None)
check("resolved reviews counted", intervention["reviews_resolved"] == 1,
      str(intervention["reviews_resolved"]))
check("pending reviews counted", intervention["reviews_pending"] == 1,
      str(intervention["reviews_pending"]))

heading("Intervention record degrades honestly when alerts are absent")
# A deployment sitting on a migration older than Phase 7.8. Zeros here
# would read as "nobody was contacted" - a much stronger and much worse
# claim than "this feature is not installed".
from sqlalchemy import text as _sql_text  # noqa: E402

db.execute(_sql_text("DROP TABLE email_messages"))
db.commit()
degraded = build_unit_report(
    db, lecturer_id=db.lecturer_id, unit_id=db.unit_id,
    checkpoint_week=WEEK, now=NOW,
)
assert degraded is not None
check("absence detected rather than assumed",
      degraded["intervention"]["available"] is False)
check("no fabricated alert counts",
      degraded["intervention"]["alerts_total"] == 0)
check("reviews still counted without the alerts feature",
      degraded["intervention"]["reviews_resolved"] == 1)
check("the absence is disclosed in the caveats",
      any("not installed" in c for c in degraded["caveats"]),
      str(degraded["caveats"]))

heading("Caveats")
caveats = " ".join(report["caveats"])
check("unresolved disagreement is disclosed", "has no risk tier" in caveats, caveats)
check("never-analysed students are disclosed",
      "never been analysed" in caveats, caveats)
check("incomplete inputs are disclosed", "incomplete input data" in caveats)
check("the uncategorised criterion is named",
      "Participation" in caveats, caveats)
check("no false 'not installed' caveat when alerts ARE installed",
      "not installed" not in caveats, caveats)
check("a fresh analysis raises no staleness caveat",
      "days ago" not in caveats, caveats)

heading("Staleness")
stale = build_unit_report(
    db, lecturer_id=db.lecturer_id, unit_id=db.unit_id,
    checkpoint_week=WEEK, now=NOW + timedelta(days=21),
)
assert stale is not None
check("an old analysis is called out",
      any("21 days ago" in c for c in stale["caveats"]),
      str(stale["caveats"]))

heading("An empty checkpoint reports emptiness, not safety")
empty = build_unit_report(
    db, lecturer_id=db.lecturer_id, unit_id=db.unit_id,
    checkpoint_week=12, now=NOW,
)
assert empty is not None
check("nobody is analysed at week 12", empty["analysed_count"] == 0)
check("no percentage divides by zero",
      all(r["percent_of_analysed"] == 0.0 for r in empty["distribution"]))
check("the at-risk list is empty", empty["at_risk"] == [])
check("and that emptiness is explained",
      any("No analysis has been run" in c for c in empty["caveats"]),
      str(empty["caveats"]))

heading("Response validates against the schema")
from app.schemas.reports import ReportResponse  # noqa: E402

try:
    ReportResponse(**report)
    check("full report validates", True)
except Exception as exc:  # noqa: BLE001
    check("full report validates", False, str(exc))

try:
    ReportResponse(**empty)
    check("empty report validates", True)
except Exception as exc:  # noqa: BLE001
    check("empty report validates", False, str(exc))

heading("Route wiring")
# The router is imported directly rather than through main.py: main pulls
# in the ML engine, which needs shap, and this section is about URL shape
# and role gating, not about the model. Registration in main.py is
# asserted textually below - a router that exists but is never included
# is exactly the never-called wiring this project keeps producing.
from app.api.routes.reports import router as reports_router  # noqa: E402

paths = {route.path for route in reports_router.routes}
check("report endpoint registered on the router",
      "/lecturer/reports/unit/{unit_id}" in paths, str(paths))
check("router is role-gated at the router level",
      len(reports_router.dependencies) >= 1)

main_source = open("main.py").read()
check("router imported in main.py",
      "from app.api.routes.reports import router as reports_router" in main_source)
check("router actually included, not merely imported",
      "app.include_router(reports_router)" in main_source)

# ---------------------------------------------------------------------
print("\n" + "=" * 60)
if failures:
    print(f"FAILED: {len(failures)} check(s)")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print(f"ALL CHECKS PASSED ({section} sections)")