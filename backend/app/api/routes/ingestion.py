"""
Lecturer-facing ingestion routes: bulk CSV/Excel upload and manual
single-student entry, both scoped to a specific unit.

A lecturer may only ingest data into units they are assigned to
(unit.lecturer_id == current_user.id) - checked explicitly here, since
require_role only confirms "this user IS a lecturer," not "this
lecturer owns THIS unit."
"""

import io
import math
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.database import get_db
from app.models.enums import UserRole
from app.models.unit import Unit
from app.models.user import User
from app.schemas.ingestion import (
    BulkIngestionMapping,
    BulkIngestionResult,
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
    pandas represents a blank cell as NaN (a real float), and assigning
    None back into a numeric-dtype column silently reverts to NaN - so
    df.where(pd.notnull(df), None) alone does NOT reliably clear blanks
    in numeric columns. pd.isna() catches both NaN and None regardless
    of dtype, so sanitizing per-cell after to_dict() is the only
    reliable place to do this.

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


# -------------------------
# BULK UPLOAD
# -------------------------
@router.post("/bulk", response_model=BulkIngestionResult, status_code=status.HTTP_201_CREATED)
async def bulk_ingest(
    unit_id: int,
    file: UploadFile = File(...),
    mapping: str = Form(..., description="BulkIngestionMapping as a JSON string"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.LECTURER)),
):
    unit = _get_unit_or_404(db, unit_id)
    _require_assigned_lecturer(unit, current_user)

    try:
        mapping_data = BulkIngestionMapping.model_validate_json(mapping)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid mapping JSON: {e}")

    filename = file.filename or "upload"
    contents = await file.read()

    try:
        if filename.lower().endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents))
        elif filename.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be .csv, .xlsx, or .xls")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not parse file: {e}")

    # Sanitize AFTER to_dict(), per-cell, using pd.isna-equivalent logic -
    # this is the only point that reliably catches NaN regardless of the
    # column's dtype. See _sanitize_row/_sanitize_cell docstring above.
    raw_rows = df.to_dict(orient="records")
    rows = [_sanitize_row(r) for r in raw_rows]

    try:
        batch, errors, warnings = ingestion_service.process_bulk_upload(
            db=db,
            unit_id=unit_id,
            lecturer_id=current_user.id,
            filename=filename,
            rows=rows,
            student_number_col=mapping_data.student_number_col,
            name_col=mapping_data.name_col,
            email_col=mapping_data.email_col,
            program_col=mapping_data.program_col,
            criteria_column_map=mapping_data.criteria_column_map,
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
    )


# -------------------------
# MANUAL ENTRY
# -------------------------
@router.post("/manual", response_model=ManualEntryResult, status_code=status.HTTP_201_CREATED)
def manual_ingest(
    unit_id: int,
    payload: ManualEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.LECTURER)),
):
    unit = _get_unit_or_404(db, unit_id)
    _require_assigned_lecturer(unit, current_user)

    try:
        events, errors, warnings = ingestion_service.process_manual_entry(
            db=db,
            unit_id=unit_id,
            lecturer_id=current_user.id,
            student_number=payload.student_number,
            name=payload.name,
            email=payload.email,
            program=payload.program,
            scores=payload.scores,
        )
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
    )