from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from app.services.approval_service import ApprovalService
from app.services.merchant_service import MerchantService

router = APIRouter(prefix="/approvals", tags=["Approvals"])

class ApprovalDecisionRequest(BaseModel):
    decision: str  # "approve" or "reject"

@router.get("")
@router.get("/pending")
def list_pending_approvals(x_agent_api_key: Optional[str] = Header(None)):
    """
    Lists all pending human-in-the-loop approvals for the active merchant.
    """
    if x_agent_api_key is not None:
        raise HTTPException(status_code=403, detail="Agent credentials not permitted for merchant operations.")

    try:
        merchant = MerchantService.get_active_merchant()
        if not merchant:
            raise HTTPException(status_code=404, detail="Active merchant profile not found.")
        
        merchant_id = UUID(merchant["id"])
        approvals = ApprovalService.get_pending_approvals(merchant_id)
        return approvals
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing pending approvals: {str(e)}")

@router.post("/{approval_id}/decision")
def submit_approval_decision(
    approval_id: UUID,
    payload: ApprovalDecisionRequest,
    x_agent_api_key: Optional[str] = Header(None)
):
    """
    Submits a merchant's approve/reject decision for a pending approval.
    """
    if x_agent_api_key is not None:
        raise HTTPException(status_code=403, detail="Agents cannot decide on approval queues.")

    if payload.decision not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Decision must be 'approve' or 'reject'.")

    try:
        merchant = MerchantService.get_active_merchant()
        if not merchant:
            raise HTTPException(status_code=404, detail="Active merchant profile not found.")
        
        merchant_id = UUID(merchant["id"])
        result = ApprovalService.submit_approval_decision(approval_id, payload.decision, merchant_id)
        if not result:
            raise HTTPException(status_code=404, detail="Approval request not found.")
            
        return {"success": True, "status": result["status"]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting approval decision: {str(e)}")

@router.post("/{approval_id}/approve")
def approve_request(
    approval_id: UUID,
    x_agent_api_key: Optional[str] = Header(None)
):
    """
    Shortcut endpoint to approve a pending approval.
    """
    return submit_approval_decision(approval_id, ApprovalDecisionRequest(decision="approve"), x_agent_api_key)

@router.post("/{approval_id}/reject")
def reject_request(
    approval_id: UUID,
    x_agent_api_key: Optional[str] = Header(None)
):
    """
    Shortcut endpoint to reject a pending approval.
    """
    return submit_approval_decision(approval_id, ApprovalDecisionRequest(decision="reject"), x_agent_api_key)
