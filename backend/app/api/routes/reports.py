"""
Lecturer reports API - Phase 7.9 / section C1.

ONE ENDPOINT, ONE FINISHED DOCUMENT
-----------------------------------
This router deliberately exposes a single read. The whole point of the
report is that the numbers are computed once, server-side, so that the
on-screen view (section C3) and the generated PDF (section C2) cannot
disagree. Splitting it into `/distribution`, `/criteria`, `/at-risk`
would hand the caller three payloads to stitch together and reopen
exactly the divergence the design is trying to close.

TENANT ISOLATION
----------------
`unit_id` arrives in the URL and is therefore attacker-controlled. The
service resolves the unit by (unit_id, lecturer_id from the validated
JWT) in SQL, so a lecturer asking for someone else's unit gets nothing
back - and this router turns "nothing" into 404, never 403, matching
the rest of the lecturer surface. A 403 would confirm the unit exists.

A report is a document about a whole cohort: names, email addresses,
risk tiers and contact history. Leaking one is worse than leaking a
single dashboard row, which is why ownership is enforced in the query
rather than checked afterwards.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.reports import ReportResponse
from app.services.report_pdf import build_report_pdf, report_filename
from app.services.report_service import DEFAULT_CHECKPOINT_WEEK, build_unit_report

router = APIRouter(
    prefix="/lecturer/reports",
    tags=["Lecturer - Reports"],
    dependencies=[Depends(require_role(UserRole.LECTURER))],
)


@router.get("/unit/{unit_id}", response_model=ReportResponse)
def get_unit_report(
    unit_id: int = Path(..., ge=1, description="Unit the report is about."),
    checkpoint_week: Optional[int] = Query(
        None,
        ge=1,
        le=52,
        description=(
            "Teaching week the report is a snapshot of. Only labels the "
            "document and splits the attendance trend into an early and a "
            "late window - it does not filter the underlying data, because "
            "the engines score the whole semester to date."
        ),
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.LECTURER)),
) -> ReportResponse:
    """
    The complete report for one unit at one checkpoint.

    Returns 404 when the unit does not exist OR is taught by somebody
    else - the two are deliberately indistinguishable from outside.
    """
    report = build_unit_report(
        db,
        lecturer_id=current_user.id,
        unit_id=unit_id,
        checkpoint_week=checkpoint_week or DEFAULT_CHECKPOINT_WEEK,
    )

    if report is None:
        raise HTTPException(status_code=404, detail="Unit not found")

    return ReportResponse(**report)


@router.get(
    "/unit/{unit_id}/pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
def download_unit_report(
    unit_id: int = Path(..., ge=1, description="Unit the report is about."),
    checkpoint_week: Optional[int] = Query(None, ge=1, le=52),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.LECTURER)),
) -> Response:
    """
    The same report, as a downloadable PDF.

    Deliberately built from `build_unit_report` rather than from anything
    the browser sends. A PDF assembled from a client-supplied payload
    would let a caller print any figures they liked under this unit's
    letterhead - and the document is designed to be forwarded to a course
    coordinator who has no way to check it.

    It also means the screen and the PDF are the same numbers by
    construction, not by two implementations agreeing.
    """
    report = build_unit_report(
        db,
        lecturer_id=current_user.id,
        unit_id=unit_id,
        checkpoint_week=checkpoint_week or DEFAULT_CHECKPOINT_WEEK,
    )

    if report is None:
        raise HTTPException(status_code=404, detail="Unit not found")

    pdf = build_report_pdf(report)

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            # `attachment` rather than `inline`: this is a record to be
            # filed, and a tab that renders it is easy to lose.
            "Content-Disposition":
                f'attachment; filename="{report_filename(report)}"',
            # The figures change whenever an analysis runs. A cached copy
            # of last week's risk tiers is worse than a slow download.
            "Cache-Control": "no-store",
        },
    )