"""Alerts API routes for reviewing, filtering, and acknowledging clinical events."""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from astra_med.db import crud
from astra_med.db.database import get_db
from astra_med.db.models import AlertRecord

router = APIRouter(prefix="/alerts", tags=["Alerts"])


class AlertRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    alert_uuid: str
    crew_id: int
    hazard: str
    severity: str
    functional_status: str
    timestamp_met: float
    metric_name: str
    observed_value: float
    baseline_mean: float
    baseline_std: float
    z_score: float
    direction: str
    summary_text: str
    action_card_id: Optional[str]
    acknowledged: bool


@router.get("", response_model=List[AlertRecordResponse])
def list_alerts(
    crew_id: Optional[int] = Query(None),
    severity: Optional[str] = Query(None),
    hazard: Optional[str] = Query(None),
    acknowledged: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    session: Session = Depends(get_db),
):
    alerts = crud.get_alerts(
        session=session,
        crew_id=crew_id,
        severity=severity,
        hazard=hazard,
        acknowledged=acknowledged,
        limit=limit,
    )
    return alerts


@router.get("/active", response_model=List[AlertRecordResponse])
def list_active_alerts(
    crew_id: Optional[int] = Query(None),
    session: Session = Depends(get_db),
):
    alerts = crud.get_active_alerts(session, crew_id=crew_id)
    return alerts


@router.put("/{alert_id}/acknowledge", response_model=AlertRecordResponse)
def acknowledge_alert(
    alert_id: int,
    session: Session = Depends(get_db),
):
    alert = crud.acknowledge_alert(session, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert with id {alert_id} not found")
    return alert


@router.get("/stats")
def get_alert_stats(
    session: Session = Depends(get_db),
):
    total = session.query(func.count(AlertRecord.id)).scalar() or 0
    active = session.query(func.count(AlertRecord.id)).filter(AlertRecord.acknowledged == False).scalar() or 0
    green = session.query(func.count(AlertRecord.id)).filter(AlertRecord.severity == "GREEN").scalar() or 0
    amber = session.query(func.count(AlertRecord.id)).filter(AlertRecord.severity == "AMBER").scalar() or 0
    red = session.query(func.count(AlertRecord.id)).filter(AlertRecord.severity == "RED").scalar() or 0

    return {
        "total_alerts": total,
        "active_unacknowledged": active,
        "by_severity": {
            "GREEN": green,
            "AMBER": amber,
            "RED": red,
        },
    }
