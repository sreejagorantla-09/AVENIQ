from fastapi import APIRouter
from app.core.config import settings
from app.db.client import supabase_client

router = APIRouter(prefix="/integrations", tags=["Integrations"])

@router.get("/status")
def get_integrations_status():
    """
    Returns the configuration and connectivity status of AVENIQ integrations.
    """
    # 1. Supabase status
    supabase_status = "unconfigured"
    if settings.SUPABASE_URL and settings.SUPABASE_SECRET_KEY:
        if supabase_client is not None:
            try:
                # Test connection query
                supabase_client.table("merchants").select("id").limit(1).execute()
                supabase_status = "connected"
            except Exception:
                supabase_status = "disconnected"
        else:
            supabase_status = "disconnected"

    # 2. Gemini status
    gemini_status = "unconfigured"
    if settings.GEMINI_API_KEY:
        gemini_status = "connected"

    # 3. Razorpay status
    razorpay_status = "unconfigured"
    if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
        razorpay_status = "connected"

    return {
        "supabase": {
            "name": "Supabase Database",
            "status": supabase_status,
            "details": f"URL: {settings.SUPABASE_URL}" if settings.SUPABASE_URL else "Not configured"
        },
        "gemini": {
            "name": "Gemini AI Gateway",
            "status": gemini_status,
            "details": "API Key loaded successfully" if settings.GEMINI_API_KEY else "Not configured"
        },
        "razorpay": {
            "name": "Razorpay Sandbox Gateway",
            "status": razorpay_status,
            "details": f"Key ID: {settings.RAZORPAY_KEY_ID}" if settings.RAZORPAY_KEY_ID else "Not configured"
        }
    }
