from fastapi import APIRouter, Response
from app.db.client import supabase_client

router = APIRouter(tags=["Health"])

@router.get("/health")
def get_health(response: Response):
    """
    Standard health check endpoint integrated with database connectivity validation.
    """
    database_status = "disconnected"
    
    if supabase_client is None:
        database_status = "unconfigured"
    else:
        try:
            # Lightweight connectivity query
            supabase_client.table("merchants").select("id").limit(1).execute()
            database_status = "connected"
        except Exception:
            database_status = "disconnected"
            
    status = "ok"
    if database_status == "disconnected":
        status = "degraded"
        response.status_code = 503  # Service Unavailable if DB connection fails
        
    return {
        "status": status,
        "service": "aveniq-api",
        "database": database_status
    }
