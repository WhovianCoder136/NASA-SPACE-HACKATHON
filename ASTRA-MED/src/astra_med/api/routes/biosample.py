"""BioSample Intelligence Engine ingestion endpoints for blood, urine, and saliva."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from astra_med.api.deps import (
    get_action_card_registry,
    get_alert_engine,
    get_baseline_engine,
    get_db,
    get_store_forward_queue,
)
from astra_med.api.routes.vitals import VitalIngestRequest, ingest_vital
from astra_med.core.action_cards import ActionCardRegistry
from astra_med.core.alert_engine import AlertEngine
from astra_med.core.baseline import PersonalBaselineEngine
from astra_med.core.store_forward import StoreAndForwardQueue

router = APIRouter(prefix="/biosample", tags=["BioSample Intelligence Engine"])


class BloodPanelRequest(BaseModel):
    crew_id: int
    timestamp_met: float
    wbc_count_k_ul: float = Field(..., description="White Blood Cell count (x10^3/uL)")
    neutrophil_pct: float = Field(..., description="Neutrophil differential %")
    lymphocyte_pct: float = Field(..., description="Lymphocyte differential %")
    platelets_k_ul: float = Field(..., description="Platelets (x10^3/uL)")
    il6_pg_ml: Optional[float] = None
    tnf_alpha_pg_ml: Optional[float] = None
    sqi_valid: bool = True
    sqi_score: float = 1.0


class UrinePanelRequest(BaseModel):
    crew_id: int
    timestamp_met: float
    specific_gravity: float = Field(..., description="Urine specific gravity (1.005 - 1.035)")
    ph: float = Field(..., description="Urine pH (4.5 - 8.0)")
    creatinine_mg_dl: float = Field(..., description="Urine creatinine (mg/dL)")
    calcium_mg_dl: Optional[float] = None
    osmolality_mosm_kg: Optional[float] = None
    sqi_valid: bool = True
    sqi_score: float = 1.0


class SalivaPanelRequest(BaseModel):
    crew_id: int
    timestamp_met: float
    cortisol_ug_dl: float = Field(..., description="Salivary free cortisol (ug/dL)")
    ebv_dna_copies_ml: Optional[float] = Field(None, description="EBV DNA viral copy number")
    vzv_dna_copies_ml: Optional[float] = Field(None, description="VZV DNA viral copy number")
    sqi_valid: bool = True
    sqi_score: float = 1.0


@router.post("/blood", status_code=status.HTTP_201_CREATED)
def ingest_blood_panel(
    req: BloodPanelRequest,
    session: Session = Depends(get_db),
    baseline_engine: PersonalBaselineEngine = Depends(get_baseline_engine),
    alert_engine: AlertEngine = Depends(get_alert_engine),
    card_registry: ActionCardRegistry = Depends(get_action_card_registry),
    sf_queue: StoreAndForwardQueue = Depends(get_store_forward_queue),
):
    measurements = [
        ("wbc_count", req.wbc_count_k_ul, "x10^3/uL", "hazard_5_hostile_closed_environments"),
        ("neutrophil_pct", req.neutrophil_pct, "%", "hazard_5_hostile_closed_environments"),
        ("lymphocyte_pct", req.lymphocyte_pct, "%", "hazard_5_hostile_closed_environments"),
        ("platelets", req.platelets_k_ul, "x10^3/uL", "hazard_5_hostile_closed_environments"),
    ]
    if req.il6_pg_ml is not None:
        measurements.append(("il6", req.il6_pg_ml, "pg/mL", "hazard_5_hostile_closed_environments"))
    if req.tnf_alpha_pg_ml is not None:
        measurements.append(("tnf_alpha", req.tnf_alpha_pg_ml, "pg/mL", "hazard_5_hostile_closed_environments"))

    results = []
    for metric, val, unit, hazard in measurements:
        r = ingest_vital(
            req=VitalIngestRequest(
                crew_id=req.crew_id,
                metric_name=metric,
                value=val,
                unit=unit,
                timestamp_met=req.timestamp_met,
                sample_type="blood",
                sqi_score=req.sqi_score,
                sqi_valid=req.sqi_valid,
                hazard=hazard,
            ),
            session=session,
            baseline_engine=baseline_engine,
            alert_engine=alert_engine,
            card_registry=card_registry,
            sf_queue=sf_queue,
        )
        results.append(r)

    return {"sample_type": "blood", "processed_analytes": len(results), "results": results}


@router.post("/urine", status_code=status.HTTP_201_CREATED)
def ingest_urine_panel(
    req: UrinePanelRequest,
    session: Session = Depends(get_db),
    baseline_engine: PersonalBaselineEngine = Depends(get_baseline_engine),
    alert_engine: AlertEngine = Depends(get_alert_engine),
    card_registry: ActionCardRegistry = Depends(get_action_card_registry),
    sf_queue: StoreAndForwardQueue = Depends(get_store_forward_queue),
):
    measurements = [
        ("urine_specific_gravity", req.specific_gravity, "ratio", "biosample_intelligence_engine"),
        ("urine_ph", req.ph, "pH", "biosample_intelligence_engine"),
        ("urine_creatinine", req.creatinine_mg_dl, "mg/dL", "biosample_intelligence_engine"),
    ]
    if req.calcium_mg_dl is not None:
        measurements.append(("urine_calcium", req.calcium_mg_dl, "mg/dL", "biosample_intelligence_engine"))
    if req.osmolality_mosm_kg is not None:
        measurements.append(("urine_osmolality", req.osmolality_mosm_kg, "mOsm/kg", "biosample_intelligence_engine"))

    results = []
    for metric, val, unit, hazard in measurements:
        r = ingest_vital(
            req=VitalIngestRequest(
                crew_id=req.crew_id,
                metric_name=metric,
                value=val,
                unit=unit,
                timestamp_met=req.timestamp_met,
                sample_type="urine",
                sqi_score=req.sqi_score,
                sqi_valid=req.sqi_valid,
                hazard=hazard,
            ),
            session=session,
            baseline_engine=baseline_engine,
            alert_engine=alert_engine,
            card_registry=card_registry,
            sf_queue=sf_queue,
        )
        results.append(r)

    return {"sample_type": "urine", "processed_analytes": len(results), "results": results}


@router.post("/saliva", status_code=status.HTTP_201_CREATED)
def ingest_saliva_panel(
    req: SalivaPanelRequest,
    session: Session = Depends(get_db),
    baseline_engine: PersonalBaselineEngine = Depends(get_baseline_engine),
    alert_engine: AlertEngine = Depends(get_alert_engine),
    card_registry: ActionCardRegistry = Depends(get_action_card_registry),
    sf_queue: StoreAndForwardQueue = Depends(get_store_forward_queue),
):
    measurements = [
        ("salivary_cortisol", req.cortisol_ug_dl, "ug/dL", "hazard_2_isolation_and_confinement"),
    ]
    if req.ebv_dna_copies_ml is not None:
        measurements.append(("saliva_ebv_dna", req.ebv_dna_copies_ml, "copies/mL", "hazard_5_hostile_closed_environments"))
    if req.vzv_dna_copies_ml is not None:
        measurements.append(("saliva_vzv_dna", req.vzv_dna_copies_ml, "copies/mL", "hazard_5_hostile_closed_environments"))

    results = []
    for metric, val, unit, hazard in measurements:
        r = ingest_vital(
            req=VitalIngestRequest(
                crew_id=req.crew_id,
                metric_name=metric,
                value=val,
                unit=unit,
                timestamp_met=req.timestamp_met,
                sample_type="saliva",
                sqi_score=req.sqi_score,
                sqi_valid=req.sqi_valid,
                hazard=hazard,
            ),
            session=session,
            baseline_engine=baseline_engine,
            alert_engine=alert_engine,
            card_registry=card_registry,
            sf_queue=sf_queue,
        )
        results.append(r)

    return {"sample_type": "saliva", "processed_analytes": len(results), "results": results}
