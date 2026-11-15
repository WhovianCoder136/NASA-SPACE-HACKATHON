"""API Routes for Insight Engine outputs."""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from astra_med.api.deps import get_db, get_insight_engine
from astra_med.core.insight_engine import InsightEngine
from astra_med.db import crud

router = APIRouter(prefix="/insights", tags=["Insight Engine"])


class InsightResponse(BaseModel):
    id: int
    subject_id: str
    crew_id: int
    module: str
    observation: str
    severity: str
    baseline_deviation_detected: bool
    diagnosis: Optional[str] = None
    requires_medical_review: bool
    metric_name: Optional[str] = None
    observed_value: Optional[float] = None
    baseline_mean: Optional[float] = None
    z_score: Optional[float] = None
    acknowledged: bool
    created_at: str

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=List[InsightResponse])
def list_insights(
    crew_id: Optional[int] = Query(None),
    severity: Optional[str] = Query(None),
    module: Optional[str] = Query(None),
    acknowledged: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_db),
):
    """Retrieve filtered observational insights across crew."""
    records = crud.list_insights(
        session=session,
        crew_id=crew_id,
        severity=severity,
        module=module,
        acknowledged=acknowledged,
        limit=limit,
    )
    return [
        InsightResponse(
            id=r.id,
            subject_id=r.subject_id,
            crew_id=r.crew_id,
            module=r.module,
            observation=r.observation,
            severity=r.severity,
            baseline_deviation_detected=r.baseline_deviation_detected,
            diagnosis=r.diagnosis,
            requires_medical_review=r.requires_medical_review,
            metric_name=r.metric_name,
            observed_value=r.observed_value,
            baseline_mean=r.baseline_mean,
            z_score=r.z_score,
            acknowledged=r.acknowledged,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in records
    ]


@router.get("/{astronaut_id}", response_model=List[InsightResponse])
def get_astronaut_insights(
    astronaut_id: str,
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_db),
):
    """Retrieve observations for a specific astronaut (by numeric id or ASTRA-xxx)."""
    if astronaut_id.isdigit():
        c_id = int(astronaut_id)
    elif astronaut_id.startswith("ASTRA-"):
        try:
            c_id = int(astronaut_id.split("-")[1])
        except Exception:
            c_id = 1
    else:
        c_id = 1

    records = crud.get_insights_for_crew(session=session, crew_id=c_id, limit=limit)
    return [
        InsightResponse(
            id=r.id,
            subject_id=r.subject_id,
            crew_id=r.crew_id,
            module=r.module,
            observation=r.observation,
            severity=r.severity,
            baseline_deviation_detected=r.baseline_deviation_detected,
            diagnosis=r.diagnosis,
            requires_medical_review=r.requires_medical_review,
            metric_name=r.metric_name,
            observed_value=r.observed_value,
            baseline_mean=r.baseline_mean,
            z_score=r.z_score,
            acknowledged=r.acknowledged,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in records
    ]


@router.put("/{insight_id}/acknowledge", response_model=InsightResponse)
def acknowledge_insight(
    insight_id: int,
    session: Session = Depends(get_db),
):
    """Acknowledge an insight."""
    rec = crud.acknowledge_insight(session, insight_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Insight not found")
    session.commit()
    return InsightResponse(
        id=rec.id,
        subject_id=rec.subject_id,
        crew_id=rec.crew_id,
        module=rec.module,
        observation=rec.observation,
        severity=rec.severity,
        baseline_deviation_detected=rec.baseline_deviation_detected,
        diagnosis=rec.diagnosis,
        requires_medical_review=rec.requires_medical_review,
        metric_name=rec.metric_name,
        observed_value=rec.observed_value,
        baseline_mean=rec.baseline_mean,
        z_score=rec.z_score,
        acknowledged=rec.acknowledged,
        created_at=rec.created_at.isoformat() if rec.created_at else "",
    )
