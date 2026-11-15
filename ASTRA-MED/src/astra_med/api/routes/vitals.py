"""Vitals telemetry ingestion and personal-baseline deviation detection."""

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
    get_store_forward_queue,
)
from astra_med.core.action_cards import ActionCardRegistry
from astra_med.core.alert_engine import AlertEngine
from astra_med.core.baseline import PersonalBaselineEngine
from astra_med.core.store_forward import StoreAndForwardQueue
from astra_med.core.types import DeviationResult, HazardType, SeverityTier
from astra_med.db import crud

router = APIRouter(prefix="/vitals", tags=["Vitals & Telemetry"])


class VitalIngestRequest(BaseModel):
    crew_id: int
    metric_name: str
    value: float
    unit: str
    timestamp_met: float
    sample_type: str = "continuous"
    sqi_score: float = Field(1.0, ge=0.0, le=1.0)
    sqi_valid: bool = True
    flags: Dict[str, Any] = Field(default_factory=dict)
    hazard: Optional[str] = None


class VitalIngestResponse(BaseModel):
    reading_id: int
    crew_id: int
    metric_name: str
    value: float
    deviation: DeviationResult
    alert_triggered: bool = False
    alert_id: Optional[str] = None
    severity: Optional[str] = None
    action_card_id: Optional[str] = None
    action_card: Optional[dict] = None


def _infer_hazard(metric_name: str, explicit_hazard: Optional[str] = None) -> HazardType:
    if explicit_hazard:
        try:
            return HazardType(explicit_hazard)
        except ValueError:
            pass

    metric = metric_name.lower()
    if any(k in metric for k in ["heart_rate", "bp", "blood_pressure", "ecg", "hrv", "orthostatic"]):
        return HazardType.GRAVITY
    elif any(k in metric for k in ["wbc", "lymphocyte", "cytokine", "il6", "tnf", "viral", "ebv"]):
        return HazardType.IMMUNE
    elif any(k in metric for k in ["radiation", "dose", "h2ax", "spe"]):
        return HazardType.RADIATION
    elif any(k in metric for k in ["sleep", "pvt", "cognitive", "reaction", "fatigue"]):
        return HazardType.ISOLATION
    elif any(k in metric for k in ["urine", "glucose", "creatinine", "saliva", "cortisol"]):
        return HazardType.BIOSAMPLE
    return HazardType.GRAVITY


@router.post("/ingest", response_model=VitalIngestResponse, status_code=status.HTTP_201_CREATED)
def ingest_vital(
    req: VitalIngestRequest,
    session: Session = Depends(get_db),
    baseline_engine: PersonalBaselineEngine = Depends(get_baseline_engine),
    alert_engine: AlertEngine = Depends(get_alert_engine),
    card_registry: ActionCardRegistry = Depends(get_action_card_registry),
    sf_queue: StoreAndForwardQueue = Depends(get_store_forward_queue),
):
    crew = crud.get_crew_member(session, req.crew_id)
    if not crew:
        raise HTTPException(status_code=404, detail=f"Crew member {req.crew_id} does not exist")

    reading = crud.create_vital_reading(
        session=session,
        crew_id=req.crew_id,
        metric_name=req.metric_name,
        value=req.value,
        unit=req.unit,
        timestamp_met=req.timestamp_met,
        sample_type=req.sample_type,
        sqi_score=req.sqi_score,
        sqi_valid=req.sqi_valid,
        flags=req.flags,
    )

    # Signal Quality Index validation
    if not req.sqi_valid or req.sqi_score < 0.5:
        deviation = DeviationResult(
            metric_name=req.metric_name,
            observed_value=req.value,
            baseline_mean=req.value,
            baseline_std=1.0,
            z_score=0.0,
            direction="nominal",
            is_significant=False,
        )
        return VitalIngestResponse(
            reading_id=reading.id,
            crew_id=req.crew_id,
            metric_name=req.metric_name,
            value=req.value,
            deviation=deviation,
            alert_triggered=False,
        )

    # Evaluate against individual baseline
    deviation = baseline_engine.evaluate(
        session=session,
        crew_id=req.crew_id,
        metric_name=req.metric_name,
        value=req.value,
    )

    alert_triggered = False
    alert_id = None
    severity_val = None
    matched_card_id = None
    matched_card_dict = None

    if deviation.is_significant:
        alert_triggered = True
        hazard = _infer_hazard(req.metric_name, req.hazard)
        severity = alert_engine.classify_severity(deviation)
        severity_val = severity.value

        candidate_cards = card_registry.find_cards(hazard=hazard, severity=severity)
        if not candidate_cards:
            candidate_cards = card_registry.find_cards(severity=severity)

        if candidate_cards:
            matched_card = candidate_cards[0]
            matched_card_id = matched_card.card_id
            matched_card_dict = matched_card.model_dump()

        alert_event = alert_engine.generate_alert(
            session=session,
            crew_id=req.crew_id,
            hazard=hazard,
            deviation=deviation,
            timestamp_met=req.timestamp_met,
            action_card_id=matched_card_id,
        )
        alert_id = alert_event.alert_id

        alert_rec = crud.get_alert_by_uuid(session, alert_id)
        if alert_rec:
            sf_queue.enqueue(
                session=session,
                crew_id=req.crew_id,
                alert_id=alert_rec.id,
                timestamp_met=req.timestamp_met,
                action_card_id=matched_card_id,
                raw_digest=f"Metric: {req.metric_name}={req.value} {req.unit}, z={deviation.z_score}",
            )
    else:
        # Nominal: update running personal baseline (Constraint #7: only updates during nominal state)
        baseline_engine.update_baseline(
            session=session,
            crew_id=req.crew_id,
            metric_name=req.metric_name,
            new_value=req.value,
            timestamp_met=req.timestamp_met,
        )

    return VitalIngestResponse(
        reading_id=reading.id,
        crew_id=req.crew_id,
        metric_name=req.metric_name,
        value=req.value,
        deviation=deviation,
        alert_triggered=alert_triggered,
        alert_id=alert_id,
        severity=severity_val,
        action_card_id=matched_card_id,
        action_card=matched_card_dict,
    )


@router.post("/batch", status_code=status.HTTP_201_CREATED)
def ingest_batch(
    readings: List[VitalIngestRequest],
    session: Session = Depends(get_db),
    baseline_engine: PersonalBaselineEngine = Depends(get_baseline_engine),
    alert_engine: AlertEngine = Depends(get_alert_engine),
    card_registry: ActionCardRegistry = Depends(get_action_card_registry),
    sf_queue: StoreAndForwardQueue = Depends(get_store_forward_queue),
):
    results = []
    for req in readings:
        res = ingest_vital(
            req=req,
            session=session,
            baseline_engine=baseline_engine,
            alert_engine=alert_engine,
            card_registry=card_registry,
            sf_queue=sf_queue,
        )
        results.append(res)
    return {"ingested_count": len(results), "results": results}


@router.get("/{crew_id}")
def get_crew_vitals(
    crew_id: int,
    metric_name: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    session: Session = Depends(get_db),
):
    vitals = crud.get_vitals_for_crew(session, crew_id, metric_name=metric_name, limit=limit)
    return [
        {
            "id": v.id,
            "crew_id": v.crew_id,
            "metric_name": v.metric_name,
            "value": v.value,
            "unit": v.unit,
            "timestamp_met": v.timestamp_met,
            "sample_type": v.sample_type,
            "sqi_score": v.sqi_score,
            "sqi_valid": v.sqi_valid,
        }
        for v in vitals
    ]


@router.get("/{crew_id}/latest")
def get_latest_crew_vitals(
    crew_id: int,
    session: Session = Depends(get_db),
):
    vitals = crud.get_latest_vitals(session, crew_id)
    return [
        {
            "metric_name": v.metric_name,
            "value": v.value,
            "unit": v.unit,
            "timestamp_met": v.timestamp_met,
            "sqi_score": v.sqi_score,
            "sqi_valid": v.sqi_valid,
        }
        for v in vitals
    ]
