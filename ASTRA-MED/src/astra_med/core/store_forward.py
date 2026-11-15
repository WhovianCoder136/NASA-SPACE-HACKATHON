"""Store-and-Forward Encounter Packager and Delayed Transmission Queue."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Optional, Sequence
from sqlalchemy.orm import Session

from astra_med.db import crud
from astra_med.db.models import EncounterPackageRecord


class StoreAndForwardQueue:
    """Manages asynchronous deep-space encounter packages with cryptographic integrity."""

    @staticmethod
    def compute_checksum(payload: dict) -> str:
        """Calculate deterministic SHA-256 digest of an encounter package."""
        canonical_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    def enqueue(
        self,
        session: Session,
        crew_id: int,
        alert_id: int,
        timestamp_met: float,
        action_card_id: Optional[str] = None,
        raw_digest: str = "",
        crew_acknowledged: bool = False,
    ) -> EncounterPackageRecord:
        """Package a clinical event and queue it in the local store-and-forward buffer."""
        encounter_uuid = f"enc-{uuid.uuid4().hex[:12]}"

        integrity_dict = {
            "encounter_uuid": encounter_uuid,
            "crew_id": crew_id,
            "alert_id": alert_id,
            "timestamp_met": timestamp_met,
            "action_card_id": action_card_id,
            "raw_digest": raw_digest,
        }
        checksum = self.compute_checksum(integrity_dict)

        record = crud.create_encounter(
            session=session,
            encounter_uuid=encounter_uuid,
            crew_id=crew_id,
            alert_id=alert_id,
            timestamp_met=timestamp_met,
            action_card_id=action_card_id,
            raw_digest=raw_digest,
            crew_acknowledged=crew_acknowledged,
            checksum=checksum,
        )
        return record

    def get_pending(self, session: Session) -> Sequence[EncounterPackageRecord]:
        """Fetch all packages awaiting Earth transmission window."""
        return crud.get_pending_encounters(session)

    def mark_synced(self, session: Session, encounter_id: int) -> bool:
        """Mark package as transmitted upon ground link confirmation."""
        return crud.mark_encounter_synced(session, encounter_id)

    def get_queue_depth(self, session: Session) -> int:
        """Get number of untransmitted encounters in buffer."""
        pending = self.get_pending(session)
        return len(pending)
