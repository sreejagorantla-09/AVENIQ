from typing import List, Optional
from uuid import UUID
from app.db.client import get_db_client
from app.schemas.models import MerchantPolicyCreate, AuditEventCreate
from app.services.audit_service import AuditService

class PolicyService:
    @staticmethod
    def get_all_policies() -> List[dict]:
        """
        Retrieves all merchant policies from the database.
        """
        db = get_db_client()
        response = db.table("merchant_policies").select("*").order("priority", desc=False).execute()
        return response.data

    @staticmethod
    def create_policy(policy_data: MerchantPolicyCreate) -> dict:
        """
        Creates a new policy constraint and logs a POLICY_CREATED audit event.
        """
        db = get_db_client()
        data = {
            "merchant_id": str(policy_data.merchant_id),
            "policy_type": policy_data.policy_type,
            "policy_name": policy_data.policy_name,
            "description": policy_data.description,
            "rules": policy_data.rules,
            "priority": policy_data.priority,
            "is_active": policy_data.is_active
        }
        response = db.table("merchant_policies").insert(data).execute()
        new_policy = response.data[0]

        # Audit event
        audit_data = AuditEventCreate(
            merchant_id=policy_data.merchant_id,
            event_type="POLICY_CREATED",
            actor_type="merchant",
            actor_id="merchant-admin",
            entity_type="policy",
            entity_id=new_policy["id"],
            action="create_policy",
            decision="ALLOW",
            details={"policy_type": policy_data.policy_type, "policy_name": policy_data.policy_name}
        )
        AuditService.create_audit_event(audit_data)

        return new_policy

    @staticmethod
    def update_policy(policy_id: UUID, policy_data: dict) -> Optional[dict]:
        """
        Updates policy parameters and logs a POLICY_UPDATED audit event.
        """
        db = get_db_client()
        # Fetch current record for merchant context
        current_res = db.table("merchant_policies").select("*").eq("id", str(policy_id)).execute()
        if not current_res.data:
            return None
        current_policy = current_res.data[0]

        response = db.table("merchant_policies").update(policy_data).eq("id", str(policy_id)).execute()
        if response.data:
            updated_policy = response.data[0]
            # Audit event
            audit_data = AuditEventCreate(
                merchant_id=UUID(current_policy["merchant_id"]),
                event_type="POLICY_UPDATED",
                actor_type="merchant",
                actor_id="merchant-admin",
                entity_type="policy",
                entity_id=str(policy_id),
                action="update_policy",
                decision="ALLOW",
                details={"updated_fields": list(policy_data.keys()), "policy_name": current_policy["policy_name"]}
            )
            AuditService.create_audit_event(audit_data)
            return updated_policy
        return None
