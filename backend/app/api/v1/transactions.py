from fastapi import APIRouter, HTTPException, Header
from typing import Optional, List
from uuid import UUID
from app.db.client import get_db_client
from app.services.merchant_service import MerchantService

router = APIRouter(prefix="/transactions", tags=["Transactions"])

@router.get("")
def list_transactions(x_agent_api_key: Optional[str] = Header(None)):
    """
    Lists all settlement transactions for the active merchant.
    """
    try:
        db = get_db_client()
        merchant = MerchantService.get_active_merchant()
        if not merchant:
            return []
        
        merchant_id = merchant["id"]
        res = db.table("transactions") \
            .select("*, agent_requests(*, ai_agents(agent_code, name))") \
            .eq("merchant_id", str(merchant_id)) \
            .order("created_at", desc=True) \
            .execute()
            
        formatted = []
        for tx in (res.data or []):
            req = tx.get("agent_requests") or {}
            agent_data = req.get("ai_agents") or {}
            meta = tx.get("metadata") or {}
            
            status = tx.get("status", "pending")
            if meta.get("detailed_status") == "paid" or tx.get("provider_transaction_id"):
                status = "completed"
                
            formatted.append({
                "id": tx["id"],
                "created_at": tx["created_at"],
                "amount": float(tx.get("amount") or 0.0),
                "currency": tx.get("currency") or "INR",
                "status": status,
                "agent_id": meta.get("agent_id") or req.get("agent_id"),
                "agent_code": agent_data.get("agent_code") or "AVENIQ_AGENT_001",
                "agent_name": agent_data.get("name") or "Smart Purchaser Agent",
                "razorpay_order_id": meta.get("razorpay_order_id"),
                "razorpay_payment_id": tx.get("provider_transaction_id") or meta.get("razorpay_payment_id"),
                "fail_reason": None
            })
        return formatted
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list transactions: {str(e)}")
