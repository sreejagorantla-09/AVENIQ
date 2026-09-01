import hashlib
import json
import logging
from typing import List, Optional
from app.db.client import get_db_client
from app.schemas.models import AuditEventCreate

logger = logging.getLogger("aveniq.audit")

class AuditService:
    @staticmethod
    def calculate_event_hash(
        previous_hash: str,
        event_type: str,
        actor_type: str,
        actor_id: Optional[str],
        entity_type: Optional[str],
        entity_id: Optional[str],
        action: Optional[str],
        decision: Optional[str],
        details: Optional[dict]
    ) -> str:
        """
        Computes a deterministic SHA-256 hash incorporating the previous event's hash
        and the current event's payload fields.
        """
        # Sort keys to ensure JSON string representation is always deterministic
        details_str = ""
        if details:
            details_str = json.dumps(details, sort_keys=True)
            
        payload = (
            f"{previous_hash}|"
            f"{event_type}|"
            f"{actor_type}|"
            f"{actor_id or ''}|"
            f"{entity_type or ''}|"
            f"{entity_id or ''}|"
            f"{action or ''}|"
            f"{decision or ''}|"
            f"{details_str}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def get_last_event_hash() -> str:
        """
        Retrieves the hash of the most recent audit event.
        Returns "0" (genesis hash) if no events exist.
        """
        try:
            db = get_db_client()
            response = db.table("audit_events") \
                .select("event_hash") \
                .order("created_at", desc=True) \
                .limit(1) \
                .execute()
            
            if response.data:
                return response.data[0].get("event_hash") or "0"
        except Exception as e:
            logger.error(f"Error fetching last audit event hash: {e}")
        
        return "0"

    @classmethod
    def create_audit_event(cls, event_data: AuditEventCreate) -> dict:
        """
        Generates and chains the SHA-256 hash, then inserts the audit event.
        """
        db = get_db_client()
        
        # Get previous hash
        previous_hash = cls.get_last_event_hash()
        
        # Calculate current hash
        current_hash = cls.calculate_event_hash(
            previous_hash=previous_hash,
            event_type=event_data.event_type,
            actor_type=event_data.actor_type,
            actor_id=event_data.actor_id,
            entity_type=event_data.entity_type,
            entity_id=event_data.entity_id,
            action=event_data.action,
            decision=event_data.decision,
            details=event_data.details
        )
        
        data = {
            "merchant_id": str(event_data.merchant_id),
            "agent_id": str(event_data.agent_id) if event_data.agent_id else None,
            "request_id": str(event_data.request_id) if event_data.request_id else None,
            "event_type": event_data.event_type,
            "actor_type": event_data.actor_type,
            "actor_id": event_data.actor_id,
            "entity_type": event_data.entity_type,
            "entity_id": event_data.entity_id,
            "action": event_data.action,
            "decision": event_data.decision,
            "details": event_data.details,
            "previous_event_hash": previous_hash,
            "event_hash": current_hash,
        }
        
        response = db.table("audit_events").insert(data).execute()
        return response.data[0]

    @staticmethod
    def get_all_audit_events() -> List[dict]:
        """
        Retrieves all audit events in chronological order.
        """
        db = get_db_client()
        response = db.table("audit_events") \
            .select("*") \
            .order("created_at", desc=False) \
            .execute()
        return response.data

    _tamper_simulation_active: bool = False

    @classmethod
    def set_tamper_simulation(cls, active: bool):
        """
        Toggles safe in-memory tamper simulation mode.
        Does not mutate or alter database audit records.
        """
        cls._tamper_simulation_active = active
        logger.info(f"Audit chain tamper simulation mode set to: {active}")

    @classmethod
    def is_tamper_simulation_active(cls) -> bool:
        return cls._tamper_simulation_active

    @classmethod
    def verify_audit_chain(cls) -> dict:
        """
        Validates the integrity of the audit events hash chain.
        Returns a detailed result dict with block counts and mismatch details.
        """
        events = cls.get_all_audit_events()
        total_blocks = len(events)
        
        if not events:
            return {
                "valid": True,
                "status": "verified",
                "total_blocks": 0,
                "tamper_simulation_active": cls._tamper_simulation_active
            }
        
        expected_prev_hash = "0"
        for idx, event in enumerate(events):
            # If tamper simulation is active, inject a simulated mismatch on block index 1
            simulated_action = event.get("action")
            if cls._tamper_simulation_active and idx == 1:
                simulated_action = f"{simulated_action}_TAMPERED_PAYLOAD"

            # 1. Verify links
            if event.get("previous_event_hash") != expected_prev_hash:
                logger.error(
                    f"Audit chain broken at index {idx} (ID: {event.get('id')}). "
                    f"Expected previous hash '{expected_prev_hash}', got '{event.get('previous_event_hash')}'."
                )
                return {
                    "valid": False,
                    "status": "corrupted",
                    "total_blocks": total_blocks,
                    "failed_block_index": idx,
                    "event_id": event.get("id"),
                    "reason": "Previous hash link broken",
                    "expected_previous_hash": expected_prev_hash,
                    "stored_previous_hash": event.get("previous_event_hash"),
                    "tamper_simulation_active": cls._tamper_simulation_active
                }
            
            # 2. Re-compute and verify current hash
            computed_hash = cls.calculate_event_hash(
                previous_hash=expected_prev_hash,
                event_type=event.get("event_type"),
                actor_type=event.get("actor_type"),
                actor_id=event.get("actor_id"),
                entity_type=event.get("entity_type"),
                entity_id=event.get("entity_id"),
                action=simulated_action,
                decision=event.get("decision"),
                details=event.get("details")
            )
            
            if event.get("event_hash") != computed_hash:
                logger.error(
                    f"Audit hash mismatch at index {idx} (ID: {event.get('id')}). "
                    f"Stored hash '{event.get('event_hash')}', computed '{computed_hash}'."
                )
                return {
                    "valid": False,
                    "status": "corrupted",
                    "total_blocks": total_blocks,
                    "failed_block_index": idx,
                    "event_id": event.get("id"),
                    "reason": "Hash signature mismatch (payload payload altered)",
                    "stored_hash": event.get("event_hash"),
                    "computed_hash": computed_hash,
                    "tamper_simulation_active": cls._tamper_simulation_active
                }
                
            expected_prev_hash = event.get("event_hash")
            
        return {
            "valid": True,
            "status": "verified",
            "total_blocks": total_blocks,
            "tamper_simulation_active": cls._tamper_simulation_active
        }
