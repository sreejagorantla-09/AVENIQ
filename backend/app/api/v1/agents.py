from fastapi import APIRouter, HTTPException, Path
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from app.schemas.models import AiAgentCreate, AiAgentResponse
from app.services.agent_service import AgentService
from app.services.key_service import KeyService

router = APIRouter(prefix="/agents", tags=["Agents"])

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    capabilities: Optional[dict] = None

class KeyCreateRequest(BaseModel):
    name: str
    scopes: List[str]
    expires_in_days: Optional[int] = None

@router.get("", response_model=List[AiAgentResponse])
def get_agents():
    """
    List registered AI agents authorized by AVENIQ merchants.
    """
    try:
        return AgentService.get_all_agents()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Database service not available or unconfigured")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("", response_model=AiAgentResponse, status_code=201)
def register_agent(agent_data: AiAgentCreate):
    """
    Register a new AI agent with merchant authorization.
    """
    try:
        return AgentService.create_agent(agent_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Database service not available or unconfigured")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to register agent: {str(e)}")

@router.put("/{agent_id}", response_model=AiAgentResponse)
def update_agent(
    agent_id: UUID = Path(..., description="The UUID of the agent to update"),
    update_data: AgentUpdate = ...
):
    """
    Update agent capabilities or status configuration.
    """
    try:
        data = {k: v for k, v in update_data.model_dump().items() if v is not None}
        if not data:
            raise HTTPException(status_code=400, detail="No update fields provided.")
            
        agent = AgentService.update_agent(agent_id, data)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent
    except HTTPException:
        raise
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Database service not available or unconfigured")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

# --- Key Management Endpoints ---

@router.post("/{agent_id}/keys", status_code=201)
def create_agent_api_key(
    agent_id: UUID = Path(..., description="The UUID of the agent to generate a key for"),
    payload: KeyCreateRequest = ...
):
    """
    Generate a secure random API key token for the AI agent.
    Returns the raw key (avq_live_...) to be copied by the user once.
    """
    try:
        result = KeyService.create_agent_key(
            agent_id=agent_id,
            name=payload.name,
            scopes=payload.scopes,
            expires_in_days=payload.expires_in_days
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Database service not available or unconfigured")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error generating API key.")

@router.get("/{agent_id}/keys")
def list_agent_api_keys(
    agent_id: UUID = Path(..., description="The UUID of the agent to query keys for")
):
    """
    List preview meta metadata of generated keys for the AI agent.
    """
    try:
        return KeyService.list_agent_keys(agent_id)
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Database service not available or unconfigured")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error listing keys.")

@router.delete("/keys/{key_id}")
def revoke_agent_api_key(
    key_id: UUID = Path(..., description="The UUID of the key to revoke")
):
    """
    Revokes (deactivates) an agent API key.
    """
    try:
        success = KeyService.revoke_agent_key(key_id)
        if not success:
            raise HTTPException(status_code=404, detail="API key not found")
        return {"success": True, "message": "API key successfully revoked"}
    except HTTPException:
        raise
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Database service not available or unconfigured")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error revoking key.")
