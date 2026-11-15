"""API Routes for Astronauts overview and profile tracking."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from astra_med.api.deps import get_db
from astra_med.db import crud

router = APIRouter(prefix="/astronauts", tags=["Astronaut Management"])


class AstronautResponse(BaseModel):
    id: int
    astronaut_id: str
    name: str
    role: str
    status: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class AstronautOverview(BaseModel):
    id: int
    astronaut_id: str
    name: str
    role: str
    status: str
    active_baselines_count: int
    active_alerts_count: int
    pending_actions_count: int
    recent_observations_count: int
    latest_vitals: List[Dict[str, Any]]
    recent_insights: List[Dict[str, Any]]
    active_alerts: List[Dict[str, Any]]


@router.get("", response_model=List[AstronautResponse])
def list_astronauts(session: Session = Depends(get_db)):
    """List all mission crew members."""
    crew = crud.list_crew_members(session)
    return [
        AstronautResponse(
            id=c.id,
            astronaut_id=f"ASTRA-{c.id:03d}",
            name=c.name,
            role=c.role,
            status=c.status,
            created_at=c.created_at.isoformat() if c.created_at else "",
        )
        for c in crew
    ]


@router.get("/{astronaut_id}/overview", response_model=AstronautOverview)
def get_astronaut_overview(astronaut_id: str, session: Session = Depends(get_db)):
    """Comprehensive single-pane health overview for an astronaut."""
    if astronaut_id.isdigit():
        c_id = int(astronaut_id)
    elif astronaut_id.startswith("ASTRA-"):
        try:
            c_id = int(astronaut_id.split("-")[1])
        except Exception:
            c_id = 1
    else:
        c_id = 1

    crew = crud.get_crew_member(session, c_id)
    if not crew:
        raise HTTPException(status_code=404, detail=f"Astronaut {astronaut_id} not found")

    baselines = crud.get_all_baselines_for_crew(session, c_id)
    latest_v = crud.get_latest_vitals(session, c_id)
    alerts = crud.get_active_alerts(session, crew_id=c_id)
    insights = crud.get_insights_for_crew(session, crew_id=c_id, limit=5)
    tasks = crud.list_action_tasks_for_crew(session, crew_id=c_id, status="pending")

    return AstronautOverview(
        id=crew.id,
        astronaut_id=f"ASTRA-{crew.id:03d}",
        name=crew.name,
        role=crew.role,
        status=crew.status,
        active_baselines_count=len(baselines),
        active_alerts_count=len(alerts),
        pending_actions_count=len(tasks),
        recent_observations_count=len(insights),
        latest_vitals=[
            {
                "metric_name": v.metric_name,
                "value": v.value,
                "unit": v.unit,
                "timestamp_met": v.timestamp_met,
            }
            for v in latest_v
        ],
        recent_insights=[
            {
                "id": i.id,
                "module": i.module,
                "observation": i.observation,
                "severity": i.severity,
                "created_at": i.created_at.isoformat() if i.created_at else "",
            }
            for i in insights
        ],
        active_alerts=[
            {
                "id": a.id,
                "alert_uuid": a.alert_uuid,
                "hazard": a.hazard,
                "severity": a.severity,
                "metric_name": a.metric_name,
                "observed_value": a.observed_value,
                "z_score": a.z_score,
                "summary_text": a.summary_text,
            }
            for a in alerts
        ],
    )
