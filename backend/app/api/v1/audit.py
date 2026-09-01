from fastapi import APIRouter, HTTPException
from typing import List
from app.schemas.models import AuditEventResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["Audit"])

@router.get("/events", response_model=List[AuditEventResponse])
def get_audit_events():
    """
    Retrieve all audit ledger events in chronological order.
    """
    try:
        return AuditService.get_all_audit_events()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Database service not available or unconfigured")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/verify")
def verify_audit_chain():
    """
    Runs verification on the SHA-256 chain to check for tampering.
    Returns detailed verification statistics including total blocks and hash mismatch data.
    """
    try:
        return AuditService.verify_audit_chain()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Database service not available or unconfigured")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/simulate-tamper")
def simulate_tamper(tamper: bool = True):
    """
    Toggles safe in-memory audit chain tamper simulation mode for buildathon demo purposes.
    Does NOT modify or corrupt any production database records.
    """
    try:
        AuditService.set_tamper_simulation(tamper)
        result = AuditService.verify_audit_chain()
        return {
            "message": f"Tamper simulation set to '{tamper}'",
            "tamper_simulation_active": tamper,
            "verification_result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to toggle tamper simulation: {str(e)}")
