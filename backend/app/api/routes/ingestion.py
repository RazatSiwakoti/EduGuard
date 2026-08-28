"""
Lecturer-facing ingestion routes: bulk CSV/Excel upload and manual
single-student entry, both scoped to a specific unit.

A lecturer may only ingest data into units they are assigned to
(unit.lecturer_id == current_user.id) - checked explicitly here, since
require_role only confirms "this user IS a lecturer," not "this
lecturer owns THIS unit."
"""

import io
import json
import math
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from app.services.analysis_service import run_analysis_for_students, run_analysis_for_student
from app.core.dependencies import require_teaching_role
from app.database import get_db
from app.models.unit import Unit
from app.models.user import User
from app.schemas.ingestion import (
    BulkIngestionMapping,
    BulkIngestionResult,
    FilePreviewResult,
    IngestionRowError,
    IngestionRowWarning,
    ManualEntryCreate,
    ManualEntryResult,
)
from app.services import ingestion_service

router = APIRouter(prefix="/units/{unit_id}/ingest", tags=["Ingestion"])


def _get_unit_or_404(db: Session, unit_id: int) -> Unit:
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")
    return unit


def _require_assigned_lecturer(unit: Unit, current_user: User) -> None:
    if unit.lecturer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the assigned lecturer for this unit",
        )


def _sanitize_cell(value):
    """
    pandas represents a blank cell as NaN (a real float), and assigning none back into a numeric-dtype column silently reverts to NaN - so
    df.where(pd.notnull(df), None) alone does NOT reliably clear blanks in numeric columns. pd.isna() catches both NaN and None regardless
    of dtype, so sanitizing per-cell after to_dict() is the only reliable place to do this.

    Without this, a blank numeric cell reaches validate_score() as a
    real NaN float - and since every comparison against NaN evaluates
    to False (score < 0 and score > max_score both silently pass), it
    would slip through range validation and get stored as garbage data.
    """
    if value is None:
        return None
    try:
        if isinstance(value, float) and math.isnan(value):
            return None
    except TypeError:
        pass
    return value


def _sanitize_row(row: dict) -> dict:
    return {key: _sanitize_cell(val) for key, val in row.items()}


def _parse_upload(filename: str, contents: bytes) -> pd.DataFrame:
    """
    Turns an uploaded .csv/.xlsx/.xls into a DataFrame.

    Extracted so /preview and /bulk parse identically. If these two ever
    drifted apart, a lecturer could map columns off a preview that the
    real upload then reads differently - which would fail in the most
    confusing way possible, silently and only for some files.
    """
    try:
        if filename.lower().endswith(".csv"):
            return pd.read_csv(io.BytesIO(contents))
        if filename.lower().endswith((".xlsx", ".xls")):
            return pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not parse file: {e}",
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="File must be .csv, .xlsx, or .xls",
    )


# -------------------------
# FILE PREVIEW
# -------------------------

@router.post("/preview", response_model=FilePreviewResult)
async def preview_upload(
    unit_id: int,
    file: UploadFile = File(...),
    sample_size: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teaching_role()),
):
    """
    Reads an uploaded file and reports its column headers plus a few
    sample rows, WITHOUT storing anything.

    This is step one of the import wizard: a lecturer cannot map columns
    to criteria until they can see what columns their file actually has.
    Because /bulk needs the mapping and the file together in one
    request, that mapping has to be built beforehand - which is what
    this endpoint makes possible.

    Same lecturer-owns-this-unit check as every other route here: a
    preview reveals real student data from the file, so it is gated
    exactly as tightly as the upload itself.
    """
    unit = _get_unit_or_404(db, unit_id)
    _require_assigned_lecturer(unit, current_user)

    filename = file.filename or "upload"
    contents = await file.read()
    df = _parse_upload(filename, contents)

    # Hard cap regardless of what the client asks for - a preview only
    # needs to prove the file parsed correctly.
    capped = max(1, min(sample_size, 20))

    # Round-tripped through pandas' own JSON writer rather than
    # to_dict(). to_dict can hand back numpy scalars (int64, bool_) and
    # Timestamps depending on the pandas version and column dtype, and
    # FastAPI cannot serialise those - it raises "Object of type int64
    # is not JSON serializable" only for certain files, which is a
    # miserable bug to chase. to_json handles every numpy type and turns
    # NaN into null in one step.
    sample = json.loads(df.head(capped).to_json(orient="records"))

    return FilePreviewResult(
        filename=filename,
        # Cast to str: pandas infers a numeric column header (e.g. a
        # file whose headers are years) as int64, which is not a valid
        # str for the response model and would fail validation.
        columns=[str(c) for c in df.columns],
        total_rows=len(df.index),
        sample_rows=sample,
    )


# -------------------------
# BULK UPLOAD
# -------------------------

@router.post("/bulk", response_model=BulkIngestionResult, status_code=status.HTTP_201_CREATED)
async def bulk_ingest(
    unit_id: int,
    file: UploadFile = File(...),
    mapping: str = Form(..., description="BulkIngestionMapping as a JSON string"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teaching_role()),
):
    unit = _get_unit_or_404(db, unit_id)
    _require_assigned_lecturer(unit, current_user)

    try:
        mapping_data = BulkIngestionMapping.model_validate_json(mapping)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid mapping JSON: {e}")

    filename = file.filename or "upload"
    contents = await file.read()

    # Shared with /preview so a mapping built against the preview can
    # never be applied to a differently-parsed file.
    df = _parse_upload(filename, contents)

    raw_rows = df.to_dict(orient="records")
    rows = [_sanitize_row(r) for r in raw_rows]

    try:
        batch, errors, warnings, touched_student_ids = ingestion_service.process_bulk_upload(
            db=db,
            unit_id=unit_id,
            lecturer_id=current_user.id,
            filename=filename,
            rows=rows,
            student_number_col=mapping_data.student_number_col,
            name_col=mapping_data.name_col,
            email_col=mapping_data.email_col,
            program_col=mapping_data.program_col,
            # BUGFIX: these two were accepted by BulkIngestionMapping and
            # supported by process_bulk_upload, but never passed through -
            # so every bulk upload silently discarded gender and age.
            # Both are real ML features on Student, and manual entry has
            # always stored them, so bulk-uploaded students were being
            # scored on strictly less information than manually entered
            # ones without anything reporting it.
            gender_col=mapping_data.gender_col,
            age_col=mapping_data.age_col,
            criteria_column_map=mapping_data.criteria_column_map,
            weekly_criteria_column_map=mapping_data.weekly_criteria_column_map,
        )

        analysis_summary = None
        if touched_student_ids:
            analysis_summary = run_analysis_for_students(
                db, unit_id, list(touched_student_ids), checkpoint_week=8
            )

        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ingestion failed")

    db.refresh(batch)
    rows_with_errors = len({e["row"] for e in errors if e.get("row") is not None})
    return BulkIngestionResult(
        batch_id=batch.id,
        filename=batch.filename,
        total_rows=batch.total_rows,
        rows_with_errors=rows_with_errors,
        values_stored=batch.values_stored,
        values_failed=batch.values_failed,
        errors=[IngestionRowError(**e) for e in errors],
        warnings=[IngestionRowWarning(**w) for w in warnings],
        analysis_summary=analysis_summary,
    )


@router.post("/manual", response_model=ManualEntryResult, status_code=status.HTTP_201_CREATED)
def manual_ingest(
    unit_id: int,
    payload: ManualEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teaching_role()),
):
    unit = _get_unit_or_404(db, unit_id)
    _require_assigned_lecturer(unit, current_user)

    try:
        (
            events,
            errors,
            warnings,
            student_created,
            enrollment_created
        ) = ingestion_service.process_manual_entry(
            db=db,
            unit_id=unit_id,
            lecturer_id=current_user.id,
            student_number=payload.student_number,
            name=payload.name,
            email=payload.email,
            program=payload.program,
            gender=payload.gender,
            age=payload.age,
            scores=payload.scores,
            weekly_scores=payload.weekly_scores,
        )

        analysis_result = None
        if events:
            student_id = events[0].student_id
            analysis_result = run_analysis_for_student(db, student_id, unit_id, checkpoint_week=8)

        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ingestion failed")

    return ManualEntryResult(
        student_number=payload.student_number,
        events_created=len(events),
        errors=[IngestionRowError(**e) for e in errors],
        warnings=[IngestionRowWarning(**w) for w in warnings],
        analysis_result=analysis_result,
        student_created=student_created,
        enrollment_created=enrollment_created,
    )