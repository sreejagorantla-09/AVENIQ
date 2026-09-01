from typing import List, Optional
from uuid import UUID
from app.db.client import get_db_client
from app.schemas.models import AuditEventCreate
from app.services.audit_service import AuditService

class ApprovalService:
    @staticmethod
    def get_pending_approvals(merchant_id: UUID) -> List[dict]:
        """
        Retrieves all pending approvals for a merchant, joining with agent_requests to show details.
        """
        db = get_db_client()
        response = db.table("approvals") \
            .select("*, agent_requests(*, ai_agents(agent_code, name), policy_decisions(*))") \
            .eq("merchant_id", str(merchant_id)) \
            .eq("status", "pending") \
            .execute()
        
        formatted = []
        for item in (response.data or []):
            req = item.get("agent_requests") or {}
            agent_data = req.get("ai_agents") or {}
            intent = req.get("structured_intent") or {}
            qty = float(intent.get("quantity") or 1)
            unit_p = float(intent.get("price") or intent.get("unit_price") or 2499.0)
            
            formatted.append({
                "id": item["id"],
                "agent_id": item.get("agent_id") or req.get("agent_id") or "agent_001",
                "agent_code": agent_data.get("agent_code") or "AVENIQ_AGENT_001",
                "agent_name": agent_data.get("name") or "Smart Purchaser Agent",
                "proposal_id": item.get("request_id") or req.get("id"),
                "amount": float(item.get("amount") or (qty * unit_p)),
                "currency": item.get("currency") or "INR",
                "reason": item.get("reason") or "Exceeds spending limit threshold requiring human authorization.",
                "status": "PENDING",
                "risk_score": item.get("risk_score") or 75,
                "created_at": item.get("created_at")
            })
        return formatted

    @staticmethod
    def submit_approval_decision(approval_id: UUID, decision: str, merchant_id: UUID) -> Optional[dict]:
        """
        Submits merchant decision on a pending approval.
        Updates approval and request status. If approved, creates checkout transaction.
        decision is expected to be 'approve' or 'reject'.
        """
        db = get_db_client()
        
        # 1. Fetch approval context
        app_res = db.table("approvals").select("*").eq("id", str(approval_id)).eq("merchant_id", str(merchant_id)).execute()
        if not app_res.data:
            return None
        approval = app_res.data[0]
        request_id = UUID(approval["request_id"])
        
        # 2. Fetch associated request
        req_res = db.table("agent_requests").select("*").eq("id", str(request_id)).execute()
        if not req_res.data:
            return None
        request_record = req_res.data[0]
        agent_id = UUID(request_record["agent_id"]) if request_record.get("agent_id") else None
        
        # 3. Update approval status
        app_status = "approved" if decision == "approve" else "rejected"
        db.table("approvals").update({"status": app_status}).eq("id", str(approval_id)).execute()
        
        # 4. Update request status
        req_status = "approved" if decision == "approve" else "denied"
        db.table("agent_requests").update({"status": req_status}).eq("id", str(request_id)).execute()
        
        # 5. Log audit event for decision
        audit_event_type = "REQUEST_APPROVED" if decision == "approve" else "REQUEST_DENIED"
        audit_data = AuditEventCreate(
            merchant_id=merchant_id,
            agent_id=agent_id,
            request_id=request_id,
            event_type=audit_event_type,
            actor_type="merchant",
            actor_id="merchant-admin",
            entity_type="approval",
            entity_id=str(approval_id),
            action="submit_approval_decision",
            decision="ALLOW",
            details={"decision": decision, "request_id": str(request_id)}
        )
        AuditService.create_audit_event(audit_data)
        
        # 6. If approved, insert checkout transaction
        if decision == "approve":
            intent = request_record.get("structured_intent") or {}
            sku = intent.get("sku")
            quantity = int(intent.get("quantity") or 0)
            price = float(intent.get("price") or intent.get("unit_price") or 0.0)
            
            # Query product_id and stock matching sku (Requirement 6: Concurrency Stock Guard)
            product_id = None
            if sku:
                prod_res = db.table("products").select("id, stock_quantity").eq("sku", sku).execute()
                if prod_res.data:
                    product = prod_res.data[0]
                    if int(product.get("stock_quantity", 999999)) < quantity:
                        # Insufficient stock at checkout release
                        fail_audit = AuditEventCreate(
                            merchant_id=merchant_id,
                            agent_id=agent_id,
                            request_id=request_id,
                            event_type="TRANSACTION_FAILED",
                            actor_type="system",
                            actor_id="checkout-guard",
                            entity_type="transaction",
                            entity_id=str(approval_id),
                            action="create_transaction",
                            decision="DENY",
                            details={"amount": quantity * price, "reason": "Insufficient stock at manual approval release"}
                        )
                        AuditService.create_audit_event(fail_audit)
                        return {"status": "declined", "error": "Insufficient stock at manual approval release"}
                    product_id = product["id"]
                    
            tx_payload = {
                "merchant_id": str(merchant_id),
                "request_id": str(request_id),
                "product_id": str(product_id) if product_id else None,
                "amount": float(quantity * price),
                "currency": "INR",
                "payment_provider": "razorpay",
                "status": "pending",
                "metadata": {
                    "sku": sku,
                    "quantity": quantity,
                    "price": price,
                    "detailed_status": "payment_pending",
                    "agent_id": str(agent_id) if agent_id else None
                }
            }
            tx_res = db.table("transactions").insert(tx_payload).execute()
            if tx_res.data:
                transaction_id = tx_res.data[0]["id"]
                # Log transaction created audit event
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
                    details={
                        "amount": quantity * price,
                        "status": "payment_pending",
                        "approval_id": str(approval_id),
                        "agent_id": str(agent_id) if agent_id else None
                    }
                )
                AuditService.create_audit_event(tx_audit)
                
        return {"status": app_status, "request_id": str(request_id)}
