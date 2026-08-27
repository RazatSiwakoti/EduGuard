"""
Section C2 verification - PDF rendering.

A PDF that builds without raising is not a PDF that is correct. Every
section here renders a real document and then reads the text back out of
it, so the assertions are about what a reader actually sees on the page.

Reuses C1's fixture: the same awkward cohort, so the PDF is proved
against the same edge cases the aggregation was.
"""

import re
import subprocess
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

from report_test_fixture import NOW, WEEK, build_db  # noqa: E402
from app.services.report_pdf import (  # noqa: E402
    MISSING,
    build_report_pdf,
    report_filename,
)
from app.services.report_service import build_unit_report  # noqa: E402

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


def text_of(pdf: bytes) -> str:
    """
    The rendered text, as a reader would see it.

    pdftotext rather than a Python parser: it is what actually ships on
    the machines this runs on, and it reads the page rather than the
    object model, so text hidden behind a layout bug does not count.
    """
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "r.pdf"
        source.write_bytes(pdf)
        result = subprocess.run(
            ["pdftotext", "-layout", str(source), "-"],
            capture_output=True, text=True, check=True,
        )
    return result.stdout


def page_count(pdf: bytes) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "r.pdf"
        source.write_bytes(pdf)
        result = subprocess.run(
            ["pdfinfo", str(source)], capture_output=True, text=True, check=True
        )
    match = re.search(r"Pages:\s+(\d+)", result.stdout)
    return int(match.group(1)) if match else 0


# ---------------------------------------------------------------------

db = build_db()
report = build_unit_report(
    db, lecturer_id=db.lecturer_id, unit_id=db.unit_id,
    checkpoint_week=WEEK, now=NOW,
)
assert report is not None
pdf = build_report_pdf(report)
body = text_of(pdf)

heading("It is a real PDF")
check("bytes returned", isinstance(pdf, bytes) and len(pdf) > 2000, str(len(pdf)))
check("PDF magic number", pdf[:5] == b"%PDF-")
check("terminated properly", b"%%EOF" in pdf[-1024:])
check("at least one page", page_count(pdf) >= 1, str(page_count(pdf)))

heading("The renderer cannot query anything")
# The signature is the guarantee: no Session, so it physically cannot
# recompute a figure and disagree with the screen.
import inspect as _inspect  # noqa: E402

params = list(_inspect.signature(build_report_pdf).parameters)
check("build_report_pdf takes only the report dict", params == ["report"],
      str(params))
source = Path("app/services/report_pdf.py").read_text()
check("no database imports in the renderer",
      "sqlalchemy" not in source and "get_db" not in source)
check("no model imports in the renderer", "app.models" not in source)

heading("Header identifies the document")
check("unit code on the page", "ICT101" in body)
check("unit name on the page", "Intro to ICT" in body)
check("lecturer named", "Dr Mine" in body)
check("checkpoint week stated", "Week 8" in body, body[:400])
check("generation time stated", "Generated" in body)
check("teaching period stated", "Semester 2" in body)

heading("Caveats are printed BEFORE the figures")
# The whole reason caveats are computed server-side. A reader must reach
# the qualifications before the numbers they qualify, not after.
panel = body.find("Read these before the figures")
cohort = body.find("Cohort summary")
check("caveat panel present", panel != -1)
check("caveat panel precedes the cohort figures",
      panel != -1 and cohort != -1 and panel < cohort,
      f"panel={panel} cohort={cohort}")
check("unresolved disagreement disclosed", "has no risk tier" in body)
check("never-analysed students disclosed", "never been analysed" in body)
check("incomplete inputs disclosed", "incomplete input data" in body)
check("uncategorised criterion named", "Participation" in body)
check("every caveat reached the page",
      all(c.split(".")[0][:40] in body.replace("\n", " ")
          for c in report["caveats"]),
      str(report["caveats"]))

heading("Cohort summary")
check("enrolled total printed", "Enrolled" in body)
check("analysed total printed", "Analysed" in body)
check("all five tiers listed",
      all(label in body for label in
          ["High Risk", "Low Risk", "Safe", "Needs Review", "Not Analysed"]))
check("percentage of ANALYSED printed, not of enrolled", "25%" in body, body)

heading("Criteria table")
check("normalisation explained on the page",
      "100% means exactly at the bar" in body.replace("\n", " "), body)
check("attendance row present", "Attendance" in body)
check("moodle row present", "Moodle" in body)
check("percent of threshold printed", "118.5%" in body, body)
check("declining count printed where it exists", "Declining" in body)

heading("At-risk list")
check("Amy listed", "Amy High" in body)
check("Ben listed", "Ben Low" in body)
check("Dan listed despite carrying no tier", "Dan Review" in body)
check("safe student NOT listed", "Cara Safe" not in body)
check("never-analysed student NOT listed", "Eve Unscored" not in body)
check("worst first", body.find("Amy High") < body.find("Ben Low"))
check("student numbers printed", "S001" in body)

heading("The max_score bug, in print")
# Amy: quiz 4/20 = 20%, essay 35/100 = 35%, mean 27.5. The raw mean
# would be 19.5 - a different and much more flattering claim.
check("normalised assessment average printed", "27.5%" in body, body)
check("raw mean NOT printed", "19.5%" not in body)
check("marked-vs-total shown", "marked" in body)

heading("Missing data prints a dash, never a zero")
check("the missing marker appears", MISSING in body)
cells = re.findall(r"(?<![\d.])0%", body)
check("no cell reads exactly 0% - missing data is not zero",
      cells == [], str(cells))
# A table row wraps across several output lines, so the assertion takes
# a window rather than one line. Dan has no tutorial mark and no
# assessment marks: BOTH must print the dash, not 0.
lines = body.splitlines()
start = next(i for i, ln in enumerate(lines) if "Dan Review" in ln)
dan_block = "\n".join(lines[start:start + 5])
check("Dan's row carries the missing marker for his absent figures",
      dan_block.count(MISSING) >= 2, repr(dan_block))

heading("Provenance reaches the page")
check("awaiting review flagged", "awaiting review" in body)
check("incomplete data flagged", "incomplete data" in body)
check("alerts already sent are shown", "alerts sent" in body or "alert sent" in body)
check("a student with no address is called out",
      "no email on record" not in body,
      "Eve has no email but is not at risk, so this must NOT appear")

heading("Intervention record")
check("section present", "Intervention record" in body)
check("sent count printed", "Alerts sent" in body)
check("failed counted separately", "Failed to send" in body)
check("distinct students, not messages", "Distinct students contacted" in body)
check("'sent' is qualified as not a read receipt",
      "not a read receipt" in body.replace("\n", " "), body)
check("reviews counted", "Engine disagreements resolved" in body)

heading("Footer and confidentiality")
check("page numbering present", "Page 1 of" in body, body[-600:])
check("footer names the unit and week",
      "ICT101" in body and "Week 8" in body)
check("confidentiality marked", "confidential" in body.lower())
check("automated-analysis disclaimer present",
      "not a determination about any student" in body.replace("\n", " "), body)

heading("Filename is meaningful in a downloads folder")
name = report_filename(report)
check("names the unit", name.startswith("ICT101"), name)
check("names the checkpoint", "week8" in name, name)
check("carries a date stamp", "20260826" in name, name)
check("is a pdf", name.endswith(".pdf"), name)
check("no path separators", "/" not in name and "\\" not in name, name)

heading("A cohort with nothing to report says so")
empty = build_unit_report(
    db, lecturer_id=db.lecturer_id, unit_id=db.unit_id,
    checkpoint_week=12, now=NOW,
)
assert empty is not None
empty_pdf = build_report_pdf(empty)
empty_body = text_of(empty_pdf)
check("empty report still renders", empty_pdf[:5] == b"%PDF-")
check("emptiness is stated, not left blank",
      "No students are currently on the at-risk list" in
      empty_body.replace("\n", " "), empty_body)
# The distribution must print the missing marker, not 0.0%, when the
# denominator is zero: a percentage of nothing is undefined, and 0.0%
# would read as "no students are at risk".
check("no percentage is fabricated from zero analysed",
      re.findall(r"(?<![\d.])0(?:\.0)?%", empty_body) == [],
      str(re.findall(r"(?<![\d.])0(?:\.0)?%", empty_body)))
check("the reason is printed",
      "No analysis has been run" in empty_body.replace("\n", " "), empty_body)

heading("A stale analysis says so on the page")
stale = build_unit_report(
    db, lecturer_id=db.lecturer_id, unit_id=db.unit_id,
    checkpoint_week=WEEK, now=NOW + timedelta(days=21),
)
assert stale is not None
stale_body = text_of(build_report_pdf(stale))
check("staleness printed", "21 days ago" in stale_body.replace("\n", " "),
      stale_body[:900])
# Deciding this myself: a stale analysis does NOT block the download. A
# lecturer at a deadline needs the document; refusing to produce it would
# push them to a spreadsheet nobody qualifies at all. The caveat is loud
# and it is above the figures, which is the honest middle.
check("but it does not block the document",
      "Amy High" in stale_body)

heading("Awkward content does not break the build")
# A student called "A & B <script>" would abort the XML parse if names
# were interpolated unescaped, and a report is built from user-entered data.
from app.models.student import Student  # noqa: E402

hostile = db.get(Student, report["at_risk"][0]["student_id"])
hostile.name = "Ana & Bo <b>Ć</b> O'Neill"
db.commit()
tricky = build_unit_report(
    db, lecturer_id=db.lecturer_id, unit_id=db.unit_id,
    checkpoint_week=WEEK, now=NOW,
)
assert tricky is not None
try:
    tricky_body = text_of(build_report_pdf(tricky))
    check("ampersands and angle brackets survive", True)
    check("the name is printed literally, not as markup",
          "Ana & Bo <b>" in tricky_body.replace("\n", " "), tricky_body[:1200])
except Exception as exc:  # noqa: BLE001
    check("ampersands and angle brackets survive", False, str(exc))
    check("the name is printed literally, not as markup", False)

heading("A large cohort paginates with its headings intact")
# 120 at-risk students spills over several pages. Without repeatRows the
# later pages lose their column headings and "55" in an unlabelled column
# means nothing at all.
big = dict(report)
template = report["at_risk"][0]
big["at_risk"] = [
    {**template, "student_id": i, "name": f"Student Number {i:03d}",
     "student_number": f"B{i:03d}", "email": f"b{i}@example.com"}
    for i in range(1, 121)
]
big_pdf = build_report_pdf(big)
big_body = text_of(big_pdf)
big_pages = page_count(big_pdf)
check("spills onto multiple pages", big_pages >= 3, str(big_pages))
check("every student rendered",
      all(f"Student Number {i:03d}" in big_body for i in (1, 60, 120)))
check("column headings repeat on later pages",
      big_body.count("Tutorial") >= 2, str(big_body.count("Tutorial")))
check("page numbers count the real total",
      f"Page {big_pages} of {big_pages}" in big_body.replace("\n", " "),
      big_body[-500:])

heading("Route wiring")
from app.api.routes.reports import router as reports_router  # noqa: E402

paths = {route.path for route in reports_router.routes}
check("pdf endpoint registered",
      "/lecturer/reports/unit/{unit_id}/pdf" in paths, str(paths))
check("json endpoint still registered",
      "/lecturer/reports/unit/{unit_id}" in paths, str(paths))

route_source = Path("app/api/routes/reports.py").read_text()
check("the PDF is built server-side from the service, not from a request body",
      "build_unit_report" in route_source and "def download_unit_report" in route_source)
check("sent as an attachment, not inline",
      "attachment; filename=" in route_source)
check("not cached - risk tiers change with every analysis run",
      "no-store" in route_source)
check("still 404 on a unit the caller does not teach",
      route_source.count("Unit not found") == 2, route_source.count("Unit not found"))

heading("reportlab is declared as a dependency")
requirements = Path("requirements.txt").read_text()
check("reportlab in requirements.txt", "reportlab" in requirements, requirements)

# ---------------------------------------------------------------------
print("\n" + "=" * 60)
if failures:
    print(f"FAILED: {len(failures)} check(s)")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print(f"ALL CHECKS PASSED ({section} sections)")