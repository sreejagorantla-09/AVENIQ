from typing import Optional
from uuid import UUID
from app.db.client import get_db_client
from app.schemas.models import AuditEventCreate
from app.services.audit_service import AuditService

class MerchantService:
    @staticmethod
    def get_active_merchant() -> Optional[dict]:
        """
        Retrieves the active merchant record (AVENIQ_MERCHANT_001).
        """
        db = get_db_client()
        response = db.table("merchants").select("*").eq("merchant_code", "AVENIQ_MERCHANT_001").execute()
        if response.data:
            return response.data[0]
        return None

    @classmethod
    def update_merchant(cls, merchant_id: UUID, data: dict) -> Optional[dict]:
        """
        Updates merchant profile details and logs a MERCHANT_UPDATED audit event.
        """
        db = get_db_client()
        response = db.table("merchants").update(data).eq("id", str(merchant_id)).execute()
        if response.data:
            updated_merchant = response.data[0]
            # Log audit event
            audit_data = AuditEventCreate(
                merchant_id=merchant_id,
                event_type="MERCHANT_UPDATED",
                actor_type="merchant",
                actor_id="merchant-admin",
                entity_type="merchant",
                entity_id=str(merchant_id),
                action="update_profile",
                decision="ALLOW",
                details={"updated_fields": list(data.keys())}
            )
            AuditService.create_audit_event(audit_data)
            return updated_merchant
        return None

    @classmethod
    def recalculate_trust_score(cls, merchant_id: UUID) -> float:
        """
        Recalculates the dynamic trust score based on transaction checks:
        - Base: 100.0
        - Fail checkouts signature: -5.0 per failure
        - Tampered audit chains: -50.0 if chain is currently corrupted
        - Successful completed payments: +1.0 per transaction (capped at 100.0)
        """
        db = get_db_client()
        base_score = 100.0
        
        # 1. Count TRANSACTION_FAILED audit events for this merchant
        failed_res = db.table("audit_events") \
            .select("id", count="exact") \
            .eq("merchant_id", str(merchant_id)) \
            .eq("event_type", "TRANSACTION_FAILED") \
            .execute()
        failed_count = failed_res.count or len(failed_res.data) or 0
        base_score -= (failed_count * 5.0)
        
        # 2. Count PAYMENT_VERIFIED / TRANSACTION_COMPLETED audit events for this merchant
        success_res = db.table("audit_events") \
            .select("id", count="exact") \
            .eq("merchant_id", str(merchant_id)) \
            .eq("event_type", "PAYMENT_VERIFIED") \
            .execute()
        success_count = success_res.count or len(success_res.data) or 0
        base_score += (success_count * 1.0)
        
        # 3. Check audit trail verification status
        try:
            from app.services.audit_service import AuditService
            if not AuditService.verify_audit_chain():
                base_score -= 50.0
        except Exception:
            pass
            
        # Clamp between 0.0 and 100.0
        final_score = max(0.0, min(100.0, base_score))
        
        # Update merchant table trust_score column
        db.table("merchants").update({"trust_score": final_score}).eq("id", str(merchant_id)).execute()
        
        return final_score
