"""Ground Medical Review and Asynchronous Store-and-Forward endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from astra_med.api.deps import get_db, get_store_forward_queue
from astra_med.core.store_forward import StoreAndForwardQueue
from astra_med.db import crud

router = APIRouter(prefix="/ground", tags=["Ground Review & Telemedicine"])


class EncounterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    encounter_uuid: str
    crew_id: int
    alert_id: int
    timestamp_met: float
    action_card_id: Optional[str]
    raw_digest: str
    crew_acknowledged: bool
    ground_synced: bool
    checksum: str


class GroundReviewSubmitRequest(BaseModel):
    encounter_id: int
    reviewer: str
    review_text: str
    recommendations: List[str] = []
    approved_updates: Dict[str, Any] = {}
    received_met: float = 0.0


class GroundReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    encounter_id: int
    reviewer: str
    review_text: str
    recommendations_json: str
    approved_updates_json: str
    received_met: float
    applied: bool


@router.get("/queue", response_model=List[EncounterResponse])
def get_ground_queue(
    session: Session = Depends(get_db),
    sf_queue: StoreAndForwardQueue = Depends(get_store_forward_queue),
):
    encounters = sf_queue.get_pending(session)
    return encounters


@router.get("/queue/depth")
def get_queue_depth(
    session: Session = Depends(get_db),
    sf_queue: StoreAndForwardQueue = Depends(get_store_forward_queue),
):
    depth = sf_queue.get_queue_depth(session)
    return {"pending_encounters": depth}


@router.post("/sync/{encounter_id}")
def sync_encounter(
    encounter_id: int,
    session: Session = Depends(get_db),
    sf_queue: StoreAndForwardQueue = Depends(get_store_forward_queue),
):
    ok = sf_queue.mark_synced(session, encounter_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Encounter {encounter_id} not found")
    return {"status": "synced", "encounter_id": encounter_id}


@router.post("/review", response_model=GroundReviewResponse, status_code=status.HTTP_201_CREATED)
def submit_ground_review(
    req: GroundReviewSubmitRequest,
    session: Session = Depends(get_db),
):
    encounter = crud.get_encounter_by_id(session, req.encounter_id)
    if not encounter:
        raise HTTPException(status_code=404, detail=f"Encounter package {req.encounter_id} not found")

    review = crud.create_ground_review(
        session=session,
        encounter_id=req.encounter_id,
        reviewer=req.reviewer,
        review_text=req.review_text,
        recommendations=req.recommendations,
        approved_updates=req.approved_updates,
        received_met=req.received_met,
    )
    return review


@router.get("/reviews/{encounter_id}", response_model=List[GroundReviewResponse])
def get_reviews_for_encounter(
    encounter_id: int,
    session: Session = Depends(get_db),
):
    reviews = crud.get_reviews_for_encounter(session, encounter_id)
    return reviews
