"""
Section C4 verification - checkpoints endpoint and download wiring.

The browser half (download button, week selector, tier filter) is
verified by the Playwright script; this covers the backend C4 adds and
re-checks that C1/C2's guarantees still hold after it.
"""

import sys
from pathlib import Path

from tests.report_test_fixture import NOW, WEEK, build_db
from app.services.report_service import available_checkpoints, build_unit_report

failures: list[str] = []
section = 0


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


db = build_db()

heading("Checkpoints - tenant isolation")
check(
    "own unit returns a list",
    available_checkpoints(db, lecturer_id=db.lecturer_id, unit_id=db.unit_id)
    is not None,
)
# Ownership is re-checked here rather than trusted from the report call:
# this is a separate request and its unit id is attacker-controlled.
check(
    "another lecturer's unit returns None (route renders 404)",
    available_checkpoints(
        db, lecturer_id=db.lecturer_id, unit_id=db.foreign_unit_id
    )
    is None,
)
check(
    "a unit that does not exist returns None",
    available_checkpoints(db, lecturer_id=db.lecturer_id, unit_id=99999) is None,
)
check(
    "the other lecturer cannot enumerate MY checkpoints",
    available_checkpoints(db, lecturer_id=db.other_id, unit_id=db.unit_id) is None,
)

checkpoints = available_checkpoints(
    db, lecturer_id=db.lecturer_id, unit_id=db.unit_id
)
assert checkpoints is not None

heading("Checkpoints - what is counted")
check("only weeks with an analysis are listed",
      [c["week"] for c in checkpoints] == [WEEK],
      str([c["week"] for c in checkpoints]))
# The fixture has FIVE verdict rows at week 8 for FOUR students: Ben
# carries a superseded verdict from a re-run. Counting rows would report
# 5 analysed students in a cohort of 5, one of whom was never analysed.
check("counts DISTINCT students, not append-only verdict rows",
      checkpoints[0]["student_count"] == 4,
      str(checkpoints[0]["student_count"]))
check("carries the analysis timestamp",
      checkpoints[0]["last_analysed_at"] is not None)
check("the timestamp is the LATEST verdict, not the superseded one",
      checkpoints[0]["last_analysed_at"].replace(tzinfo=None)
      == NOW.replace(tzinfo=None),
      str(checkpoints[0]["last_analysed_at"]))
check("the count agrees with the report's own analysed_count",
      checkpoints[0]["student_count"]
      == build_unit_report(db, lecturer_id=db.lecturer_id, unit_id=db.unit_id,
                           checkpoint_week=WEEK, now=NOW)["analysed_count"])

heading("A never-analysed unit lists nothing, and that is not an error")
# The foreign unit belongs to the other lecturer and has no verdicts.
empty = available_checkpoints(
    db, lecturer_id=db.other_id, unit_id=db.foreign_unit_id
)
check("owned but unanalysed returns a list, not None", empty == [], str(empty))
check("an empty list is distinguishable from a 404", empty is not None)

heading("Ordering")
check("weeks ascend, so the selector's LAST entry is the newest",
      [c["week"] for c in checkpoints] == sorted(c["week"] for c in checkpoints))

heading("Route wiring")
from app.api.routes.reports import router as reports_router  # noqa: E402

paths = {route.path for route in reports_router.routes}
check("checkpoints endpoint registered",
      "/lecturer/reports/unit/{unit_id}/checkpoints" in paths, str(paths))
check("pdf endpoint still registered",
      "/lecturer/reports/unit/{unit_id}/pdf" in paths)
check("json endpoint still registered",
      "/lecturer/reports/unit/{unit_id}" in paths)

route_source = Path("app/api/routes/reports.py").read_text()
check("all three endpoints 404 rather than 403 on an unowned unit",
      route_source.count("Unit not found") == 3,
      str(route_source.count("Unit not found")))
check("the router is still role-gated as a whole",
      len(reports_router.dependencies) >= 1)

heading("The download is still built server-side")
# C4 adds a button. It must not become a way to POST figures back.
# Grepping for "payload" was a false positive: the DOCSTRING uses the
# word to explain why there is no body. Assert the signature instead.
import inspect as _inspect  # noqa: E402

from app.api.routes.reports import download_unit_report  # noqa: E402

_params = set(_inspect.signature(download_unit_report).parameters)
check("the PDF endpoint takes no request body - only path, query and deps",
      _params == {"unit_id", "checkpoint_week", "db", "current_user"},
      str(_params))
check("the PDF is still built from the service",
      "build_report_pdf(report)" in route_source)
check("still sent as an attachment", "attachment; filename=" in route_source)
check("still uncached", "no-store" in route_source)

heading("C1 and C2 are unbroken by C4")
report = build_unit_report(
    db, lecturer_id=db.lecturer_id, unit_id=db.unit_id,
    checkpoint_week=WEEK, now=NOW,
)
assert report is not None
criteria = {row["category"]: row for row in report["criteria"]}
# The bug the PDF found. Pinned here too, because C4 touched this module.
check("the cohort assessment average is still normalised",
      criteria["assessment"]["average_score"] == 56.0,
      str(criteria["assessment"]["average_score"]))
check("moodle counts are still NOT divided by max_score",
      criteria["moodle"]["average_score"] == 11.8)
check("the at-risk list is still worst-first",
      report["at_risk"][0]["name"] == "Amy High")
check("caveats are still produced", len(report["caveats"]) > 0)

from app.services.report_pdf import build_report_pdf  # noqa: E402

check("the PDF still builds", build_report_pdf(report)[:5] == b"%PDF-")

print("\n" + "=" * 60)
if failures:
    print(f"FAILED: {len(failures)} check(s)")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print(f"ALL CHECKS PASSED ({section} sections)")