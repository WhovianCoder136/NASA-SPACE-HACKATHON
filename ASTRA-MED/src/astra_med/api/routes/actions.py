"""API Routes for Action Engine & Pre-Approved Support Protocols."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from astra_med.api.deps import get_action_engine, get_db
from astra_med.core.action_engine import ActionEngine
from astra_med.db import crud

router = APIRouter(prefix="/actions", tags=["Action Engine"])


class ActionTaskResponse(BaseModel):
    id: int
    action_id: str
    crew_id: int
    title: str
    description: str
    source: str
    approval_required: bool
    status: str
    notes: Optional[str] = None
    created_at: str
    acknowledged_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AcknowledgeRequest(BaseModel):
    notes: Optional[str] = None


class AssignActionRequest(BaseModel):
    crew_id: int
    action_id: str
    notes: Optional[str] = None


@router.get("")
def list_actions_and_tasks(
    crew_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    action_engine: ActionEngine = Depends(get_action_engine),
    session: Session = Depends(get_db),
):
    """Retrieve pre-approved action library alongside assigned crew action tasks."""
    library = action_engine.get_library()
    tasks = crud.list_action_tasks_for_crew(session=session, crew_id=crew_id, status=status)
    return {
        "library": library,
        "tasks": [
            ActionTaskResponse(
                id=t.id,
                action_id=t.action_id,
                crew_id=t.crew_id,
                title=t.title,
                description=t.description,
                source=t.source,
                approval_required=t.approval_required,
                status=t.status,
                notes=t.notes,
                created_at=t.created_at.isoformat() if t.created_at else "",
                acknowledged_at=t.acknowledged_at.isoformat() if t.acknowledged_at else None,
            )
            for t in tasks
        ],
    }


@router.post("/assign", response_model=ActionTaskResponse, status_code=status.HTTP_201_CREATED)
def assign_action_task(
    req: AssignActionRequest,
    action_engine: ActionEngine = Depends(get_action_engine),
    session: Session = Depends(get_db),
):
    """Assign a pre-approved action task to an astronaut."""
    task = action_engine.dispatch_action(
        session=session,
        crew_id=req.crew_id,
        action_id=req.action_id,
        notes=req.notes,
    )
    session.commit()
    return ActionTaskResponse(
        id=task.id,
        action_id=task.action_id,
        crew_id=task.crew_id,
        title=task.title,
        description=task.description,
        source=task.source,
        approval_required=task.approval_required,
        status=task.status,
        notes=task.notes,
        created_at=task.created_at.isoformat() if task.created_at else "",
        acknowledged_at=task.acknowledged_at.isoformat() if task.acknowledged_at else None,
    )


@router.post("/{action_id}/acknowledge", response_model=ActionTaskResponse)
def acknowledge_action(
    action_id: str,
    req: Optional[AcknowledgeRequest] = None,
    action_engine: ActionEngine = Depends(get_action_engine),
    session: Session = Depends(get_db),
):
    """Acknowledge an action task by ID or action code (e.g. ACT-HYD-01)."""
    notes = req.notes if req else None
    task = action_engine.acknowledge_action(session, action_id, notes=notes)
    if not task:
        # If task does not exist yet in DB, auto-create and acknowledge it for crew #1
        task = action_engine.dispatch_action(session, crew_id=1, action_id=action_id, notes=notes)
        task = action_engine.acknowledge_action(session, str(task.id), notes=notes)
    session.commit()
    return ActionTaskResponse(
        id=task.id,
        action_id=task.action_id,
        crew_id=task.crew_id,
        title=task.title,
        description=task.description,
        source=task.source,
        approval_required=task.approval_required,
        status=task.status,
        notes=task.notes,
        created_at=task.created_at.isoformat() if task.created_at else "",
        acknowledged_at=task.acknowledged_at.isoformat() if task.acknowledged_at else None,
    )
