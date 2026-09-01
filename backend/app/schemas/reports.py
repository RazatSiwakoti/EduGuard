"""
Pydantic schemas for the lecturer report (Phase 7.9 / section C1).

WHY A REPORT NEEDS ITS OWN SHAPE
--------------------------------
The dashboard payload is built for cross-filtering: one flat row per
student, aggregated in the browser so a filter click costs nothing. A
report is the opposite problem. It is a fixed document about one unit at
one checkpoint, it is aggregated ONCE, and a copy of it leaves the
building as a PDF. Reusing the dashboard payload would mean the browser
computing the figures, the PDF generator computing them again, and the
two quietly disagreeing the first time either changed.

So the server produces the finished numbers, and both the screen and the
PDF render the same object.

CAVEATS ARE DATA, NOT DECORATION
--------------------------------
Every screen in this application qualifies what it shows: a tooltip
saying "sent" means SMTP accepted it, an amber icon meaning the score
used incomplete data, a badge saying a human overruled the engines. A
PDF carries none of that - it gets forwarded to a course coordinator
with no hover states and no context.

`caveats` is therefore computed server-side and rendered in BOTH places.
It is the mechanism that stops a document leaving the building claiming
more certainty than the system has.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ReportBucketCount(BaseModel):
    """One risk tier and how many students are in it."""

    bucket: str
    label: str
    count: int
    #: Share of ANALYSED students, not of everyone. Including students the
    #: engines never scored would understate the risk rate, which is the
    #: opposite of what an early-warning system should do.
    percent_of_analysed: float


class ReportCriterionSummary(BaseModel):
    """
    Cohort performance on one criterion category.

    `percent_of_threshold` exists because the categories are not
    comparable raw: attendance is a percentage against a threshold of 50,
    while Moodle is a login COUNT against a threshold of 10. Dividing
    each student's value by the threshold they were actually held to puts
    every category on one axis where 100% means "exactly at the bar".

    Normalised per student BEFORE averaging, because thresholds are set
    per unit and two units can hold students to different bars.
    """

    category: str
    label: str
    #: On the SAME scale as `average_threshold`. Assessment marks are
    #: divided by their own max_score first, so this is a percentage, not
    #: a raw mark - otherwise a mark out of 20 would be averaged with a
    #: mark out of 100 and compared against a percentage threshold.
    average_score: float
    average_threshold: float
    percent_of_threshold: float
    #: How many student-criterion data points went into the average.
    sample_size: int
    #: How many of those sat below their own threshold.
    below_threshold: int
    #: Only ever populated for attendance and weekly tutorials - the
    #: other two are single figures with no early/late window.
    declining_count: Optional[int] = None


class ReportStudentRow(BaseModel):
    """
    One student in the at-risk list, with the figures behind their tier.

    Percentages are pre-rounded and assessments are pre-normalised, so
    the PDF and the screen cannot round differently and print two
    different numbers for the same student.
    """

    student_id: int
    student_number: str
    name: str
    email: Optional[str] = None

    risk_tier: Optional[str] = None
    risk_label: str

    #: None means NOT RECORDED, never zero. A student with no attendance
    #: data has not attended zero classes - nobody has measured them.
    attendance_pct: Optional[float] = None
    attendance_threshold: Optional[float] = None
    attendance_trend: Optional[float] = None

    tutorial_pct: Optional[float] = None
    tutorial_threshold: Optional[float] = None

    #: "Marked", not "submitted". A blank cell creates no event while a
    #: literal 0 creates one scored zero, so this counts marks on record.
    assessments_marked: int = 0
    assessments_total: int = 0
    #: Mean of marked assessments as a percentage of their own max_score.
    assessment_avg_pct: Optional[float] = None

    moodle_logins: Optional[float] = None
    moodle_threshold: Optional[float] = None

    #: An engine flagged missing inputs. Printed beside the row so a
    #: reader of the PDF knows which figures to distrust.
    is_incomplete: bool = False
    #: True when the tier came from a HUMAN resolving an engine
    #: disagreement rather than from the engines agreeing.
    decided_by_lecturer: bool = False
    reviewer_name: Optional[str] = None
    #: Still unresolved: the engines disagreed and nobody has decided.
    requires_review: bool = False

    #: Whether this student has been emailed about this unit, and when.
    #: Empty when the alerts feature is not installed.
    alerts_sent: int = 0
    last_alert_at: Optional[datetime] = None

    #: How many of those the student confirmed receiving, and when they
    #: last did. Zero means either "not confirmed" or "cannot be
    #: recorded on this deployment" - the intervention summary's
    #: `acknowledgment_available` is what separates the two, and the
    #: caveats say so in words.
    alerts_acknowledged: int = 0
    last_acknowledged_at: Optional[datetime] = None


class ReportInterventionSummary(BaseModel):
    """
    What the lecturer DID, as distinct from what the engines found.

    This is the section that makes the document a record of an
    intervention rather than only a diagnosis.
    """

    #: False when the alerts feature is not installed on this deployment.
    #: The report still renders; this section says so instead of showing
    #: zeros that would read as "nobody was contacted".
    available: bool = True

    alerts_total: int = 0
    alerts_sent: int = 0
    alerts_failed: int = 0
    alerts_queued: int = 0
    alerts_automatic: int = 0
    alerts_manual: int = 0
    #: Distinct students contacted, which is not the same as alerts sent -
    #: one student can be emailed more than once over a semester.
    students_contacted: int = 0

    #: False when this deployment predates the acknowledgment columns.
    #: Separate from `available` on purpose: a working alerts feature
    #: that cannot record receipts is not an absent alerts feature, and
    #: zero confirmations on such a deployment is a fact about the
    #: database rather than about the students.
    acknowledgment_available: bool = False
    #: Messages a student confirmed receiving.
    alerts_acknowledged: int = 0
    #: Distinct students who confirmed at least one - not the same
    #: number, since one student can confirm three messages.
    students_acknowledged: int = 0

    reviews_resolved: int = 0
    reviews_pending: int = 0
    
class ReportCheckpoint(BaseModel):
    """
    One checkpoint week that actually has an analysis behind it.

    The week selector is built from these rather than from a fixed 1-14
    range. Offering a lecturer thirteen weeks that would all render
    "no analysis has been run" is a menu of dead ends; offering only the
    weeks that were analysed is a short, honest list.
    """

    week: int
    #: Distinct students with a verdict at this week - NOT rows, because
    #: the verdict table is append-only and a re-run leaves several.
    student_count: int
    last_analysed_at: Optional[datetime] = None

class ReportResponse(BaseModel):
    """One unit's complete report at one checkpoint."""

    unit_id: int
    unit_code: str
    class_code: str = ""
    #: "ICT730LA1" - what the header and the filename print.
    full_code: str = ""
    unit_name: str
    year: Optional[int] = None
    teaching_period: Optional[str] = None
    lecturer_name: Optional[str] = None

    checkpoint_week: int
    generated_at: datetime

    enrolled_count: int
    analysed_count: int
    not_analysed_count: int
    #: When the most recent verdict in this unit was computed. A report
    #: generated today from an analysis run three weeks ago should say so.
    last_analysed_at: Optional[datetime] = None

    distribution: list[ReportBucketCount] = []
    criteria: list[ReportCriterionSummary] = []
    at_risk: list[ReportStudentRow] = []
    intervention: ReportInterventionSummary

    #: Honest qualifications, computed server-side and rendered in BOTH
    #: the on-screen view and the PDF. See the module docstring.
    caveats: list[str] = []