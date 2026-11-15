"""API Routes for Medical Reports, Asynchronous Store-and-Forward, and Earth Physician Review."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from astra_med.api.deps import get_db
from astra_med.db import crud

router = APIRouter(prefix="/medical-reports", tags=["Medical Reports & Asynchronous Communication"])


class CreateMedicalReportRequest(BaseModel):
    crew_id: int
    title: str
    summary: str
    domain: str = "general"
    requires_physician_review: bool = True
    future_phase_updates: Optional[Dict[str, Any]] = None


class ReviewReportRequest(BaseModel):
    physician_name: str
    decision: str  # approved, amended, rejected
    comments: str
    future_phase_updates: Optional[Dict[str, Any]] = None


class MedicalReportResponse(BaseModel):
    id: int
    report_id: str
    crew_id: int
    title: str
    summary: str
    domain: str
    status: str
    requires_physician_review: bool
    physician_decision: Optional[str] = None
    physician_comments: Optional[str] = None
    future_phase_updates: Dict[str, Any] = {}
    checksum: str
    created_at: str
    synced_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


@router.post("", response_model=MedicalReportResponse, status_code=status.HTTP_201_CREATED)
def create_medical_report(
    req: CreateMedicalReportRequest,
    session: Session = Depends(get_db),
):
    """Create and queue a medical encounter report for ground transmission."""
    report_uuid = f"MED-REP-{uuid.uuid4().hex[:8].upper()}"
    digest_payload = f"{report_uuid}|{req.crew_id}|{req.title}|{req.summary}"
    checksum = hashlib.sha256(digest_payload.encode()).hexdigest()

    rec = crud.create_medical_report(
        session=session,
        report_id=report_uuid,
        crew_id=req.crew_id,
        title=req.title,
        summary=req.summary,
        domain=req.domain,
        status="queued_for_sync",
        requires_physician_review=req.requires_physician_review,
        future_phase_updates=req.future_phase_updates,
        checksum=checksum,
    )
    session.commit()

    return MedicalReportResponse(
        id=rec.id,
        report_id=rec.report_id,
        crew_id=rec.crew_id,
        title=rec.title,
        summary=rec.summary,
        domain=rec.domain,
        status=rec.status,
        requires_physician_review=rec.requires_physician_review,
        physician_decision=rec.physician_decision,
        physician_comments=rec.physician_comments,
        future_phase_updates=json.loads(rec.future_phase_updates_json or "{}"),
        checksum=rec.checksum,
        created_at=rec.created_at.isoformat() if rec.created_at else "",
        synced_at=rec.synced_at.isoformat() if rec.synced_at else None,
    )


@router.get("", response_model=List[MedicalReportResponse])
def list_reports(
    crew_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    session: Session = Depends(get_db),
):
    """List medical reports with optional crew or status filter."""
    recs = crud.get_medical_reports_for_crew(session=session, crew_id=crew_id, status=status)
    return [
        MedicalReportResponse(
            id=r.id,
            report_id=r.report_id,
            crew_id=r.crew_id,
            title=r.title,
            summary=r.summary,
            domain=r.domain,
            status=r.status,
            requires_physician_review=r.requires_physician_review,
            physician_decision=r.physician_decision,
            physician_comments=r.physician_comments,
            future_phase_updates=json.loads(r.future_phase_updates_json or "{}"),
            checksum=r.checksum,
            created_at=r.created_at.isoformat() if r.created_at else "",
            synced_at=r.synced_at.isoformat() if r.synced_at else None,
        )
        for r in recs
    ]


@router.get("/{astronaut_id}", response_model=List[MedicalReportResponse])
def get_astronaut_reports(
    astronaut_id: str,
    session: Session = Depends(get_db),
):
    """Get all medical reports for a specific astronaut."""
    if astronaut_id.isdigit():
        c_id = int(astronaut_id)
    elif astronaut_id.startswith("ASTRA-"):
        try:
            c_id = int(astronaut_id.split("-")[1])
        except Exception:
            c_id = 1
    else:
        c_id = 1

    recs = crud.get_medical_reports_for_crew(session=session, crew_id=c_id)
    return [
        MedicalReportResponse(
            id=r.id,
            report_id=r.report_id,
            crew_id=r.crew_id,
            title=r.title,
            summary=r.summary,
            domain=r.domain,
            status=r.status,
            requires_physician_review=r.requires_physician_review,
            physician_decision=r.physician_decision,
            physician_comments=r.physician_comments,
            future_phase_updates=json.loads(r.future_phase_updates_json or "{}"),
            checksum=r.checksum,
            created_at=r.created_at.isoformat() if r.created_at else "",
            synced_at=r.synced_at.isoformat() if r.synced_at else None,
        )
        for r in recs
    ]


@router.post("/{report_id}/sync", response_model=MedicalReportResponse)
def sync_report(
    report_id: str,
    session: Session = Depends(get_db),
):
    """Simulate downlink transmission to Earth ground station."""
    rec = crud.mark_medical_report_synced(session, report_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Medical report not found")
    session.commit()
    return MedicalReportResponse(
        id=rec.id,
        report_id=rec.report_id,
        crew_id=rec.crew_id,
        title=rec.title,
        summary=rec.summary,
        domain=rec.domain,
        status=rec.status,
        requires_physician_review=rec.requires_physician_review,
        physician_decision=rec.physician_decision,
        physician_comments=rec.physician_comments,
        future_phase_updates=json.loads(rec.future_phase_updates_json or "{}"),
        checksum=rec.checksum,
        created_at=rec.created_at.isoformat() if rec.created_at else "",
        synced_at=rec.synced_at.isoformat() if rec.synced_at else None,
    )


@router.post("/{report_id}/review", response_model=MedicalReportResponse)
def review_report(
    report_id: str,
    req: ReviewReportRequest,
    session: Session = Depends(get_db),
):
    """Receive asynchronous ground flight surgeon decision and future mission phase updates."""
    rec = crud.review_medical_report(
        session=session,
        report_id=report_id,
        physician_decision=req.decision,
        comments=f"[{req.physician_name}] {req.comments}",
        future_phase_updates=req.future_phase_updates,
    )
    if not rec:
        raise HTTPException(status_code=404, detail="Medical report not found")
    session.commit()
    return MedicalReportResponse(
        id=rec.id,
        report_id=rec.report_id,
        crew_id=rec.crew_id,
        title=rec.title,
        summary=rec.summary,
        domain=rec.domain,
        status=rec.status,
        requires_physician_review=rec.requires_physician_review,
        physician_decision=rec.physician_decision,
        physician_comments=rec.physician_comments,
        future_phase_updates=json.loads(rec.future_phase_updates_json or "{}"),
        checksum=rec.checksum,
        created_at=rec.created_at.isoformat() if rec.created_at else "",
        synced_at=rec.synced_at.isoformat() if rec.synced_at else None,
    )
