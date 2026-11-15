from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from astra_med.api.deps import get_db, get_insight_engine, get_ml_router
from astra_med.core.insight_engine import InsightEngine
from astra_med.db import crud
from astra_med.ml.router import MLRouter

router = APIRouter(prefix="", tags=["Machine Learning Inference"])

MAX_UPLOAD_BYTES = 100 * 1024 * 1024
ALLOWED_EXTENSIONS = {
    "cardiovascular": {".csv"},
    "immune": {".csv"},
    "metabolic": {".csv"},
    "radiation": {".csv"},
    "sleep": {".csv"},
    "neuromuscular": {".csv"},
    "sans": {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"},
}


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


def _save_prediction(session, insight_engine, crew_id, module_name, prediction, summary, timestamp_met):
    crud.create_ml_prediction(
        session=session,
        crew_id=crew_id,
        module_name=module_name,
        input_summary=summary,
        prediction=prediction,
        confidence=prediction.get("confidence", 0.0),
        timestamp_met=timestamp_met,
    )
    insight = insight_engine.evaluate_ml_prediction(
        session=session,
        crew_id=crew_id,
        module=module_name,
        prediction=prediction,
    )
    session.commit()
    return insight.observation


def _response(module_name, prediction, observation):
    return MLPredictResponse(
        module_name=module_name,
        risk_label=prediction.get("risk_label", "Unknown"),
        risk_score=prediction.get("risk_score", 0.0),
        confidence=prediction.get("confidence", 0.0),
        details=prediction.get("details", {}),
        observation=observation,
    )


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
        crew_id = req.crew_id if req.crew_id is not None else 1
        observation = _save_prediction(
            session, insight_engine, crew_id, module_name, prediction,
            str(list(req.input_data.keys())), req.timestamp_met
        )
        return _response(module_name, prediction, observation)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Inference error in '{module_name}': {exc}")


@router.post("/ml/{module_name}/upload", response_model=MLPredictResponse)
async def upload_ml_input(
    module_name: str,
    file: UploadFile = File(...),
    crew_id: int = Form(1),
    timestamp_met: float = Form(0.0),
    subject_id: Optional[str] = Form(None),
    timepoint: Optional[str] = Form(None),
    sampling_rate: int = Form(100),
    model_type: str = Form("emg"),
    session: Session = Depends(get_db),
    ml_router: MLRouter = Depends(get_ml_router),
    insight_engine: InsightEngine = Depends(get_insight_engine),
):
    if module_name not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=404, detail=f"Unknown ML module: {module_name}")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS[module_name]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type for {module_name}. Allowed: {sorted(ALLOWED_EXTENSIONS[module_name])}",
        )

    temp_path = None
    try:
        with NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            temp_path = Path(temp.name)
            total = 0
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="Upload exceeds 100 MB limit.")
                temp.write(chunk)

        if total == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        metadata = {
            "subject_id": subject_id,
            "timepoint": timepoint,
            "sampling_rate": sampling_rate,
            "model_type": model_type,
        }

        prediction = ml_router.predict_file(module_name, temp_path, metadata)
        observation = _save_prediction(
            session,
            insight_engine,
            crew_id,
            module_name,
            prediction,
            f"uploaded_file:{file.filename}; bytes:{total}",
            timestamp_met,
        )
        return _response(module_name, prediction, observation)

    except HTTPException:
        session.rollback()
        raise
    except KeyError as exc:
        session.rollback()
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"File inference error in '{module_name}': {exc}")
    finally:
        await file.close()
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)


@router.get("/ml/health", response_model=List[Dict[str, Any]])
def check_all_modules_health(ml_router: MLRouter = Depends(get_ml_router)):
    return ml_router.health_check_all()


@router.get("/ml/{module_name}/health", response_model=Dict[str, Any])
def check_module_health(module_name: str, ml_router: MLRouter = Depends(get_ml_router)):
    try:
        return ml_router.health_check(module_name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Module '{module_name}' not found")
