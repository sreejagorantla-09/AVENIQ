from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from uuid import UUID
from app.services.negotiation_service import NegotiationService
from app.services.merchant_service import MerchantService

router = APIRouter(prefix="/negotiations", tags=["Negotiations"])

@router.get("")
def list_negotiation_sessions(x_agent_api_key: Optional[str] = Header(None)):
    """
    Lists all negotiation sessions for the active merchant.
    Blocked for agent keys.
    """
    if x_agent_api_key is not None:
        raise HTTPException(status_code=403, detail="Agent credentials not permitted for merchant operations.")
        
    try:
        merchant = MerchantService.get_active_merchant()
        if not merchant:
            raise HTTPException(status_code=404, detail="Active merchant profile not found.")
            
        merchant_id = UUID(merchant["id"])
        sessions = NegotiationService.get_all_sessions(merchant_id)
        return sessions
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch negotiations: {str(e)}")
