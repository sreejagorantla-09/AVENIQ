from fastapi import APIRouter, Request, HTTPException, status
import hmac
import hashlib
import json
import logging
from uuid import UUID
from app.core.config import settings
from app.db.client import get_db_client
from app.schemas.models import AuditEventCreate
from app.services.audit_service import AuditService

logger = logging.getLogger("aveniq.payments")
router = APIRouter(prefix="/payments", tags=["Payments"])

@router.post("/webhook")
async def razorpay_webhook(request: Request):
    """
    Asynchronously processes Razorpay payment webhook notifications securely on the backend.
    """
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    # Webhook signature verification
    verified = False
    if settings.RAZORPAY_WEBHOOK_SECRET:
        try:
            expected = hmac.new(
                settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
                body,
                hashlib.sha256
            ).hexdigest()
            verified = hmac.compare_digest(expected, signature)
        except Exception as e:
            logger.error(f"Error calculating webhook HMAC signature: {e}")
    else:
        # Mock mode verification
        verified = True

    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature."
        )

    try:
        event_data = json.loads(body.decode("utf-8"))
        event_name = event_data.get("event")
        
        logger.info(f"Received payment webhook event: {event_name}")

        if event_name == "payment.captured":
            payload = event_data["payload"]["payment"]["entity"]
            order_id = payload.get("order_id")
            payment_id = payload.get("id")

            if order_id:
                db = get_db_client()
                
                # Fetch transaction matching metadata->>razorpay_order_id
                tx_res = db.table("transactions").select("*").eq("metadata->>razorpay_order_id", order_id).execute()
                if tx_res.data:
                    transaction = tx_res.data[0]
                    tx_id = transaction["id"]
                    tx_metadata = transaction.get("metadata") or {}
                    detailed_status = tx_metadata.get("detailed_status")
                    
                    if detailed_status != "paid":
                        tx_metadata["razorpay_payment_id"] = payment_id
                        tx_metadata["detailed_status"] = "paid"
                        
                        # Update status to completed to satisfy constraints
                        db.table("transactions") \
                            .update({
                                "status": "completed",
                                "provider_transaction_id": payment_id,
                                "metadata": tx_metadata
                            }) \
                            .eq("id", tx_id) \
                            .execute()

                        # Subtract stock
                        sku = transaction["metadata"].get("sku")
                        qty = int(transaction["metadata"].get("quantity", 0))
                        merchant_id = transaction["merchant_id"]
                        
                        if sku and qty > 0:
                            prod_res = db.table("products") \
                                .select("id, stock_quantity") \
                                .eq("sku", sku) \
                                .eq("merchant_id", merchant_id) \
                                .execute()
                            if prod_res.data:
                                p_id = prod_res.data[0]["id"]
                                current_stock = int(prod_res.data[0]["stock_quantity"])
                                db.table("products").update({"stock_quantity": max(0, current_stock - qty)}).eq("id", p_id).execute()

                        # Log webhook payment verification success
                        audit_success = AuditEventCreate(
                            merchant_id=UUID(merchant_id),
                            agent_id=UUID(transaction["agent_id"]) if transaction.get("agent_id") else None,
                            request_id=UUID(transaction["request_id"]) if transaction.get("request_id") else None,
                            event_type="PAYMENT_VERIFIED",
                            actor_type="system",
                            actor_id="payment-webhook",
                            entity_type="transaction",
                            entity_id=str(tx_id),
                            action="webhook_verify_payment",
                            decision="ALLOW",
                            details={"razorpay_payment_id": payment_id, "source": "webhook"}
                        )
                        AuditService.create_audit_event(audit_success)

        return {"status": "ok"}
    except Exception as e:
        logger.exception("Webhook execution failed")
        raise HTTPException(
            status_code=500,
            detail="Error processing payment webhook event"
        )
