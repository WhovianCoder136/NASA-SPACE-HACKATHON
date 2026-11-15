"""Action Card Registry: manages immutable, pre-approved medical action cards."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from astra_med.config import ACTION_CARDS_DIR
from astra_med.core.types import ActionCard, HazardType, SeverityTier
from astra_med.db import crud


class ActionCardRegistry:
    """Loads and serves pre-approved, versioned action cards."""

    def __init__(self, cards_dir: Path = ACTION_CARDS_DIR):
        self.cards_dir = cards_dir
        self._cards: Dict[str, ActionCard] = {}
        self.load_cards()

    def load_cards(self) -> None:
        """Scan ACTION_CARDS_DIR and parse all JSON action cards."""
        self._cards.clear()
        if not self.cards_dir.exists():
            return

        for json_path in self.cards_dir.glob("*.json"):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                card = ActionCard(
                    card_id=data["card_id"],
                    version=data.get("version", "1.0"),
                    hazard=HazardType(data["hazard"]),
                    severity=SeverityTier(data["severity"]),
                    title=data["title"],
                    plain_language_summary=data["plain_language_summary"],
                    crew_instructions=data["crew_instructions"],
                    safety_limits=data.get("safety_limits", {}),
                    de_escalation_criteria=data.get("de_escalation_criteria"),
                )
                self._cards[card.card_id] = card
            except Exception as e:
                print(f"[ActionCardRegistry] Error loading {json_path}: {e}")

    def get_card(self, card_id: str) -> Optional[ActionCard]:
        return self._cards.get(card_id)

    def find_cards(
        self,
        hazard: Optional[HazardType] = None,
        severity: Optional[SeverityTier] = None,
    ) -> List[ActionCard]:
        results = []
        for card in self._cards.values():
            if hazard and card.hazard != hazard:
                continue
            if severity and card.severity != severity:
                continue
            results.append(card)
        return results

    def seed_defaults(self, session: Session) -> None:
        """Sync loaded action cards into SQLite database records."""
        for card in self._cards.values():
            existing = crud.get_action_card(session, card.card_id)
            if existing is None:
                crud.create_action_card(
                    session=session,
                    card_id=card.card_id,
                    version=card.version,
                    hazard=card.hazard.value,
                    severity=card.severity.value,
                    title=card.title,
                    summary=card.plain_language_summary,
                    instructions=card.crew_instructions,
                    safety_limits=card.safety_limits,
                    de_escalation_criteria=card.de_escalation_criteria or "",
                )
