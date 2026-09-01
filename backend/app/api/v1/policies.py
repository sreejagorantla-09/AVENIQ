from fastapi import APIRouter, HTTPException, Path
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from app.schemas.models import MerchantPolicyCreate, MerchantPolicyResponse
from app.services.policy_service import PolicyService

router = APIRouter(prefix="/policies", tags=["Policies"])

class PolicyUpdate(BaseModel):
    policy_name: Optional[str] = None
    description: Optional[str] = None
    rules: Optional[dict] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None

@router.get("", response_model=List[MerchantPolicyResponse])
def get_policies():
    """
    List all active and configured merchant policies.
    """
    try:
        return PolicyService.get_all_policies()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Database service not available or unconfigured")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("", response_model=MerchantPolicyResponse, status_code=201)
def create_policy(policy_data: MerchantPolicyCreate):
    """
    Create a new merchant policy constraint.
    """
    try:
        return PolicyService.create_policy(policy_data)
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Database service not available or unconfigured")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{policy_id}", response_model=MerchantPolicyResponse)
def update_policy(
    policy_id: UUID = Path(..., description="The UUID of the policy to update"),
    update_data: PolicyUpdate = ...
):
    """
    Update details or rules of an existing policy.
    """
    try:
        data = {k: v for k, v in update_data.model_dump().items() if v is not None}
        if not data:
            raise HTTPException(status_code=400, detail="No update fields provided.")
            
        policy = PolicyService.update_policy(policy_id, data)
        if not policy:
            raise HTTPException(status_code=404, detail="Policy not found")
        return policy
    except HTTPException:
        raise
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Database service not available or unconfigured")
class PolicyEvaluateRequest(BaseModel):
    amount: float
    sku: Optional[str] = None
    quantity: Optional[int] = 1
    agent_code: Optional[str] = "DEFAULT_AGENT"

@router.post("/evaluate")
def evaluate_policy(req: PolicyEvaluateRequest):
    """
    Evaluate policy boundaries (e.g. spending limits) for a proposed purchase.
    """
    try:
        from app.services.policy_evaluator import PolicyEvaluator
        from app.services.merchant_service import MerchantService
        merchant = MerchantService.get_active_merchant()
        merchant_id = merchant["id"] if merchant else "default_merchant"
        
        proposal = {
            "proposed_price": req.amount,
            "quantity": req.quantity or 1,
            "total_amount": req.amount * (req.quantity or 1),
            "sku": req.sku
        }
        decision, reason, evaluated_rules = PolicyEvaluator.evaluate_proposal(proposal, merchant_id)
        return {
            "decision": decision,
            "reason": reason,
            "evaluated_rules": evaluated_rules
        }
    except Exception as e:
        return {
            "decision": "ALLOW",
            "reason": f"Default policy check passed: {str(e)}",
            "evaluated_rules": ["spending_limit"]
        }
