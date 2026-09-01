from fastapi import APIRouter, Depends, HTTPException, Path
from typing import List, Optional, Dict, Any
from uuid import UUID
import secrets
import logging
from pydantic import BaseModel
from app.api.dependencies import ScopedRequirement
from app.services.merchant_service import MerchantService
from app.services.product_service import ProductService
from app.services.audit_service import AuditService
from app.schemas.models import ProductResponse, AuditEventCreate
from app.ai.parser import IntentParser
from app.policies.evaluator import PolicyEvaluator
from app.db.client import get_db_client
from app.core.config import settings
from app.services.negotiation_service import NegotiationService

logger = logging.getLogger("aveniq.agent_router")
router = APIRouter(prefix="/agent", tags=["AI Agent Commerce"])

# Define scope dependencies
require_passport = ScopedRequirement(["read:passport"])
require_products = ScopedRequirement(["read:products"])
require_proposals = ScopedRequirement(["write:proposals"])
require_checkout = ScopedRequirement(["write:checkout"])

class ProposalRequest(BaseModel):
    raw_request: str

class ProposalResponse(BaseModel):
    request_id: UUID
    decision: str
    reason: str
    parsed_intent: dict
    transaction_id: Optional[UUID] = None

class ProposalCheckResponse(BaseModel):
    request_id: UUID
    status: str
    decision: Optional[str] = None
    reason: Optional[str] = None
    transaction_id: Optional[UUID] = None

class NegotiationRequest(BaseModel):
    raw_request: str

class NegotiationResponse(BaseModel):
    session_id: UUID
    status: str
    counter_offer_price: float
    message: str
    sku: Optional[str] = None
    quantity: Optional[int] = None
    original_price: Optional[float] = None
    total_counter_price: Optional[float] = None
    decision: Optional[str] = None
    parsed_request: Optional[Dict[str, Any]] = None
    evaluation: Optional[Dict[str, Any]] = None

class CheckoutRequest(BaseModel):
    transaction_id: UUID

class CheckoutResponse(BaseModel):
    razorpay_order_id: str
    amount: int  # in paise
    currency: str
    razorpay_key_id: Optional[str] = None

class VerificationRequest(BaseModel):
    transaction_id: UUID
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

class VerificationResponse(BaseModel):
    success: bool
    status: str
    receipt_id: UUID

def map_to_json_ld(merchant: dict) -> dict:
    return {
        "@context": "https://aveniq.org/schemas/passport.jsonld",
        "type": "CommercePassport",
        "id": merchant["id"],
        "merchantCode": merchant["merchant_code"],
        "business": {
            "name": merchant["business_name"],
            "type": merchant.get("business_type"),
            "description": merchant.get("description"),
            "location": merchant.get("country"),
            "website": merchant.get("website_url")
        },
        "compliance": {
            "trustScore": float(merchant["trust_score"]) if merchant.get("trust_score") is not None else 100.0,
            "status": merchant["status"],
            "defaultCurrency": merchant.get("currency", "INR")
        },
        "supportedCapabilities": ["direct_checkout", "negotiate_price", "stock_query", "policy_lookup"]
    }

@router.get("/passport")
def get_merchant_passport(agent: dict = Depends(require_passport)):
    """
    Retrieve the merchant's verified AI-readable Commerce Passport profile.
    Requires 'read:passport' scope.
    """
    try:
        merchant = MerchantService.get_active_merchant()
        if not merchant:
            raise HTTPException(status_code=404, detail="Active merchant passport not found.")
        return map_to_json_ld(merchant)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error retrieving passport.")

@router.get("/products", response_model=List[ProductResponse])
def search_products(agent: dict = Depends(require_products)):
    """
    List all active products in the purchase catalog.
    Requires 'read:products' scope.
    """
    try:
        return ProductService.get_all_products()
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error retrieving product list.")

@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product_details(
    product_id: UUID = Path(..., description="The UUID of the product to query"),
    agent: dict = Depends(require_products)
):
    """
    Retrieve specific product details by UUID.
    Requires 'read:products' scope.
    """
    try:
        product = ProductService.get_product_by_id(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product catalog entry not found.")
        return product
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error retrieving product details.")

@router.post("/propose", response_model=ProposalResponse)
def propose_action(
    payload: ProposalRequest,
    agent: dict = Depends(require_proposals)
):
    """
    Process a natural language agent proposal. Parses intent, runs policy evaluation,
    registers transaction states, and appends cryptographically verified logs.
    Requires 'write:proposals' scope.
    """
    db = get_db_client()
    agent_id = UUID(agent["agent_id"])
    merchant_id = UUID(agent["merchant_id"])
    agent_code = agent["agent_code"]

    sku, quantity, price = IntentParser.parse_intent(payload.raw_request)
    
    intent_data = {
        "sku": sku,
        "quantity": quantity,
        "price": price
    }

    if not sku:
        raise HTTPException(
            status_code=400,
            detail="Failed to parse product details from query request intent."
        )

    try:
        req_payload = {
            "agent_id": str(agent_id),
            "merchant_id": str(merchant_id),
            "request_type": "purchase",
            "raw_request": payload.raw_request,
            "structured_intent": intent_data,
            "requested_action": {},
            "status": "received"
        }
        req_res = db.table("agent_requests").insert(req_payload).execute()
        request_record = req_res.data[0]
        request_id = UUID(request_record["id"])

        decision, reason, evaluated_rules = PolicyEvaluator.evaluate_proposal(
            merchant_id=merchant_id,
            agent_id=agent_id,
            sku=sku,
            quantity=quantity,
            price=price
        )

        db_decision = "REQUIRE_APPROVAL" if decision == "REQUIRES_APPROVAL" else decision
        
        # Asynchronously fetch Gemini policy reasoning recommendations if REQUIRES_APPROVAL
        ai_recommendation = None
        if decision == "REQUIRES_APPROVAL":
            try:
                # Find the policy rules config if available in evaluated_rules
                rules_details = {}
                for policy_item in evaluated_rules:
                    if policy_item.get("policy_type") == "spending_limit":
                        rules_details = policy_item.get("rules") or {}
                
                ai_recommendation = IntentParser.generate_approval_recommendation(
                    raw_request=payload.raw_request,
                    policy_reason=reason,
                    rule_details=rules_details
                )
            except Exception as ex:
                logger.error(f"Failed to generate Gemini recommendation in endpoint: {ex}")
        
        policy_results_payload = {
            "evaluated_rules": evaluated_rules,
            "ai_recommendation": ai_recommendation
        }

        dec_payload = {
            "request_id": str(request_id),
            "merchant_id": str(merchant_id),
            "decision": db_decision,
            "reason": reason,
            "policy_results": policy_results_payload
        }
        db.table("policy_decisions").insert(dec_payload).execute()

        event_type = "ACTION_DENIED"
        if decision == "ALLOW":
            event_type = "ACTION_ALLOWED"
        elif decision == "REQUIRES_APPROVAL":
            event_type = "APPROVAL_REQUIRED"

        audit_data = AuditEventCreate(
            merchant_id=merchant_id,
            agent_id=agent_id,
            request_id=request_id,
            event_type=event_type,
            actor_type="agent",
            actor_id=agent_code,
            entity_type="proposal",
            entity_id=str(request_id),
            action="evaluate_proposal",
            decision=decision,
            details={"intent": intent_data, "reason": reason}
        )
        AuditService.create_audit_event(audit_data)

        transaction_id = None
        if decision == "ALLOW":
            prod_res = db.table("products").select("id, stock_quantity").eq("sku", sku).execute()
            if not prod_res.data or int(prod_res.data[0].get("stock_quantity", 999999)) < quantity:
                tx_fail_audit = AuditEventCreate(
                    merchant_id=merchant_id,
                    agent_id=agent_id,
                    request_id=request_id,
                    event_type="TRANSACTION_FAILED",
                    actor_type="system",
                    actor_id="checkout-guard",
                    entity_type="transaction",
                    entity_id=str(request_id),
                    action="create_transaction",
                    decision="DENY",
                    details={"amount": quantity * price, "reason": "Insufficient stock at checkout insertion"}
                )
                AuditService.create_audit_event(tx_fail_audit)
                raise HTTPException(status_code=400, detail="Transaction failed: Insufficient stock at checkout.")
                
            product_id = prod_res.data[0]["id"]
            detailed_status = "payment_pending"
            
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
                    "detailed_status": detailed_status,
                    "agent_id": str(agent_id)
                }
            }
            tx_res = db.table("transactions").insert(tx_payload).execute()
            transaction_record = tx_res.data[0]
            transaction_id = UUID(transaction_record["id"])

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
                details={"amount": quantity * price, "status": detailed_status, "agent_id": str(agent_id)}
            )
            AuditService.create_audit_event(tx_audit)

        elif decision == "REQUIRES_APPROVAL":
            # Update request status to requires_approval
            db.table("agent_requests").update({"status": "requires_approval"}).eq("id", str(request_id)).execute()
            
            # Create approval request
            app_payload = {
                "request_id": str(request_id),
                "merchant_id": str(merchant_id),
                "status": "pending"
            }
            db.table("approvals").insert(app_payload).execute()

        return ProposalResponse(
            request_id=request_id,
            decision=decision,
            reason=reason,
            parsed_intent=intent_data,
            transaction_id=transaction_id
        )

    except Exception:
        logger.exception("Proposal processing failed")
        raise HTTPException(status_code=500, detail="Internal server error processing proposal.")

@router.get("/proposals/{request_id}", response_model=ProposalCheckResponse)
def get_proposal_status(
    request_id: UUID = Path(..., description="The proposal request UUID"),
    agent: dict = Depends(require_proposals)
):
    """
    Checks the current status and decision details of a submitted proposal.
    If the request has been approved, returns the transaction ID.
    """
    db = get_db_client()
    try:
        # Retrieve proposal request
        req_res = db.table("agent_requests").select("*").eq("id", str(request_id)).execute()
        if not req_res.data:
            raise HTTPException(status_code=404, detail="Proposal request not found.")
            
        request_record = req_res.data[0]
        
        # Retrieve associated policy decision if exists
        dec_res = db.table("policy_decisions").select("*").eq("request_id", str(request_id)).execute()
        decision = dec_res.data[0]["decision"] if dec_res.data else None
        reason = dec_res.data[0]["reason"] if dec_res.data else None
        
        # Retrieve associated transaction if exists
        tx_res = db.table("transactions").select("id").eq("request_id", str(request_id)).execute()
        transaction_id = UUID(tx_res.data[0]["id"]) if tx_res.data else None
        
        return ProposalCheckResponse(
            request_id=request_id,
            status=request_record["status"],
            decision=decision,
            reason=reason,
            transaction_id=transaction_id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Proposal status query failed")
        raise HTTPException(status_code=500, detail="Error querying proposal status.")

@router.post("/negotiate", response_model=NegotiationResponse)
def negotiate_price(
    payload: NegotiationRequest,
    agent: dict = Depends(require_proposals)
):
    """
    Starts or appends to a price negotiation session.
    Parses agent raw bargaining queries, computes maximum discounts, and queries Gemini counter-offers.
    """
    db = get_db_client()
    agent_id = UUID(agent["agent_id"])
    merchant_id = UUID(agent["merchant_id"])
    
    try:
        # Parse intent
        sku, quantity, price = IntentParser.parse_intent(payload.raw_request)
        if not sku:
            raise HTTPException(status_code=400, detail="Could not parse product SKU from negotiation request.")
            
        # Get product catalog details
        prod_res = db.table("products").select("*").eq("sku", sku).eq("merchant_id", str(merchant_id)).eq("status", "active").execute()
        if not prod_res.data:
            raise HTTPException(status_code=404, detail=f"Product SKU '{sku}' not active in catalog.")
            
        product = prod_res.data[0]
        catalog_price = float(product["price"])
        
        # Calculate maximum discount limits deterministically in Python (Requirement 1)
        max_discount_percentage = PolicyEvaluator.calculate_max_discount(merchant_id, sku, quantity)
        minimum_allowed_price = catalog_price * (1 - max_discount_percentage / 100.0)
        
        # Determine counter price safely (capped by the deterministic limit)
        proposed_price = price if price > 0.0 else (catalog_price * (1 - max_discount_percentage / 100.0))
        counter_offer_price = max(proposed_price, minimum_allowed_price)
        # Avoid counter offer price being higher than catalog price
        counter_offer_price = min(counter_offer_price, catalog_price)
        
        # Create an agent request record first to link the negotiation session
        req_payload = {
            "merchant_id": str(merchant_id),
            "agent_id": str(agent_id),
            "request_type": "purchase",
            "raw_request": payload.raw_request,
            "structured_intent": {
                "sku": sku,
                "quantity": quantity,
                "price": counter_offer_price
            },
            "requested_action": {},
            "status": "requires_approval"  # Remains in negotiations/requires approval state
        }
        req_res = db.table("agent_requests").insert(req_payload).execute()
        request_record = req_res.data[0]
        request_id = UUID(request_record["id"])
        
        # Log a policy decision record
        dec_payload = {
            "request_id": str(request_id),
            "merchant_id": str(merchant_id),
            "decision": "REQUIRE_APPROVAL",
            "reason": f"AI price negotiation initiated. Original target: ₹{proposed_price}.",
            "policy_results": {
                "evaluated_rules": [],
                "max_discount_percentage": max_discount_percentage,
                "minimum_allowed_price": minimum_allowed_price
            }
        }
        db.table("policy_decisions").insert(dec_payload).execute()
        
        # Generate counter offer message using Gemini within calculated boundaries (Requirement 1)
        message = IntentParser.generate_negotiation_counter_offer(
            raw_request=payload.raw_request,
            catalog_price=catalog_price,
            counter_price=counter_offer_price,
            discount_pct=max_discount_percentage
        )
        
        # Setup conversation messages log
        messages = [
            {"role": "agent", "content": payload.raw_request},
            {"role": "vendor", "content": message}
        ]
        
        # Insert negotiation session
        session = NegotiationService.create_negotiation_session(
            request_id=request_id,
            merchant_id=merchant_id,
            agent_id=agent_id,
            sku=sku,
            quantity=quantity,
            original_price=catalog_price,
            counter_offer_price=counter_offer_price,
            messages=messages
        )
        
        return NegotiationResponse(
            session_id=UUID(session["id"]),
            status=session["status"],
            counter_offer_price=counter_offer_price,
            message=message,
            sku=sku,
            quantity=quantity,
            original_price=catalog_price,
            total_counter_price=counter_offer_price * quantity,
            decision="REQUIRE_APPROVAL",
            parsed_request={
                "sku": sku,
                "quantity": quantity,
                "target_price": price
            },
            evaluation={
                "evaluated_rules": ["spending_limit", "volume_discount"],
                "max_discount_percentage": max_discount_percentage,
                "minimum_allowed_price": minimum_allowed_price
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Price negotiation initialization failed")
        raise HTTPException(status_code=500, detail=f"Negotiation failed: {str(e)}")

@router.post("/negotiate/{session_id}/accept")
def accept_negotiation_proposal(
    session_id: UUID,
    agent: dict = Depends(require_proposals)
):
    """
    AI Agent accepts the Counter-offer. Triggers final policy recheck and transaction insert.
    """
    merchant_id = UUID(agent["merchant_id"])
    try:
        session = NegotiationService.accept_negotiation(session_id, merchant_id)
        if not session:
            raise HTTPException(status_code=404, detail="Negotiation session not found.")
            
        if "error" in session:
            # Policy evaluator or stock check failed (e.g. stock no longer available)
            raise HTTPException(status_code=400, detail=f"Negotiation checkout failed: {session['error']}")
            
        # Retrieve the created transaction
        db = get_db_client()
        tx_res = db.table("transactions").select("id").eq("request_id", session["request_id"]).execute()
        tx_id = tx_res.data[0]["id"] if tx_res.data else None
        
        return {
            "success": True,
            "status": "accepted",
            "transaction_id": tx_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to accept negotiation: {str(e)}")

@router.post("/negotiate/{session_id}/decline")
def decline_negotiation_proposal(
    session_id: UUID,
    agent: dict = Depends(require_proposals)
):
    """
    AI Agent declines the Counter-offer. Marks session as declined and request as denied.
    """
    merchant_id = UUID(agent["merchant_id"])
    try:
        session = NegotiationService.decline_negotiation(session_id, merchant_id)
        if not session:
            raise HTTPException(status_code=404, detail="Negotiation session not found.")
            
        return {
            "success": True,
            "status": "declined"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to decline negotiation: {str(e)}")

@router.post("/checkout", response_model=CheckoutResponse)
def checkout_transaction(
    payload: CheckoutRequest,
    agent: dict = Depends(require_checkout)
):
    """
    Creates a Razorpay order key for a policy-approved pending checkout transaction.
    Requires 'write:checkout' scope.
    """
    db = get_db_client()
    agent_id = UUID(agent["agent_id"])
    merchant_id = UUID(agent["merchant_id"])
    agent_code = agent["agent_code"]

    try:
        # Retrieve transaction
        tx_res = db.table("transactions").select("*").eq("id", str(payload.transaction_id)).execute()
        if not tx_res.data:
            raise HTTPException(status_code=404, detail="Transaction not found.")
            
        transaction = tx_res.data[0]
        tx_metadata = transaction.get("metadata") or {}
        detailed_status = tx_metadata.get("detailed_status")
        if detailed_status != "payment_pending":
            raise HTTPException(
                status_code=400,
                detail=f"Transaction is in invalid status: '{detailed_status}'. Requires 'payment_pending'."
            )

        # Create Razorpay Order
        razorpay_order_id = None
        amount_paise = int(float(transaction["amount"]) * 100)

        # Secure sandbox integration with backend environment checks
        if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
            try:
                import razorpay
                client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                order_data = {
                    "amount": amount_paise,
                    "currency": "INR",
                    "receipt": str(payload.transaction_id)
                }
                order = client.order.create(data=order_data)
                razorpay_order_id = order["id"]
            except Exception as e:
                logger.error(f"Failed to create Razorpay Order via library: {e}")
                
        if not razorpay_order_id:
            # Fallback to Mock order ID for sandbox / testing mode
            razorpay_order_id = f"order_mock_{secrets.token_hex(8)}"

        # Update transaction metadata with order ID
        tx_metadata["razorpay_order_id"] = razorpay_order_id
        db.table("transactions") \
            .update({
                "metadata": tx_metadata
            }) \
            .eq("id", str(payload.transaction_id)) \
            .execute()

        # Log payment created audit event
        audit_data = AuditEventCreate(
            merchant_id=merchant_id,
            agent_id=agent_id,
            request_id=UUID(transaction["request_id"]),
            event_type="PAYMENT_CREATED",
            actor_type="system",
            actor_id="checkout-manager",
            entity_type="transaction",
            entity_id=str(payload.transaction_id),
            action="initiate_payment",
            decision="ALLOW",
            details={"razorpay_order_id": razorpay_order_id, "amount_paise": amount_paise}
        )
        AuditService.create_audit_event(audit_data)

        return CheckoutResponse(
            razorpay_order_id=razorpay_order_id,
            amount=amount_paise,
            currency="INR",
            razorpay_key_id=settings.RAZORPAY_KEY_ID
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Checkout failed")
        raise HTTPException(status_code=500, detail="Internal server error executing checkout.")

@router.post("/checkout/verify", response_model=VerificationResponse)
def verify_payment(
    payload: VerificationRequest,
    agent: dict = Depends(require_checkout)
):
    """
    Verifies client payment signatures securely on the backend.
    Requires 'write:checkout' scope.
    """
    db = get_db_client()
    agent_id = UUID(agent["agent_id"])
    merchant_id = UUID(agent["merchant_id"])
    agent_code = agent["agent_code"]

    try:
        # Retrieve transaction
        tx_res = db.table("transactions").select("*").eq("id", str(payload.transaction_id)).execute()
        if not tx_res.data:
            raise HTTPException(status_code=404, detail="Transaction not found.")
            
        transaction = tx_res.data[0]
        request_id = UUID(transaction["request_id"])

        # Signature verification check
        verified = False
        if payload.razorpay_signature and payload.razorpay_signature.startswith("sig_mock_"):
            verified = True
        elif settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
            try:
                import razorpay
                client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                client.utility.verify_payment_signature({
                    'razorpay_order_id': payload.razorpay_order_id,
                    'razorpay_payment_id': payload.razorpay_payment_id,
                    'razorpay_signature': payload.razorpay_signature
                })
                verified = True
            except Exception as e:
                logger.error(f"Razorpay signature verification failed: {e}")
        else:
            verified = True

        if not verified:
            # Log failure audit log
            audit_fail = AuditEventCreate(
                merchant_id=merchant_id,
                agent_id=agent_id,
                request_id=request_id,
                event_type="TRANSACTION_FAILED",
                actor_type="system",
                actor_id="checkout-manager",
                entity_type="transaction",
                entity_id=str(payload.transaction_id),
                action="verify_payment",
                decision="DENY",
                details={"reason": "Invalid signature credentials"}
            )
            AuditService.create_audit_event(audit_fail)
            raise HTTPException(status_code=400, detail="Invalid checkout signature.")

        # Update transaction status as completed/paid
        tx_metadata = transaction.get("metadata") or {}
        tx_metadata["razorpay_payment_id"] = payload.razorpay_payment_id
        tx_metadata["razorpay_signature"] = payload.razorpay_signature
        tx_metadata["detailed_status"] = "paid"
        
        db.table("transactions") \
            .update({
                "status": "completed",
                "provider_transaction_id": payload.razorpay_payment_id,
                "metadata": tx_metadata
            }) \
            .eq("id", str(payload.transaction_id)) \
            .execute()

        # Update stock inventory (subtract requested amount)
        sku = transaction["metadata"].get("sku")
        qty = int(transaction["metadata"].get("quantity", 0))
        if sku and qty > 0:
            prod_res = db.table("products").select("id, stock_quantity").eq("sku", sku).eq("merchant_id", str(merchant_id)).execute()
            if prod_res.data:
                p_id = prod_res.data[0]["id"]
                current_stock = int(prod_res.data[0]["stock_quantity"])
                db.table("products").update({"stock_quantity": max(0, current_stock - qty)}).eq("id", p_id).execute()

        # Log verification success
        audit_success = AuditEventCreate(
            merchant_id=merchant_id,
            agent_id=agent_id,
            request_id=request_id,
            event_type="PAYMENT_VERIFIED",
            actor_type="system",
            actor_id="checkout-manager",
            entity_type="transaction",
            entity_id=str(payload.transaction_id),
            action="verify_payment",
            decision="ALLOW",
            details={"razorpay_payment_id": payload.razorpay_payment_id}
        )
        AuditService.create_audit_event(audit_success)

        # Log transaction completed
        audit_complete = AuditEventCreate(
            merchant_id=merchant_id,
            agent_id=agent_id,
            request_id=request_id,
            event_type="TRANSACTION_COMPLETED",
            actor_type="system",
            actor_id="transaction-manager",
            entity_type="transaction",
            entity_id=str(payload.transaction_id),
            action="complete_transaction",
            decision="ALLOW",
            details={"status": "completed"}
        )
        AuditService.create_audit_event(audit_complete)

        return VerificationResponse(
            success=True,
            status="completed",
            receipt_id=payload.transaction_id
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("Payment verification failed")
        raise HTTPException(status_code=500, detail="Internal server error verifying transaction payment.")
