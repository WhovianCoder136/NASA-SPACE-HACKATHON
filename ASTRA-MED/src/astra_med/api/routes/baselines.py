"""Personal Baselines API routes."""

from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from astra_med.api.deps import get_baseline_engine, get_db
from astra_med.core.baseline import PersonalBaselineEngine
from astra_med.db import crud

router = APIRouter(prefix="/baselines", tags=["Baselines"])


class BaselineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    crew_id: int
    metric_name: str
    mean: float
    std: float
    n_samples: int
    frozen: bool
    last_updated_met: float


@router.get("/{crew_id}", response_model=List[BaselineResponse])
def list_baselines_for_crew(
    crew_id: int,
    session: Session = Depends(get_db),
):
    baselines = crud.get_all_baselines_for_crew(session, crew_id)
    return baselines


@router.get("/{crew_id}/{metric_name}", response_model=BaselineResponse)
def get_specific_baseline(
    crew_id: int,
    metric_name: str,
    session: Session = Depends(get_db),
):
    baseline = crud.get_baseline(session, crew_id, metric_name)
    if not baseline:
        raise HTTPException(
            status_code=404,
            detail=f"Baseline for metric '{metric_name}' and crew member {crew_id} not found",
        )
    return baseline


@router.post("/{crew_id}/{metric_name}/freeze")
def freeze_baseline(
    crew_id: int,
    metric_name: str,
    session: Session = Depends(get_db),
    baseline_engine: PersonalBaselineEngine = Depends(get_baseline_engine),
):
    ok = baseline_engine.freeze(session, crew_id, metric_name)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail=f"Baseline for '{metric_name}' on crew {crew_id} does not exist",
        )
    return {"status": "frozen", "crew_id": crew_id, "metric_name": metric_name}


@router.post("/{crew_id}/{metric_name}/unfreeze")
def unfreeze_baseline(
    crew_id: int,
    metric_name: str,
    session: Session = Depends(get_db),
    baseline_engine: PersonalBaselineEngine = Depends(get_baseline_engine),
):
    ok = baseline_engine.unfreeze(session, crew_id, metric_name)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail=f"Baseline for '{metric_name}' on crew {crew_id} does not exist",
        )
    return {"status": "unfrozen", "crew_id": crew_id, "metric_name": metric_name}
