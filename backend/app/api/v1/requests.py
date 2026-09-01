from fastapi import APIRouter, HTTPException, Path
from uuid import UUID
from app.schemas.models import AgentRequestCreate, AgentRequestResponse
from app.services.request_service import RequestService

router = APIRouter(prefix="/requests", tags=["Requests"])

@router.post("", response_model=AgentRequestResponse, status_code=201)
def create_request(request_data: AgentRequestCreate):
    """
    Log a new agent request/proposal.
    """
    try:
        return RequestService.create_request(request_data)
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Database service not available or unconfigured")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{request_id}", response_model=AgentRequestResponse)
def get_request(request_id: UUID = Path(..., description="The UUID of the request to retrieve")):
    """
    Retrieve details of an agent request.
    """
    try:
        request = RequestService.get_request_by_id(request_id)
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")
        return request
    except HTTPException:
        raise
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Database service not available or unconfigured")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")
