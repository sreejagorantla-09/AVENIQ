import logging
from typing import Optional
from supabase import create_client, Client
from app.core.config import settings

logger = logging.getLogger("aveniq.db")

# Initialize client as None
supabase_client: Optional[Client] = None

# Only initialize if credentials are provided
if not settings.SUPABASE_URL or not settings.SUPABASE_SECRET_KEY:
    logger.warning(
        "Supabase credentials (SUPABASE_URL / SUPABASE_SECRET_KEY) are missing in environment. "
        "Database integration will run in offline/unconfigured mode."
    )
else:
    try:
        supabase_client = create_client(
            supabase_url=settings.SUPABASE_URL,
            supabase_key=settings.SUPABASE_SECRET_KEY
        )
        logger.info("Supabase client initialized successfully using service_role credentials.")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}", exc_info=True)
        supabase_client = None

def get_db_client() -> Client:
    """
    Dependency injection helper or service getter.
    Raises RuntimeError if client is not configured.
    """
    if supabase_client is None:
        raise RuntimeError("Database client is not initialized. Check your environment variables.")
    return supabase_client
