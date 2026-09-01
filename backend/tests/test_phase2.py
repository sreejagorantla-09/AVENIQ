import pytest
import uuid
import hashlib
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import Settings
from app.schemas.models import AgentRequestCreate, AuditEventCreate
from app.services.audit_service import AuditService

client = TestClient(app)

# ----------------------------------------------------
# 1. Health Endpoint Tests
# ----------------------------------------------------
def test_health_endpoint_unconfigured():
    """Test health endpoint when database credentials are not set."""
    with patch("app.api.v1.health.supabase_client", None):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"] == "unconfigured"

def test_health_endpoint_connected():
    """Test health endpoint when database query succeeds."""
    mock_client = MagicMock()
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[])

    with patch("app.api.v1.health.supabase_client", mock_client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"] == "connected"

def test_health_endpoint_disconnected():
    """Test health endpoint when database query throws exception (returns 503)."""
    mock_client = MagicMock()
    mock_client.table.side_effect = Exception("Connection lost")

    with patch("app.api.v1.health.supabase_client", mock_client):
        response = client.get("/api/v1/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"] == "disconnected"

# ----------------------------------------------------
# 2. Database Configuration Validation
# ----------------------------------------------------
def test_config_validation_production_missing_secrets():
    """Ensures settings validation fails when running in production with missing secrets."""
    prod_settings = Settings(
        ENV="production",
        SUPABASE_URL=None,  # Missing
        SUPABASE_PUBLISHABLE_KEY="key",
        SUPABASE_SECRET_KEY="secret",
        GEMINI_API_KEY="key",
        RAZORPAY_KEY_ID="id",
        RAZORPAY_KEY_SECRET="secret",
        RAZORPAY_WEBHOOK_SECRET="secret"
    )
    with pytest.raises(ValueError) as exc_info:
        prod_settings.validate_secrets()
    assert "SUPABASE_URL" in str(exc_info.value)

# ----------------------------------------------------
# 3. Product Retrieval Tests
# ----------------------------------------------------
@patch("app.services.product_service.ProductService.get_all_products")
def test_product_list_retrieval(mock_get_all):
    """Test list retrieval for products."""
    mock_product = {
        "id": "e3fe7da8-75c1-4ab6-857c-1f5163a3fb9e",
        "merchant_id": "836b8a8b-14ea-4c4f-9e6b-7bc0991ff573",
        "sku": "SKU-TEST-001",
        "name": "Test Product",
        "description": "Just a test",
        "category": "Electronics",
        "price": 99.99,
        "currency": "INR",
        "stock_quantity": 10,
        "status": "active",
        "metadata": {},
        "created_at": "2026-08-27T15:00:00Z",
        "updated_at": "2026-08-27T15:00:00Z"
    }
    mock_get_all.return_value = [mock_product]
    response = client.get("/api/v1/products")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["sku"] == "SKU-TEST-001"

@patch("app.services.product_service.ProductService.get_product_by_id")
def test_product_detail_not_found(mock_get_by_id):
    """Test that a missing product returns 404."""
    mock_get_by_id.return_value = None
    product_uuid = str(uuid.uuid4())
    response = client.get(f"/api/v1/products/{product_uuid}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"

# ----------------------------------------------------
# 4. Policy Retrieval Tests
# ----------------------------------------------------
@patch("app.services.policy_service.PolicyService.get_all_policies")
def test_policy_list_retrieval(mock_get_policies):
    """Test retrieval of policies list."""
    mock_policy = {
        "id": "76d54cf8-5eb8-4228-a53c-1b77f98fbde1",
        "merchant_id": "836b8a8b-14ea-4c4f-9e6b-7bc0991ff573",
        "policy_type": "spending_limit",
        "policy_name": "Test Limit",
        "description": "Rule details",
        "rules": {"max_amount": 100},
        "priority": 1,
        "is_active": True,
        "created_at": "2026-08-27T15:00:00Z",
        "updated_at": "2026-08-27T15:00:00Z"
    }
    mock_get_policies.return_value = [mock_policy]
    response = client.get("/api/v1/policies")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["policy_type"] == "spending_limit"

# ----------------------------------------------------
# 5. Request Creation Validation
# ----------------------------------------------------
@patch("app.services.request_service.RequestService.create_request")
def test_request_creation_valid(mock_create):
    """Test posting valid request payload."""
    agent_id = str(uuid.uuid4())
    merchant_id = str(uuid.uuid4())
    payload = {
        "agent_id": agent_id,
        "merchant_id": merchant_id,
        "request_type": "procure",
        "raw_request": "Buy smart watch",
        "structured_intent": {"item": "Smart Watch"},
        "requested_action": {"action": "purchase", "value": 3499.00},
        "status": "received"
    }
    
    mock_create.return_value = {
        **payload,
        "id": "4c424683-16a7-4b77-aa98-de7662c82cf9",
        "created_at": "2026-08-27T15:00:00Z"
    }
    
    response = client.post("/api/v1/requests", json=payload)
    assert response.status_code == 201
    assert response.json()["raw_request"] == "Buy smart watch"

# ----------------------------------------------------
# 6. Audit Event Structure Validation
# ----------------------------------------------------
def test_audit_event_structure():
    """Validates the properties required in AuditEvent schemas."""
    m_id = uuid.uuid4()
    event = AuditEventCreate(
        merchant_id=m_id,
        event_type="POLICY_EVALUATION",
        actor_type="system",
        actor_id="engine-01",
        entity_type="policy",
        entity_id="spending-limit",
        action="evaluate",
        decision="ALLOW",
        details={"evaluated_rules": ["spending_limit"]},
        previous_event_hash="0",
        event_hash=None
    )
    assert event.merchant_id == m_id
    assert event.actor_type == "system"
    assert event.decision == "ALLOW"

# ----------------------------------------------------
# 7. Audit Hash Generation & Chain Verification
# ----------------------------------------------------
def test_audit_hash_chaining():
    """Verify SHA-256 hash generation and verification chain validity."""
    # Compute base hashes
    hash_genesis = "0"
    hash_1 = AuditService.calculate_event_hash(
        previous_hash=hash_genesis,
        event_type="INIT",
        actor_type="system",
        actor_id="system-01",
        entity_type="system",
        entity_id=None,
        action="start",
        decision="ALLOW",
        details={"info": "started"}
    )
    
    hash_2 = AuditService.calculate_event_hash(
        previous_hash=hash_1,
        event_type="PROPOSE",
        actor_type="agent",
        actor_id="agent-01",
        entity_type="request",
        entity_id="req-123",
        action="propose",
        decision=None,
        details={"amount": 250}
    )
    
    # Mock events list representation in db
    mock_events = [
        {
            "id": "e3fe7da8-75c1-4ab6-857c-1f5163a3fb91",
            "merchant_id": "836b8a8b-14ea-4c4f-9e6b-7bc0991ff573",
            "event_type": "INIT",
            "actor_type": "system",
            "actor_id": "system-01",
            "entity_type": "system",
            "entity_id": None,
            "action": "start",
            "decision": "ALLOW",
            "details": {"info": "started"},
            "previous_event_hash": hash_genesis,
            "event_hash": hash_1,
            "created_at": "2026-08-27T15:00:00Z"
        },
        {
            "id": "e3fe7da8-75c1-4ab6-857c-1f5163a3fb92",
            "merchant_id": "836b8a8b-14ea-4c4f-9e6b-7bc0991ff573",
            "event_type": "PROPOSE",
            "actor_type": "agent",
            "actor_id": "agent-01",
            "entity_type": "request",
            "entity_id": "req-123",
            "action": "propose",
            "decision": None,
            "details": {"amount": 250},
            "previous_event_hash": hash_1,
            "event_hash": hash_2,
            "created_at": "2026-08-27T15:01:00Z"
        }
    ]
    
    with patch("app.services.audit_service.AuditService.get_all_audit_events", return_value=mock_events):
        res = AuditService.verify_audit_chain()
        assert res["valid"] is True
        assert res["status"] == "verified"

    # Tamper with the first event and verify the chain fails validation
    mock_events_tampered = [dict(e) for e in mock_events]
    mock_events_tampered[0]["details"] = {"info": "tampered"} # Alter details without changing hash
    
    with patch("app.services.audit_service.AuditService.get_all_audit_events", return_value=mock_events_tampered):
        res_tampered = AuditService.verify_audit_chain()
        assert res_tampered["valid"] is False
        assert res_tampered["status"] == "corrupted"

def test_audit_chain_tamper_simulation():
    """Test safe in-memory tamper simulation toggle via POST /api/v1/audit/simulate-tamper."""
    # Reset tamper mode
    res_reset = client.post("/api/v1/audit/simulate-tamper?tamper=false")
    assert res_reset.status_code == 200
    assert res_reset.json()["tamper_simulation_active"] is False

    # Enable tamper simulation
    res_tamper = client.post("/api/v1/audit/simulate-tamper?tamper=true")
    assert res_tamper.status_code == 200
    assert res_tamper.json()["tamper_simulation_active"] is True
    
    # Restore
    client.post("/api/v1/audit/simulate-tamper?tamper=false")

# ----------------------------------------------------
# 8. Invalid UUID Handling
# ----------------------------------------------------
def test_invalid_uuid_route_handling():
    """Passing an invalid UUID format must result in a 422 validator error."""
    response = client.get("/api/v1/products/invalid-uuid-string")
    assert response.status_code == 422
    assert "valid uuid" in response.json()["detail"][0]["msg"].lower()

# ----------------------------------------------------
# 9. Missing Required Fields
# ----------------------------------------------------
def test_request_missing_required_fields():
    """Posting a request payload with missing required agent_id must result in 422 error."""
    payload = {
        # "agent_id" is missing
        "merchant_id": str(uuid.uuid4()),
        "request_type": "procure",
        "raw_request": "Missing agent",
        "structured_intent": {},
        "requested_action": {},
        "status": "received"
    }
    response = client.post("/api/v1/requests", json=payload)
    assert response.status_code == 422
    assert "field required" in response.json()["detail"][0]["msg"].lower()

# ----------------------------------------------------
# 10. Secrets leakage prevention
# ----------------------------------------------------
@patch("app.services.product_service.ProductService.get_all_products")
def test_secrets_are_never_leaked(mock_products):
    """Verifies that API response payloads do not contain secret keys."""
    mock_products.return_value = [
        {
            "id": "e3fe7da8-75c1-4ab6-857c-1f5163a3fb9e",
            "merchant_id": "836b8a8b-14ea-4c4f-9e6b-7bc0991ff573",
            "sku": "SKU-001",
            "name": "Headphones",
            "price": 1999.00,
            "currency": "INR",
            "status": "active",
            "created_at": "2026-08-27T15:00:00Z",
            "updated_at": "2026-08-27T15:00:00Z"
        }
    ]
    
    response = client.get("/api/v1/products")
    response_body = response.text
    
    # Assert standard secrets are not inside the serialized payload
    assert "SUPABASE_SECRET_KEY" not in response_body
    assert "RAZORPAY_KEY_SECRET" not in response_body
    assert "GEMINI_API_KEY" not in response_body
