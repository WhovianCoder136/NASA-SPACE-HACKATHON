"""ML Inference endpoints for the 6 ASTRA-MED prediction modules."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from astra_med.api.deps import get_db, get_insight_engine, get_ml_router
from astra_med.core.insight_engine import InsightEngine
from astra_med.db import crud
from astra_med.ml.router import MLRouter

router = APIRouter(prefix="", tags=["Machine Learning Inference"])


class MLPredictRequest(BaseModel):
    crew_id: Optional[int] = 1
    input_data: Dict[str, Any]
    timestamp_met: float = 0.0


class MLPredictResponse(BaseModel):
    module_name: str
    risk_label: str
    risk_score: float
    confidence: float
    details: Dict[str, Any]
    observation: Optional[str] = None


@router.post("/ml/{module_name}/predict", response_model=MLPredictResponse)
@router.post("/predictions/{module_name}", response_model=MLPredictResponse)
def predict_module(
    module_name: str,
    req: MLPredictRequest,
    session: Session = Depends(get_db),
    ml_router: MLRouter = Depends(get_ml_router),
    insight_engine: InsightEngine = Depends(get_insight_engine),
):
    try:
        prediction = ml_router.predict(module_name, req.input_data)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Module '{module_name}' is not recognized. Available: {ml_router.module_names}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error in '{module_name}': {str(e)}")

    observation_text = None
    c_id = req.crew_id if req.crew_id is not None else 1

    crud.create_ml_prediction(
        session=session,
        crew_id=c_id,
        module_name=module_name,
        input_summary=str(list(req.input_data.keys())),
        prediction=prediction,
        confidence=prediction.get("confidence", 0.0),
        timestamp_met=req.timestamp_met,
    )

    # Automatically transform prediction into structured insight
    insight = insight_engine.evaluate_ml_prediction(
        session=session,
        crew_id=c_id,
        module=module_name,
        prediction=prediction,
    )
    observation_text = insight.observation
    session.commit()

    return MLPredictResponse(
        module_name=module_name,
        risk_label=prediction.get("risk_label", "Unknown"),
        risk_score=prediction.get("risk_score", 0.0),
        confidence=prediction.get("confidence", 0.0),
        details=prediction.get("details", {}),
        observation=observation_text,
    )


@router.get("/ml/health", response_model=List[Dict[str, Any]])
def check_all_modules_health(
    ml_router: MLRouter = Depends(get_ml_router),
):
    return ml_router.health_check_all()


@router.get("/ml/{module_name}/health", response_model=Dict[str, Any])
def check_module_health(
    module_name: str,
    ml_router: MLRouter = Depends(get_ml_router),
):
    try:
        return ml_router.health_check(module_name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Module '{module_name}' not found")
