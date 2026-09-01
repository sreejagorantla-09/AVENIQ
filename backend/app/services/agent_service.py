from typing import List, Optional
from uuid import UUID
from app.db.client import get_db_client
from app.schemas.models import AiAgentCreate, AuditEventCreate
from app.services.audit_service import AuditService

class AgentService:
    @staticmethod
    def get_all_agents() -> List[dict]:
        """
        Retrieves all registered AI agents from the database.
        """
        db = get_db_client()
        response = db.table("ai_agents").select("*").order("created_at", desc=True).execute()
        return response.data

    @staticmethod
    def create_agent(agent_data: AiAgentCreate) -> dict:
        """
        Registers a new AI agent and logs an AGENT_REGISTERED audit event.
        """
        db = get_db_client()

        # Verify merchant exists to prevent foreign key violation
        merchant_res = db.table("merchants").select("id").eq("id", str(agent_data.merchant_id)).execute()
        if not merchant_res.data:
            raise ValueError(f"Merchant profile with ID '{agent_data.merchant_id}' not found.")

        data = {
            "merchant_id": str(agent_data.merchant_id),
            "agent_code": agent_data.agent_code,
            "name": agent_data.name,
            "description": agent_data.description,
            "agent_type": agent_data.agent_type,
            "status": agent_data.status,
            "capabilities": agent_data.capabilities
        }
        response = db.table("ai_agents").insert(data).execute()
        if not response.data:
            raise RuntimeError("Failed to insert AI agent record.")
        new_agent = response.data[0]

        # Audit event
        audit_data = AuditEventCreate(
            merchant_id=agent_data.merchant_id,
            event_type="AGENT_REGISTERED",
            actor_type="system",
            actor_id="system-registry",
            entity_type="agent",
            entity_id=new_agent["id"],
            action="register_agent",
            decision="ALLOW",
            details={"agent_code": agent_data.agent_code, "name": agent_data.name}
        )
        AuditService.create_audit_event(audit_data)

        return new_agent

    @staticmethod
    def update_agent(agent_id: UUID, agent_data: dict) -> Optional[dict]:
        """
        Updates agent capabilities or status and logs an AGENT_UPDATED audit event.
        """
        db = get_db_client()
        # Fetch current record for merchant context
        current_res = db.table("ai_agents").select("*").eq("id", str(agent_id)).execute()
        if not current_res.data:
            return None
        current_agent = current_res.data[0]

        response = db.table("ai_agents").update(agent_data).eq("id", str(agent_id)).execute()
        if response.data:
            updated_agent = response.data[0]
            
            # Determine correct event type (status toggle vs generic update)
            event_type = "AGENT_STATUS_UPDATED" if "status" in agent_data else "AGENT_UPDATED"
            
            # Audit event
            audit_data = AuditEventCreate(
                merchant_id=UUID(current_agent["merchant_id"]),
                event_type=event_type,
                actor_type="merchant",
                actor_id="merchant-admin",
                entity_type="agent",
                entity_id=str(agent_id),
                action="update_agent",
                decision="ALLOW",
                details={"updated_fields": list(agent_data.keys()), "agent_code": current_agent["agent_code"]}
            )
            AuditService.create_audit_event(audit_data)
            return updated_agent
        return None
