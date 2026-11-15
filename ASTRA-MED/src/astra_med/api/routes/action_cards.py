"""Action Cards API routes for retrieving pre-authorized medical guidance."""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from astra_med.api.deps import get_action_card_registry, get_db
from astra_med.core.action_cards import ActionCardRegistry
from astra_med.core.types import ActionCard, HazardType, SeverityTier
from astra_med.db import crud

router = APIRouter(prefix="/action-cards", tags=["Action Cards"])


@router.get("", response_model=List[ActionCard])
def list_action_cards(
    hazard: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    card_registry: ActionCardRegistry = Depends(get_action_card_registry),
):
    h = None
    if hazard and isinstance(hazard, str):
        try:
            h = HazardType(hazard)
        except ValueError:
            pass

    s = None
    if severity and isinstance(severity, str):
        try:
            s = SeverityTier(severity)
        except ValueError:
            pass

    cards = card_registry.find_cards(hazard=h, severity=s)
    return cards


@router.get("/{card_id}", response_model=ActionCard)
def get_action_card(
    card_id: str,
    card_registry: ActionCardRegistry = Depends(get_action_card_registry),
):
    card = card_registry.get_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail=f"Action card {card_id} not found")
    return card


@router.get("/for-alert/{alert_id}", response_model=ActionCard)
def get_action_card_for_alert(
    alert_id: int,
    session: Session = Depends(get_db),
    card_registry: ActionCardRegistry = Depends(get_action_card_registry),
):
    alert = crud.get_alert(session, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    if alert.action_card_id:
        card = card_registry.get_card(alert.action_card_id)
        if card:
            return card

    hazard = HazardType(alert.hazard) if alert.hazard in HazardType._value2member_map_ else None
    severity = SeverityTier(alert.severity) if alert.severity in SeverityTier._value2member_map_ else None
    candidates = card_registry.find_cards(hazard=hazard, severity=severity)
    if candidates:
        return candidates[0]

    raise HTTPException(status_code=404, detail="No matching action card found for alert")
