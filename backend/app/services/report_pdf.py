"""
Renders a unit report as a PDF (section C2).

THIS MODULE NEVER TOUCHES THE DATABASE
--------------------------------------
Its only input is the dict `report_service.build_unit_report` returns.
That is the whole point of C1: the server computes the figures once and
the screen and the PDF both render the same object. If this module
queried anything, it would be a second implementation of the same
arithmetic, and the two would disagree the first time either changed.

The signature enforces it - there is no Session parameter to misuse.

WHY SERVER-SIDE AND NOT BROWSER PRINT
-------------------------------------
Print-to-PDF would tie the document to whichever browser produced it,
its fonts and its zoom level, and it could never be produced by a
scheduled job. A report that a course coordinator receives should look
the same whoever generated it.

CAVEATS COME FIRST, BEFORE THE FIGURES
--------------------------------------
The qualifications are printed in a boxed panel at the top of page one,
above the numbers they qualify. Putting them in a footnote would mean a
reader reaches the risk figures first and the disclaimer afterwards, if
at all - which is the failure mode the caveats exist to prevent.
"""

from datetime import datetime
from io import BytesIO
from typing import Any, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# Palette lifted from the frontend's BUCKET_STYLES so a printed report and
# the screen do not colour the same tier differently.
TIER_COLOURS = {
    "high_risk": colors.HexColor("#DC2626"),
    "low_risk": colors.HexColor("#EA580C"),
    "safe": colors.HexColor("#16A34A"),
    "needs_review": colors.HexColor("#7C3AED"),
    "not_analysed": colors.HexColor("#78716C"),
}
TIER_TINTS = {
    "high_risk": colors.HexColor("#FEF2F2"),
    "low_risk": colors.HexColor("#FFF7ED"),
    "safe": colors.HexColor("#F0FDF4"),
    "needs_review": colors.HexColor("#FAF5FF"),
    "not_analysed": colors.HexColor("#FAFAF9"),
}

INK = colors.HexColor("#1C1917")
MUTED = colors.HexColor("#78716C")
RULE = colors.HexColor("#E7E5E4")
BAND = colors.HexColor("#F5F5F4")

#: Printed wherever a figure does not exist. NEVER "0" - a student with no
#: attendance record has not attended zero classes; nobody has measured
#: them, and a printed 0 is a claim the system cannot support.
MISSING = "—"

#: The unit each category's figures are actually in. Without this the
#: "Avg score" column silently mixes percentages with a login count, and
#: a reader comparing 59.2 against 11.8 concludes the wrong thing.
CATEGORY_UNITS = {
    "attendance": "%",
    "weekly_tut": "%",
    "assessment": "%",
    "moodle": " logins",
}

PAGE_MARGIN = 16 * mm


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "eg_title", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=17, leading=21, alignment=TA_LEFT, textColor=INK,
            spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "eg_subtitle", parent=base["Normal"], fontName="Helvetica",
            fontSize=9.5, leading=13, textColor=MUTED,
        ),
        "h2": ParagraphStyle(
            "eg_h2", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=11.5, leading=15, textColor=INK,
            spaceBefore=14, spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "eg_body", parent=base["Normal"], fontName="Helvetica",
            fontSize=9, leading=12.5, textColor=INK,
        ),
        "cell": ParagraphStyle(
            "eg_cell", parent=base["Normal"], fontName="Helvetica",
            fontSize=8, leading=10.5, textColor=INK,
        ),
        "cell_head": ParagraphStyle(
            "eg_cell_head", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=7.5, leading=10, textColor=colors.white,
        ),
        "caveat": ParagraphStyle(
            "eg_caveat", parent=base["Normal"], fontName="Helvetica",
            fontSize=8.5, leading=12, textColor=colors.HexColor("#7C2D12"),
            leftIndent=8, bulletIndent=0,
        ),
        "caveat_head": ParagraphStyle(
            "eg_caveat_head", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=9, leading=12, textColor=colors.HexColor("#9A3412"),
            spaceAfter=4,
        ),
        "note": ParagraphStyle(
            "eg_note", parent=base["Normal"], fontName="Helvetica-Oblique",
            fontSize=8, leading=11, textColor=MUTED,
        ),
    }


def _fmt(value: Optional[float], suffix: str = "") -> str:
    """A number, or the missing marker. Never silently zero."""
    if value is None:
        return MISSING
    text = f"{value:g}"
    return f"{text}{suffix}"


def _fmt_dt(value: Optional[datetime]) -> str:
    if value is None:
        return MISSING
    return value.strftime("%d %b %Y, %H:%M")


def _hex(colour: colors.Color) -> str:
    """`#rrggbb` for ReportLab's inline `<font color=...>` markup."""
    return "#" + colour.hexval()[2:]


def _escape(text: Any) -> str:
    """Paragraph content is mini-XML, so a student named `A & B` would
    otherwise abort the build."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


class _NumberedCanvas(pdfcanvas.Canvas):
    """
    Footer with "Page N of M".

    The total is unknowable while the first pass is still laying out, so
    pages are held and stamped at save time. Without this the footer can
    only say "Page N", and a reader of a printed copy cannot tell whether
    a page is missing - which for a document that gets forwarded and
    photocopied is worth the extra pass.
    """

    def __init__(self, *args, footer_note: str = "", **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_states: list[dict] = []
        self._footer_note = footer_note

    def showPage(self) -> None:  # noqa: N802 - ReportLab's casing
        self._saved_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        total = len(self._saved_states)
        for state in self._saved_states:
            self.__dict__.update(state)
            self._draw_footer(total)
            super().showPage()
        super().save()

    def _draw_footer(self, total: int) -> None:
        width, _ = A4
        self.setStrokeColor(RULE)
        self.setLineWidth(0.5)
        self.line(PAGE_MARGIN, 12 * mm, width - PAGE_MARGIN, 12 * mm)

        self.setFont("Helvetica", 7.5)
        self.setFillColor(MUTED)
        self.drawString(PAGE_MARGIN, 8 * mm, self._footer_note)
        self.drawRightString(
            width - PAGE_MARGIN, 8 * mm,
            f"Page {self._pageNumber} of {total}",
        )


# ---------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------

def _header(report: dict, style: dict) -> list:
    period = " ".join(
        part for part in [report.get("teaching_period") or "", str(report.get("year") or "")]
        if part
    ).strip()

    line2 = [f"Checkpoint: Week {report['checkpoint_week']}"]
    if period:
        line2.insert(0, period)
    if report.get("lecturer_name"):
        line2.append(f"Lecturer: {_escape(report['lecturer_name'])}")

    return [
        Paragraph(
            f"{_escape(report.get('full_code') or report['unit_code'])} "
            f"&mdash; {_escape(report['unit_name'])}",
            style["title"],
        ),
        Paragraph("Early-warning report", style["subtitle"]),
        Spacer(1, 3),
        Paragraph(" &nbsp;·&nbsp; ".join(line2), style["subtitle"]),
        Paragraph(
            f"Generated {_fmt_dt(report['generated_at'])} &nbsp;·&nbsp; "
            f"Analysis last run {_fmt_dt(report.get('last_analysed_at'))}",
            style["subtitle"],
        ),
        Spacer(1, 10),
    ]


def _caveats_panel(report: dict, style: dict, width: float) -> list:
    """
    The qualifications, boxed, above the figures.

    An empty list is itself worth printing: "no qualifications" is a
    statement about the data, and its absence would read as the section
    having been forgotten.
    """
    caveats = report.get("caveats") or []

    if not caveats:
        inner = [Paragraph(
            "No qualifications apply. Every enrolled student has been analysed "
            "on complete data and no engine disagreements are outstanding.",
            style["body"],
        )]
        border, background = colors.HexColor("#BBF7D0"), colors.HexColor("#F0FDF4")
    else:
        inner = [Paragraph("Read these before the figures", style["caveat_head"])]
        inner += [
            Paragraph(_escape(text), style["caveat"], bulletText="•")
            for text in caveats
        ]
        border, background = colors.HexColor("#FDBA74"), colors.HexColor("#FFF7ED")

    box = Table([[inner]], colWidths=[width])
    box.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.9, border),
        ("BACKGROUND", (0, 0), (-1, -1), background),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return [box, Spacer(1, 4)]


def _cohort_section(report: dict, style: dict, width: float) -> list:
    analysed = report["analysed_count"]

    headline = Table(
        [[
            Paragraph(f"<b>{report['enrolled_count']}</b><br/>Enrolled", style["cell"]),
            Paragraph(f"<b>{analysed}</b><br/>Analysed", style["cell"]),
            Paragraph(
                f"<b>{report['not_analysed_count']}</b><br/>Not analysed",
                style["cell"],
            ),
            Paragraph(f"<b>{len(report['at_risk'])}</b><br/>On the at-risk list",
                      style["cell"]),
        ]],
        colWidths=[width / 4.0] * 4,
    )
    headline.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BAND),
        ("BOX", (0, 0), (-1, -1), 0.5, RULE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, RULE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))

    rows = [[
        Paragraph("Risk tier", style["cell_head"]),
        Paragraph("Students", style["cell_head"]),
        Paragraph("% of analysed", style["cell_head"]),
    ]]
    body_style = [
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("GRID", (0, 0), (-1, -1), 0.4, RULE),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]

    for index, row in enumerate(report["distribution"], start=1):
        bucket = row["bucket"]
        rows.append([
            Paragraph(f"<b>{_escape(row['label'])}</b>", style["cell"]),
            Paragraph(str(row["count"]), style["cell"]),
            # A percentage of nothing is not 0% - it is undefined, and
            # printing 0.0% would read as "no students are at risk".
            Paragraph(
                f"{row['percent_of_analysed']:g}%" if analysed else MISSING,
                style["cell"],
            ),
        ])
        body_style.append(("BACKGROUND", (0, index), (-1, index), TIER_TINTS[bucket]))
        body_style.append(("LINEBEFORE", (0, index), (0, index), 2.4,
                           TIER_COLOURS[bucket]))

    table = Table(rows, colWidths=[width * 0.5, width * 0.25, width * 0.25],
                  repeatRows=1)
    table.setStyle(TableStyle(body_style))

    out = [Paragraph("Cohort summary", style["h2"]), headline, Spacer(1, 8), table]
    if not analysed:
        out.append(Spacer(1, 4))
        out.append(Paragraph(
            "No analysis has been run for this unit at this checkpoint. The "
            "figures above describe enrolment only; they are not evidence "
            "that no student is at risk.",
            style["note"],
        ))
    return out


def _criteria_section(report: dict, style: dict, width: float) -> list:
    criteria = report.get("criteria") or []
    out = [Paragraph("Criteria performance", style["h2"])]

    if not criteria:
        out.append(Paragraph(
            "No criteria on this unit have recorded data yet.", style["note"]))
        return out

    out.append(Paragraph(
        "Categories are not comparable raw &mdash; attendance is a percentage, "
        "Moodle is a login count, and assessment marks are shown as a "
        "percentage of each assessment's own maximum. Each student's value is "
        "divided by the threshold <i>they</i> were held to before averaging, "
        "so <b>100% means exactly at the bar</b>.",
        style["note"],
    ))
    out.append(Spacer(1, 6))

    heads = ["Category", "Cohort avg", "Threshold", "% of threshold",
             "Below bar", "Declining"]
    rows = [[Paragraph(h, style["cell_head"]) for h in heads]]

    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("GRID", (0, 0), (-1, -1), 0.4, RULE),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]

    for index, row in enumerate(criteria, start=1):
        percent = row["percent_of_threshold"]
        unit = CATEGORY_UNITS.get(row["category"], "")
        # Below the bar on average is the finding, so it is marked rather
        # than left for the reader to compare two columns.
        emphasis = "#B91C1C" if percent < 100 else "#166534"
        rows.append([
            Paragraph(f"<b>{_escape(row['label'])}</b><br/>"
                      f"<font size=6.5 color='#78716C'>"
                      f"{row['sample_size']} data point"
                      f"{'' if row['sample_size'] == 1 else 's'}</font>",
                      style["cell"]),
            # Both carry the unit, so the two columns are visibly on the
            # same scale and visibly not the same scale as the row above.
            Paragraph(_fmt(row["average_score"], unit), style["cell"]),
            Paragraph(_fmt(row["average_threshold"], unit), style["cell"]),
            Paragraph(f"<font color='{emphasis}'><b>{percent:g}%</b></font>",
                      style["cell"]),
            Paragraph(f"{row['below_threshold']} of {row['sample_size']}",
                      style["cell"]),
            # None is not zero here: assessments have no early/late window,
            # so "is anyone declining" is not a question that can be asked.
            Paragraph(
                MISSING if row.get("declining_count") is None
                else str(row["declining_count"]),
                style["cell"],
            ),
        ])
        if index % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, index), (-1, index), BAND))

    table = Table(
        rows,
        colWidths=[width * 0.26, width * 0.14, width * 0.16, width * 0.16,
                   width * 0.15, width * 0.13],
        repeatRows=1,
    )
    table.setStyle(TableStyle(style_cmds))
    out.append(table)
    return out


def _flags_of(row: dict) -> str:
    """The short provenance markers printed under a student's name."""
    flags = []
    if row.get("requires_review"):
        flags.append("awaiting review")
    if row.get("decided_by_lecturer"):
        reviewer = row.get("reviewer_name")
        flags.append(f"decided by {_escape(reviewer)}" if reviewer
                     else "decided by lecturer")
    if row.get("is_incomplete"):
        flags.append("incomplete data")
    if row.get("alerts_sent"):
        count = row["alerts_sent"]
        flags.append(f"{count} alert{'' if count == 1 else 's'} sent")
        # Printed only when it happened. A "0 confirmed" on every line
        # would put the same six characters beside every student in the
        # document and stop meaning anything by the third row; the
        # caveat on page 1 already covers the cohort-wide case.
        confirmed = row.get("alerts_acknowledged") or 0
        if confirmed:
            flags.append(f"{confirmed} confirmed received")
    return ", ".join(flags)


def _at_risk_section(report: dict, style: dict, width: float) -> list:
    at_risk = report.get("at_risk") or []
    out = [Paragraph("Students requiring attention", style["h2"])]

    if not at_risk:
        out.append(Paragraph(
            "No students are currently on the at-risk list for this "
            "checkpoint. Read this alongside the qualifications on page 1 "
            "&mdash; students who have never been analysed do not appear here.",
            style["note"],
        ))
        return out

    out.append(Paragraph(
        "Ordered worst first. Assessment figures are percentages of each "
        "assessment's own maximum mark, not raw marks. A dash means "
        "<b>not recorded</b>, which is not the same as zero.",
        style["note"],
    ))
    out.append(Spacer(1, 6))

    heads = ["Student", "Tier", "Attend.", "Tutorial", "Assess.", "Moodle"]
    rows = [[Paragraph(h, style["cell_head"]) for h in heads]]

    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("GRID", (0, 0), (-1, -1), 0.4, RULE),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]

    for index, row in enumerate(at_risk, start=1):
        bucket = row.get("risk_tier") or "needs_review"
        identity = (
            f"<b>{_escape(row['name'])}</b><br/>"
            f"<font size=6.5 color='#78716C'>{_escape(row['student_number'])}"
        )
        if row.get("email"):
            identity += f" &nbsp;·&nbsp; {_escape(row['email'])}"
        else:
            # Worth printing: no address means the alerts feature can never
            # reach this student, and they are on the at-risk list.
            identity += " &nbsp;·&nbsp; no email on record"
        flags = _flags_of(row)
        if flags:
            identity += f"<br/>{flags}"
        identity += "</font>"

        assessment = (
            f"{row['assessment_avg_pct']:g}%"
            if row.get("assessment_avg_pct") is not None else MISSING
        )
        assessment += (
            f"<br/><font size=6.5 color='#78716C'>"
            f"{row.get('assessments_marked', 0)} of "
            f"{row.get('assessments_total', 0)} marked</font>"
        )

        attendance = _fmt(row.get("attendance_pct"), "%")
        trend = row.get("attendance_trend")
        if trend is not None:
            arrow = "▼" if trend < 0 else "▲" if trend > 0 else "–"
            colour = "#B91C1C" if trend <= -10 else "#78716C"
            attendance += (
                f"<br/><font size=6.5 color='{colour}'>{arrow} {abs(trend):g} pp</font>"
            )

        rows.append([
            Paragraph(identity, style["cell"]),
            Paragraph(
                f"<font color='{_hex(TIER_COLOURS[bucket])}'>"
                f"<b>{_escape(row['risk_label'])}</b></font>",
                style["cell"],
            ),
            Paragraph(attendance, style["cell"]),
            Paragraph(_fmt(row.get("tutorial_pct"), "%"), style["cell"]),
            Paragraph(assessment, style["cell"]),
            Paragraph(_fmt(row.get("moodle_logins")), style["cell"]),
        ])
        style_cmds.append(("LINEBEFORE", (0, index), (0, index), 2.4,
                           TIER_COLOURS[bucket]))
        if index % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, index), (-1, index), BAND))

    table = Table(
        rows,
        colWidths=[width * 0.38, width * 0.13, width * 0.13, width * 0.12,
                   width * 0.13, width * 0.11],
        # Without this a cohort that spills onto page two loses its column
        # headings, and "55" in an unlabelled column means nothing.
        repeatRows=1,
    )
    table.setStyle(TableStyle(style_cmds))
    out.append(table)
    return out


def _intervention_section(report: dict, style: dict, width: float) -> list:
    data = report["intervention"]
    out = [Paragraph("Intervention record", style["h2"])]

    if not data.get("available"):
        # Zeros here would read as "nobody was contacted", which is a
        # different and much worse claim than "this is not installed".
        out.append(Paragraph(
            "The alerts feature is not installed on this deployment, so no "
            "contact history can be reported. <b>This is not evidence that no "
            "students were contacted.</b>",
            style["note"],
        ))
        pairs = [
            ("Engine disagreements resolved", data.get("reviews_resolved", 0)),
            ("Still awaiting a decision", data.get("reviews_pending", 0)),
        ]
    else:
        # THE NOTE CHANGES WITH WHAT THE DEPLOYMENT CAN ACTUALLY KNOW.
        # Before acknowledgment existed, this paragraph had to apologise
        # that "sent" is not a read receipt and leave it there. Where
        # receipts ARE recorded, the document can now draw the line
        # itself - and a reader forwarding this to a course coordinator
        # needs the distinction stated, not implied by two numbers
        # sitting next to each other.
        if data.get("acknowledgment_available"):
            out.append(Paragraph(
                "What was done, as distinct from what the engines found. "
                "&ldquo;Sent&rdquo; means the mail server accepted the message. "
                "&ldquo;Confirmed received&rdquo; means the student opened the "
                "link in it and said so &mdash; the only figure here that comes "
                "from the student rather than from this system.",
                style["note"],
            ))
        else:
            out.append(Paragraph(
                "What was done, as distinct from what the engines found. "
                "&ldquo;Sent&rdquo; means the mail server accepted the message; it "
                "is not a read receipt. Receipt confirmation is not recorded on "
                "this deployment.",
                style["note"],
            ))

        pairs = [
            ("Alerts sent", data.get("alerts_sent", 0)),
            ("Failed to send", data.get("alerts_failed", 0)),
            ("Still queued", data.get("alerts_queued", 0)),
            # Distinct students, not messages: one student can be emailed
            # more than once, and counting messages as people overstates reach.
            ("Distinct students contacted", data.get("students_contacted", 0)),
        ]

        if data.get("acknowledgment_available"):
            # Placed directly after the contact figures, because the
            # question the reader is holding at that point is "and did
            # any of that reach anyone".
            pairs += [
                ("Confirmed received", data.get("alerts_acknowledged", 0)),
                ("Students who confirmed", data.get("students_acknowledged", 0)),
            ]

        pairs += [
            ("Sent automatically", data.get("alerts_automatic", 0)),
            ("Sent manually", data.get("alerts_manual", 0)),
            ("Engine disagreements resolved", data.get("reviews_resolved", 0)),
            ("Still awaiting a decision", data.get("reviews_pending", 0)),
        ]

    out.append(Spacer(1, 6))

    cells = [
        Paragraph(f"<b>{value}</b><br/>"
                  f"<font size=6.5 color='#78716C'>{label}</font>", style["cell"])
        for label, value in pairs
    ]
    while len(cells) % 4:
        cells.append(Paragraph("", style["cell"]))

    grid = [cells[i:i + 4] for i in range(0, len(cells), 4)]
    table = Table(grid, colWidths=[width / 4.0] * 4)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, RULE),
        ("BACKGROUND", (0, 0), (-1, -1), BAND),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    out.append(table)
    return out


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------

def report_filename(report: dict) -> str:
    """A filename that stays meaningful in a downloads folder of thirty."""
    code = "".join(
        char for char in str(report.get("full_code") or report.get("unit_code") or "unit")
        if char.isalnum() or char in "-_"
    ) or "unit"
    stamp = report["generated_at"].strftime("%Y%m%d")
    return f"{code}_week{report['checkpoint_week']}_report_{stamp}.pdf"


def build_report_pdf(report: dict) -> bytes:
    """
    Render a report dict as PDF bytes.

    No Session parameter, deliberately: this renders what C1 computed and
    must not be able to compute anything itself.
    """
    style = _styles()
    buffer = BytesIO()

    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=PAGE_MARGIN, rightMargin=PAGE_MARGIN,
        topMargin=14 * mm, bottomMargin=18 * mm,
        title=f"{report.get('full_code') or report['unit_code']} early-warning report",
        author=report.get("lecturer_name") or "EduGuard",
        subject=f"Week {report['checkpoint_week']} checkpoint",
    )
    frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        doc.width, doc.height, id="body",
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
    )
    doc.addPageTemplates([PageTemplate(id="report", frames=[frame])])

    width = doc.width
    story: list = []
    story += _header(report, style)
    story += _caveats_panel(report, style, width)
    story += _cohort_section(report, style, width)
    story += _criteria_section(report, style, width)
    story += _at_risk_section(report, style, width)
    # Kept whole: a heading stranded at the foot of a page with its figures
    # overleaf is how a reader concludes the section is empty.
    story.append(KeepTogether(_intervention_section(report, style, width)))

    story.append(Spacer(1, 14))
    story.append(Paragraph(
        "This report contains identifiable student information and is intended "
        "for staff involved in supporting this cohort. Risk tiers are produced "
        "by automated analysis and, where marked, by a lecturer resolving a "
        "disagreement between the two engines. They are an indication for "
        "follow-up, not a determination about any student.",
        style["note"],
    ))

    footer = (
        f"{report.get('full_code') or report['unit_code']} · Week {report['checkpoint_week']} · "
        f"Generated {_fmt_dt(report['generated_at'])} · "
        f"EduGuard — confidential"
    )
    doc.build(
        story,
        canvasmaker=lambda *a, **kw: _NumberedCanvas(*a, footer_note=footer, **kw),
    )

    return buffer.getvalue()