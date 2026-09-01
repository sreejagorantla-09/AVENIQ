from fastapi import APIRouter, HTTPException, Path
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from app.schemas.models import MerchantResponse
from app.services.merchant_service import MerchantService

router = APIRouter(prefix="/merchants", tags=["Merchants"])

class MerchantUpdate(BaseModel):
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    description: Optional[str] = None
    website_url: Optional[str] = None
    country: Optional[str] = None
    currency: Optional[str] = None

@router.get("/active", response_model=MerchantResponse)
def get_active_merchant():
    """
    Retrieve the active Merchant Commerce Passport.
    """
    try:
        merchant = MerchantService.get_active_merchant()
        if not merchant:
            raise HTTPException(status_code=404, detail="Active merchant profile not found.")
        return merchant
    except HTTPException:
        raise
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Database service not available or unconfigured")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{merchant_id}", response_model=MerchantResponse)
def update_merchant(
    merchant_id: UUID = Path(..., description="The UUID of the merchant to update"),
    update_data: MerchantUpdate = ...
):
    """
    Update details of the Merchant Commerce Passport.
    """
    try:
        data = {k: v for k, v in update_data.model_dump().items() if v is not None}
        if not data:
            raise HTTPException(status_code=400, detail="No update fields provided.")
            
        merchant = MerchantService.update_merchant(merchant_id, data)
        if not merchant:
            raise HTTPException(status_code=404, detail="Merchant profile not found.")
        return merchant
    except HTTPException:
        raise
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Database service not available or unconfigured")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
