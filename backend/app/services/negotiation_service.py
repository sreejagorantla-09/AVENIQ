import logging
from typing import List, Optional
from uuid import UUID
from app.db.client import get_db_client
from app.schemas.models import AuditEventCreate
from app.services.audit_service import AuditService
from app.policies.evaluator import PolicyEvaluator

logger = logging.getLogger("aveniq.negotiation_service")

class NegotiationService:
    @staticmethod
    def get_session_by_id(session_id: UUID) -> Optional[dict]:
        """
        Retrieves a negotiation session by its ID.
        """
        db = get_db_client()
        res = db.table("negotiation_sessions").select("*").eq("id", str(session_id)).execute()
        if res.data:
            return res.data[0]
        return None

    @staticmethod
    def get_all_sessions(merchant_id: UUID) -> List[dict]:
        """
        Lists all negotiation sessions for a merchant.
        """
        db = get_db_client()
        res = db.table("negotiation_sessions") \
            .select("*, agent_requests(*, ai_agents(agent_code))") \
            .eq("merchant_id", str(merchant_id)) \
            .order("created_at", desc=True) \
            .execute()
        return res.data

    @staticmethod
    def create_negotiation_session(
        request_id: UUID,
        merchant_id: UUID,
        agent_id: UUID,
        sku: str,
        quantity: int,
        original_price: float,
        counter_offer_price: float,
        messages: List[dict]
    ) -> dict:
        """
        Creates a new negotiation session and registers a NEGOTIATION_STARTED audit event.
        """
        db = get_db_client()
        payload = {
            "request_id": str(request_id),
            "merchant_id": str(merchant_id),
            "agent_id": str(agent_id),
            "status": "active",
            "sku": sku,
            "quantity": quantity,
            "original_price": original_price,
            "counter_offer_price": counter_offer_price,
            "messages": messages
        }
        res = db.table("negotiation_sessions").insert(payload).execute()
        session = res.data[0]

        # Log audit trail
        audit_data = AuditEventCreate(
            merchant_id=merchant_id,
            agent_id=agent_id,
            request_id=request_id,
            event_type="NEGOTIATION_STARTED",
            actor_type="agent",
            actor_id=str(agent_id),
            entity_type="negotiation",
            entity_id=session["id"],
            action="start_negotiation",
            decision="ALLOW",
            details={
                "sku": sku,
                "quantity": quantity,
                "original_price": original_price,
                "counter_offer_price": counter_offer_price
            }
        )
        AuditService.create_audit_event(audit_data)
        return session

    @classmethod
    def submit_counter_offer(
        cls,
        session_id: UUID,
        counter_price: float,
        messages: List[dict],
        merchant_id: UUID
    ) -> Optional[dict]:
        """
        Submits a counter-offer in the negotiation session and audits the event.
        """
        db = get_db_client()
        session = cls.get_session_by_id(session_id)
        if not session:
            return None

        # Check maximum allowed discount boundary deterministically
        qty = int(session["quantity"])
        sku = session["sku"]
        
        # Calculate max discount allowed in Python
        max_discount_percentage = PolicyEvaluator.calculate_max_discount(merchant_id, sku, qty)
        
        # Get catalog price
        prod_res = db.table("products").select("price").eq("sku", sku).eq("merchant_id", str(merchant_id)).execute()
        if not prod_res.data:
            return None
        catalog_price = float(prod_res.data[0]["price"])
        
        minimum_allowed_price = catalog_price * (1 - max_discount_percentage / 100.0)

        # Enforce boundary: Prohibited from proposing lower than maximum allowed discount bounds
        final_counter_price = max(counter_price, minimum_allowed_price)

        payload = {
            "counter_offer_price": final_counter_price,
            "messages": messages,
            "updated_at": "now()"
        }
        res = db.table("negotiation_sessions").update(payload).eq("id", str(session_id)).execute()
        updated_session = res.data[0]

        # Log audit trail
        audit_data = AuditEventCreate(
            merchant_id=merchant_id,
            agent_id=UUID(session["agent_id"]),
            request_id=UUID(session["request_id"]),
            event_type="COUNTER_OFFER_MADE",
            actor_type="system",
            actor_id="negotiator-assistant",
            entity_type="negotiation",
            entity_id=str(session_id),
            action="submit_counter_offer",
            decision="ALLOW",
            details={
                "counter_price": final_counter_price,
                "requested_counter": counter_price,
                "minimum_allowed": minimum_allowed_price
            }
        )
        AuditService.create_audit_event(audit_data)

        # Log policy check event
        policy_audit = AuditEventCreate(
            merchant_id=merchant_id,
            agent_id=UUID(session["agent_id"]),
            request_id=UUID(session["request_id"]),
            event_type="NEGOTIATION_POLICY_CHECKED",
            actor_type="system",
            actor_id="policy-engine",
            entity_type="negotiation",
            entity_id=str(session_id),
            action="verify_discount_compliance",
            decision="ALLOW" if final_counter_price >= minimum_allowed_price else "DENY",
            details={
                "sku": sku,
                "quantity": qty,
                "proposed_price": final_counter_price,
                "min_allowed_price": minimum_allowed_price
            }
        )
        AuditService.create_audit_event(policy_audit)

        return updated_session

    @classmethod
    def accept_negotiation(cls, session_id: UUID, merchant_id: UUID) -> Optional[dict]:
        """
        Accepts the current counter-offer, re-evaluates policy/stock, and inserts transaction.
        """
        db = get_db_client()
        session = cls.get_session_by_id(session_id)
        if not session:
            return None

        agent_id = UUID(session["agent_id"])
        request_id = UUID(session["request_id"])
        sku = session["sku"]
        quantity = int(session["quantity"])
        final_price = float(session["counter_offer_price"])

        # Concurrency Stock Guard & Policy Re-evaluation immediately before order
        decision, reason, evaluated_rules = PolicyEvaluator.evaluate_proposal_negotiated(
            merchant_id=merchant_id,
            agent_id=agent_id,
            sku=sku,
            quantity=quantity,
            price=final_price
        )

        if decision != "ALLOW":
            # Failed final checkout evaluation
            logger.error(f"Negotiation final checkout failed: {reason}")
            # Audit the failure
            fail_audit = AuditEventCreate(
                merchant_id=merchant_id,
                agent_id=agent_id,
                request_id=request_id,
                event_type="TRANSACTION_FAILED",
                actor_type="system",
                actor_id="checkout-guard",
                entity_type="negotiation",
                entity_id=str(session_id),
                action="checkout_final_check",
                decision="DENY",
                details={"reason": reason}
            )
            AuditService.create_audit_event(fail_audit)
            return {"status": "declined", "error": reason}

        # Transition status
        res = db.table("negotiation_sessions").update({"status": "accepted", "updated_at": "now()"}).eq("id", str(session_id)).execute()
        updated_session = res.data[0]

        # Update request status
        db.table("agent_requests").update({"status": "approved"}).eq("id", str(request_id)).execute()

        # Log audit trail
        audit_data = AuditEventCreate(
            merchant_id=merchant_id,
            agent_id=agent_id,
            request_id=request_id,
            event_type="NEGOTIATION_ACCEPTED",
            actor_type="agent",
            actor_id=str(agent_id),
            entity_type="negotiation",
            entity_id=str(session_id),
            action="accept_negotiation",
            decision="ALLOW",
            details={"final_price": final_price}
        )
        AuditService.create_audit_event(audit_data)

        # Create checkout transaction record
        prod_res = db.table("products").select("id").eq("sku", sku).execute()
        product_id = prod_res.data[0]["id"] if prod_res.data else None
        
        tx_payload = {
            "merchant_id": str(merchant_id),
            "request_id": str(request_id),
            "product_id": str(product_id) if product_id else None,
            "amount": float(quantity * final_price),
            "currency": "INR",
            "payment_provider": "razorpay",
            "status": "pending",
            "metadata": {
                "sku": sku,
                "quantity": quantity,
                "price": final_price,
                "detailed_status": "payment_pending",
                "agent_id": str(agent_id)
            }
        }
        tx_res = db.table("transactions").insert(tx_payload).execute()
        transaction_id = tx_res.data[0]["id"]

        tx_audit = AuditEventCreate(
            merchant_id=merchant_id,
            agent_id=agent_id,
            request_id=request_id,
            event_type="TRANSACTION_CREATED",
            actor_type="system",
            actor_id="transaction-manager",
            entity_type="transaction",
            entity_id=str(transaction_id),
            action="create_transaction",
            decision="ALLOW",
            details={"amount": quantity * final_price, "status": "payment_pending", "negotiation_id": str(session_id), "agent_id": str(agent_id)}
        )
        AuditService.create_audit_event(tx_audit)

        return updated_session

    @classmethod
    def decline_negotiation(cls, session_id: UUID, merchant_id: UUID) -> Optional[dict]:
        """
        Declines the counter-offer and marks request as denied.
        """
        db = get_db_client()
        session = cls.get_session_by_id(session_id)
        if not session:
            return None

        # Transition status
        res = db.table("negotiation_sessions").update({"status": "declined", "updated_at": "now()"}).eq("id", str(session_id)).execute()
        updated_session = res.data[0]

        agent_id = UUID(session["agent_id"])
        request_id = UUID(session["request_id"])

        # Update request status
        db.table("agent_requests").update({"status": "denied"}).eq("id", str(request_id)).execute()

        # Log audit trail
        audit_data = AuditEventCreate(
            merchant_id=merchant_id,
            agent_id=agent_id,
            request_id=request_id,
            event_type="NEGOTIATION_DECLINED",
            actor_type="agent",
            actor_id=str(agent_id),
            entity_type="negotiation",
            entity_id=str(session_id),
            action="decline_negotiation",
            decision="ALLOW",
            details={}
        )
        AuditService.create_audit_event(audit_data)
        return updated_session
