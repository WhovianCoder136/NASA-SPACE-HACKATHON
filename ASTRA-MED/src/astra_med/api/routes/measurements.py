"""API Routes for Unified Measurements (vitals, biosamples, sleep, biometrics)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from astra_med.api.deps import (
    get_action_card_registry,
    get_alert_engine,
    get_baseline_engine,
    get_db,
    get_insight_engine,
    get_store_forward_queue,
)
from astra_med.core.action_cards import ActionCardRegistry
from astra_med.core.alert_engine import AlertEngine
from astra_med.core.baseline import PersonalBaselineEngine
from astra_med.core.insight_engine import InsightEngine
from astra_med.core.store_forward import StoreAndForwardQueue
from astra_med.core.types import DeviationResult, HazardType
from astra_med.db import crud

router = APIRouter(prefix="/measurements", tags=["Unified Measurements"])


class MeasurementIngestRequest(BaseModel):
    astronaut_id: Optional[str] = None
    crew_id: Optional[int] = 1
    domain: str = "cardiovascular"  # cardiovascular, immune, metabolic, radiation, sleep, neuromuscular, sans
    metric_name: str
    value: float
    unit: str
    timestamp_met: Optional[float] = None
    sample_type: str = "continuous"
    sqi_score: float = Field(1.0, ge=0.0, le=1.0)
    flags: Dict[str, Any] = Field(default_factory=dict)


class MeasurementResponse(BaseModel):
    id: int
    crew_id: int
    metric_name: str
    value: float
    unit: str
    timestamp_met: float
    deviation: Optional[DeviationResult] = None
    alert_triggered: bool = False
    observation: Optional[str] = None


@router.post("", response_model=MeasurementResponse, status_code=status.HTTP_201_CREATED)
def ingest_measurement(
    req: MeasurementIngestRequest,
    session: Session = Depends(get_db),
    baseline_engine: PersonalBaselineEngine = Depends(get_baseline_engine),
    alert_engine: AlertEngine = Depends(get_alert_engine),
    insight_engine: InsightEngine = Depends(get_insight_engine),
    card_registry: ActionCardRegistry = Depends(get_action_card_registry),
    sf_queue: StoreAndForwardQueue = Depends(get_store_forward_queue),
):
    """Ingest a physiological measurement, update running baseline if nominal, and generate insight."""
    c_id = req.crew_id or 1
    if req.astronaut_id:
        if req.astronaut_id.isdigit():
            c_id = int(req.astronaut_id)
        elif req.astronaut_id.startswith("ASTRA-"):
            try:
                c_id = int(req.astronaut_id.split("-")[1])
            except Exception:
                c_id = 1

    crew = crud.get_crew_member(session, c_id)
    if not crew:
        # Fallback to first crew or create
        members = crud.list_crew_members(session)
        if members:
            c_id = members[0].id
        else:
            new_c = crud.create_crew_member(session, name="ASTRA Crew", role="Astronaut")
            c_id = new_c.id

    met = req.timestamp_met if req.timestamp_met is not None else 142.0

    reading = crud.create_vital_reading(
        session=session,
        crew_id=c_id,
        metric_name=req.metric_name,
        value=req.value,
        unit=req.unit,
        timestamp_met=met,
        sample_type=req.sample_type,
        sqi_score=req.sqi_score,
        sqi_valid=(req.sqi_score >= 0.5),
        flags=req.flags,
    )

    deviation = baseline_engine.evaluate(
        session=session,
        crew_id=c_id,
        metric_name=req.metric_name,
        value=req.value,
    )

    alert_triggered = False
    if deviation.is_significant:
        alert_triggered = True
        hazard_map = {
            "cardiovascular": HazardType.GRAVITY,
            "neuromuscular": HazardType.GRAVITY,
            "sans": HazardType.GRAVITY,
            "immune": HazardType.IMMUNE,
            "metabolic": HazardType.BIOSAMPLE,
            "radiation": HazardType.RADIATION,
            "sleep": HazardType.ISOLATION,
        }
        hazard = hazard_map.get(req.domain.lower(), HazardType.GRAVITY)
        severity = alert_engine.classify_severity(deviation)

        cards = card_registry.find_cards(hazard=hazard, severity=severity)
        matched_card_id = cards[0].card_id if cards else None

        alert_event = alert_engine.generate_alert(
            session=session,
            crew_id=c_id,
            hazard=hazard,
            deviation=deviation,
            timestamp_met=met,
            action_card_id=matched_card_id,
        )

        alert_rec = crud.get_alert_by_uuid(session, alert_event.alert_id)
        if alert_rec:
            sf_queue.enqueue(
                session=session,
                crew_id=c_id,
                alert_id=alert_rec.id,
                timestamp_met=met,
                action_card_id=matched_card_id,
                raw_digest=f"Metric: {req.metric_name}={req.value} {req.unit}, z={deviation.z_score}",
            )
    else:
        baseline_engine.update_baseline(
            session=session,
            crew_id=c_id,
            metric_name=req.metric_name,
            new_value=req.value,
            timestamp_met=met,
        )

    # Automatically generate structured insight via Insight Engine
    insight = insight_engine.evaluate_deviation(
        session=session,
        crew_id=c_id,
        module=req.domain,
        deviation=deviation,
    )
    session.commit()

    return MeasurementResponse(
        id=reading.id,
        crew_id=c_id,
        metric_name=reading.metric_name,
        value=reading.value,
        unit=reading.unit,
        timestamp_met=reading.timestamp_met,
        deviation=deviation,
        alert_triggered=alert_triggered,
        observation=insight.observation,
    )


@router.get("/{astronaut_id}")
def get_measurements(
    astronaut_id: str,
    metric_name: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_db),
):
    """Retrieve measurements for an astronaut."""
    if astronaut_id.isdigit():
        c_id = int(astronaut_id)
    elif astronaut_id.startswith("ASTRA-"):
        try:
            c_id = int(astronaut_id.split("-")[1])
        except Exception:
            c_id = 1
    else:
        c_id = 1

    readings = crud.get_vitals_for_crew(session=session, crew_id=c_id, metric_name=metric_name, limit=limit)
    return [
        {
            "id": r.id,
            "crew_id": r.crew_id,
            "metric_name": r.metric_name,
            "value": r.value,
            "unit": r.unit,
            "timestamp_met": r.timestamp_met,
            "sample_type": r.sample_type,
            "sqi_score": r.sqi_score,
        }
        for r in readings
    ]
