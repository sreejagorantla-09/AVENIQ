from typing import Optional
from uuid import UUID
from app.db.client import get_db_client
from app.schemas.models import AgentRequestCreate

class RequestService:
    @staticmethod
    def create_request(request_data: AgentRequestCreate) -> dict:
        """
        Creates an agent request (proposal) in the database.
        """
        db = get_db_client()
        data = {
            "agent_id": str(request_data.agent_id),
            "merchant_id": str(request_data.merchant_id),
            "request_type": request_data.request_type,
            "raw_request": request_data.raw_request,
            "structured_intent": request_data.structured_intent,
            "requested_action": request_data.requested_action,
            "status": request_data.status,
        }
        response = db.table("agent_requests").insert(data).execute()
        return response.data[0]

    @staticmethod
    def get_request_by_id(request_id: UUID) -> Optional[dict]:
        """
        Retrieves a single agent request by its UUID.
        """
        db = get_db_client()
        response = db.table("agent_requests").select("*").eq("id", str(request_id)).execute()
        if response.data:
            return response.data[0]
        return None
