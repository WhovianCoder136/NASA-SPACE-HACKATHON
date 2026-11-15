"""Crew management API routes."""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from astra_med.db import crud
from astra_med.db.database import get_db

router = APIRouter(prefix="/crew", tags=["Crew"])


class CrewCreateRequest(BaseModel):
    name: str
    role: str
    status: str = "active"
    astronaut_id: Optional[str] = None
    mission_id: str = "ASTRA-1"
    username: Optional[str] = None
    password: Optional[str] = None
    is_medical_officer: bool = False


class CrewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    astronaut_id: Optional[str] = None
    name: str
    role: str
    status: str
    is_medical_officer: bool = False


class CrewDetailResponse(CrewResponse):
    active_baselines_count: int = 0
    latest_vitals: List[dict] = []


@router.post("", response_model=CrewResponse, status_code=status.HTTP_201_CREATED)
def create_crew(
    req: CrewCreateRequest,
    session: Session = Depends(get_db),
):
    from astra_med.api.auth import get_password_hash
    pwd_hash = get_password_hash(req.password) if req.password else None
    member = crud.create_crew_member(
        session=session,
        name=req.name,
        role=req.role,
        status=req.status,
        astronaut_id=req.astronaut_id,
        mission_id=req.mission_id,
        username=req.username,
        password_hash=pwd_hash,
        is_medical_officer=req.is_medical_officer,
    )
    return member


@router.get("", response_model=List[CrewResponse])
def list_crew(
    session: Session = Depends(get_db),
):
    members = crud.list_crew_members(session)
    return members


@router.get("/{crew_id}", response_model=CrewDetailResponse)
def get_crew(
    crew_id: int,
    session: Session = Depends(get_db),
):
    member = crud.get_crew_member(session, crew_id)
    if not member:
        raise HTTPException(status_code=404, detail=f"Crew member with id {crew_id} not found")

    baselines = crud.get_all_baselines_for_crew(session, crew_id)
    latest_vitals_records = crud.get_latest_vitals(session, crew_id)

    latest_vitals = [
        {
            "metric_name": v.metric_name,
            "value": v.value,
            "unit": v.unit,
            "timestamp_met": v.timestamp_met,
            "sqi_score": v.sqi_score,
            "sqi_valid": v.sqi_valid,
        }
        for v in latest_vitals_records
    ]

    return CrewDetailResponse(
        id=member.id,
        name=member.name,
        role=member.role,
        status=member.status,
        active_baselines_count=len(baselines),
        latest_vitals=latest_vitals,
    )
