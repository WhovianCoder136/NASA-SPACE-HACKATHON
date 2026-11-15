
"""ASTRA-MED Action Engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from astra_med.db import crud
from astra_med.db.models import ActionTaskRecord


PREAPPROVED_ACTIONS: List[Dict[str, Any]] = [
    {
        "action_id": "ACT-HYD-01",
        "title": "Electrolyte & Fluid Volume Loading",
        "description": "Ingest 500 mL water with oral electrolyte rehydration sachet over 30 minutes to support circulating plasma volume.",
        "source": "preapproved_action_library",
        "approval_required": False,
        "hazard": "hazard_4_gravity_fields",
    },
    {
        "action_id": "ACT-PST-02",
        "title": "Staged Postural Orthostatic Transition",
        "description": "Remain seated with bilateral calf flexions for 3 minutes before executing upright standing maneuver during microgravity-to-hypergravity transition.",
        "source": "preapproved_action_library",
        "approval_required": False,
        "hazard": "hazard_4_gravity_fields",
    },
    {
        "action_id": "ACT-SLP-03",
        "title": "Circadian Reset & Dynamic Blue Light Notch",
        "description": "Activate 460nm notch cabin lighting filter 2 hours prior to sleep window. Perform 10-minute paced diaphragmatic breathing protocol.",
        "source": "preapproved_action_library",
        "approval_required": False,
        "hazard": "hazard_2_isolation_and_confinement",
    },
    {
        "action_id": "ACT-RPT-04",
        "title": "Repeat Telemetry Verification Cycle",
        "description": "Conduct repeat vital measurement in 15 minutes to confirm observed deviation.",
        "source": "preapproved_action_library",
        "approval_required": False,
        "hazard": "general",
    },
    {
        "action_id": "ACT-EXR-05",
        "title": "Countermeasure Resistive Ergometer Adjustment",
        "description": "Maintain the approved daily exercise countermeasure schedule.",
        "source": "preapproved_action_library",
        "approval_required": False,
        "hazard": "hazard_4_gravity_fields",
    },
    {
        "action_id": "ACT-REP-06",
        "title": "Compile Ground Telemedicine Encounter Dossier",
        "description": "Bundle recent telemetry, baseline deviation statistics, and action card execution records for Earth review.",
        "source": "preapproved_action_library",
        "approval_required": False,
        "hazard": "hazard_3_distance_from_earth",
    },
]


class ActionEngine:
    """Orchestrates operational actions and task acknowledgments."""

    def __init__(self, action_library: Optional[List[Dict[str, Any]]] = None):
        self.library = action_library or PREAPPROVED_ACTIONS

    def get_library(self) -> List[Dict[str, Any]]:
        """Load all JSON action cards from the project action_cards directory."""
        project_root = Path(__file__).resolve().parents[3]
        action_cards_dir = project_root / "action_cards"

        library = []

        if not action_cards_dir.exists():
            return library

        for card_file in sorted(action_cards_dir.glob("*.json")):
            try:
                with card_file.open("r", encoding="utf-8") as file:
                    card = json.load(file)
                    library.append(card)
            except (json.JSONDecodeError, OSError) as error:
                print(f"Failed to load {card_file.name}: {error}")

        return library

    def get_action_by_id(self, action_id: str) -> Optional[Dict[str, Any]]:
        for action in self.library:
            if action["action_id"] == action_id:
                return action
        return None

    def recommend_for_module(
        self,
        module: str,
        severity: str = "monitor",
    ) -> List[Dict[str, Any]]:
        mod = module.lower()
        recommendations = []

        if "cardio" in mod or "gravity" in mod:
            recommendations.extend([
                self.get_action_by_id("ACT-HYD-01"),
                self.get_action_by_id("ACT-PST-02"),
            ])
        elif "sleep" in mod or "isolation" in mod:
            recommendations.append(self.get_action_by_id("ACT-SLP-03"))
        elif "metabolic" in mod:
            recommendations.append(self.get_action_by_id("ACT-HYD-01"))

        if severity in ("warning", "critical"):
            recommendations.append(self.get_action_by_id("ACT-RPT-04"))
            recommendations.append(self.get_action_by_id("ACT-REP-06"))

        return [item for item in recommendations if item is not None]

    def dispatch_action(
        self,
        session: Session,
        crew_id: int,
        action_id: str,
        notes: Optional[str] = None,
    ) -> ActionTaskRecord:
        template = self.get_action_by_id(action_id)

        if not template:
            return crud.create_action_task(
                session=session,
                action_id=action_id,
                crew_id=crew_id,
                title=f"Protocol Action: {action_id}",
                description=f"Execute pre-approved flight protocol {action_id}.",
                source="action_card",
                notes=notes,
            )

        return crud.create_action_task(
            session=session,
            action_id=template["action_id"],
            crew_id=crew_id,
            title=template["title"],
            description=template["description"],
            source=template.get("source", "preapproved_action_library"),
            approval_required=template.get("approval_required", False),
            notes=notes,
        )

    def acknowledge_action(
        self,
        session: Session,
        action_id: str,
        notes: Optional[str] = None,
    ) -> Optional[ActionTaskRecord]:
        return crud.acknowledge_action_task(
            session,
            action_id,
            notes=notes,
        )
