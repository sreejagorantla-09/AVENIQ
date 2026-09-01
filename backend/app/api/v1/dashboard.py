from fastapi import APIRouter, HTTPException
from app.db.client import supabase_client
from app.services.audit_service import AuditService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/stats")
def get_dashboard_stats():
    """
    Returns aggregated metrics and recent activity for the AVENIQ Control Plane.
    """
    if supabase_client is None:
        return {
            "total_products": 0,
            "active_products": 0,
            "total_agents": 0,
            "total_requests": 0,
            "total_policies": 0,
            "recent_activity": [],
            "health": {
                "service": "online",
                "database": "unconfigured"
            }
        }

    try:
        # Get product counts
        prod_res = supabase_client.table("products").select("id, status", count="exact").execute()
        total_products = len(prod_res.data) if prod_res.data else 0
        active_products = sum(1 for p in prod_res.data if p["status"] == "active") if prod_res.data else 0

        # Get agents count
        agent_res = supabase_client.table("ai_agents").select("id", count="exact").execute()
        total_agents = agent_res.count if agent_res.count is not None else len(agent_res.data)

        # Get requests count
        req_res = supabase_client.table("agent_requests").select("id", count="exact").execute()
        total_requests = req_res.count if req_res.count is not None else len(req_res.data)

        # Get policies count
        policy_res = supabase_client.table("merchant_policies").select("id", count="exact").execute()
        total_policies = policy_res.count if policy_res.count is not None else len(policy_res.data)

        # Get recent activity (recent audit events)
        recent_activity = supabase_client.table("audit_events") \
            .select("*") \
            .order("created_at", desc=True) \
            .limit(5) \
            .execute() \
            .data

        return {
            "total_products": total_products,
            "active_products": active_products,
            "total_agents": total_agents,
            "total_requests": total_requests,
            "total_policies": total_policies,
            "recent_activity": recent_activity or [],
            "health": {
                "service": "online",
                "database": "connected"
            }
        }
    except Exception as e:
        # Fallback in case of database connectivity issues
        return {
            "total_products": 0,
            "active_products": 0,
            "total_agents": 0,
            "total_requests": 0,
            "total_policies": 0,
            "recent_activity": [],
            "health": {
                "service": "online",
                "database": "disconnected"
            }
        }

@router.post("/trust-score/recalculate")
def recalculate_merchant_trust_score():
    """
    Triggers dynamic recalculation of the merchant's trust score.
    """
    try:
        from uuid import UUID
        from app.services.merchant_service import MerchantService
        merchant = MerchantService.get_active_merchant()
        if not merchant:
            raise HTTPException(status_code=404, detail="Active merchant profile not found.")
        
        merchant_id = UUID(merchant["id"])
        new_score = MerchantService.recalculate_trust_score(merchant_id)
        return {"success": True, "trust_score": new_score}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to recalculate trust score: {str(e)}")
