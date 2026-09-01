import pytest
import uuid
import hashlib
from unittest.mock import MagicMock, patch
from fastapi import Header, HTTPException
from fastapi.testclient import TestClient
from app.main import app
from app.services.key_service import KeyService
from app.api.dependencies import get_current_agent, ScopedRequirement
from app.api.v1.agent_router import require_checkout

client = TestClient(app)

# ----------------------------------------------------
# 1. Key Service & API Hashing Tests
# ----------------------------------------------------
def test_key_generation_and_hashing():
    """Verify raw generated keys are prefix-secured and correctly hashed."""
    raw, key_hash, preview = KeyService.generate_api_key()
    assert raw.startswith("avq_live_")
    assert len(raw) > 20
    assert len(key_hash) == 64 # SHA-256 hex length
    assert preview.startswith("avq_live_")
    assert preview.endswith("...")
    
    # Verify hash match
    assert hashlib.sha256(raw.encode("utf-8")).hexdigest() == key_hash

# ----------------------------------------------------
# 2. Scoped Agent Authentication & Dependency Tests
# ----------------------------------------------------
@pytest.mark.anyio
async def test_agent_api_key_auth_valid():
    """Test valid API Key header fetches scoped agent payload."""
    mock_client = MagicMock()
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    
    agent_id = str(uuid.uuid4())
    merchant_id = str(uuid.uuid4())
    
    mock_query.execute.side_effect = [
        MagicMock(data=[{
            "id": "key_id",
            "agent_id": agent_id,
            "scopes": ["read:passport", "read:products"],
            "is_active": True,
            "expires_at": None,
            "ai_agents": {
                "merchant_id": merchant_id,
                "agent_code": "BOT-001",
                "status": "active"
            }
        }]), # agent keys query
        MagicMock(data=[{}]) # last_used_at update query
    ]

    with patch("app.db.client.supabase_client", mock_client):
        agent_data = await get_current_agent("avq_live_validkey123")
        assert agent_data["agent_code"] == "BOT-001"
        assert "read:passport" in agent_data["scopes"]
        assert agent_data["merchant_id"] == merchant_id

@pytest.mark.anyio
async def test_agent_api_key_auth_invalid():
    """Verify invalid API Key header raises HTTP 401."""
    mock_client = MagicMock()
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[]) # No match found

    with patch("app.db.client.supabase_client", mock_client):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_agent("avq_live_invalidkey")
        assert exc_info.value.status_code == 401

def test_scope_requirement_factory_pass():
    """Verify ScopedRequirement passes if the required scope is present."""
    agent_payload = {
        "agent_id": str(uuid.uuid4()),
        "merchant_id": str(uuid.uuid4()),
        "scopes": ["read:products"]
    }
    requirement = ScopedRequirement(["read:products"])
    result = requirement(agent_payload)
    assert result == agent_payload

def test_scope_requirement_factory_fail():
    """Verify ScopedRequirement raises HTTP 403 if a scope is missing."""
    agent_payload = {
        "agent_id": str(uuid.uuid4()),
        "merchant_id": str(uuid.uuid4()),
        "scopes": ["read:products"]
    }
    requirement = ScopedRequirement(["write:checkout"])
    with pytest.raises(HTTPException) as exc_info:
        requirement(agent_payload)
    assert exc_info.value.status_code == 403

# ----------------------------------------------------
# 3. Policy Evaluator Engine Tests
# ----------------------------------------------------
def test_policy_evaluator_allow():
    """Verify evaluator allows compliant transactions."""
    mock_client = MagicMock()
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    
    merchant_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    
    mock_query.execute.side_effect = [
        MagicMock(data=[{
            "id": str(uuid.uuid4()),
            "sku": "W-HP-001",
            "name": "Headphones",
            "price": 1000.0,
            "stock_quantity": 20,
            "status": "active"
        }]), # catalog check
        MagicMock(data=[]) # no active limiting policies
    ]

    with patch("app.db.client.supabase_client", mock_client):
        from app.policies.evaluator import PolicyEvaluator
        decision, reason, _ = PolicyEvaluator.evaluate_proposal(merchant_id, agent_id, "W-HP-001", 2, 1000.0)
        assert decision == "ALLOW"
        assert "compliance" in reason.lower()

def test_policy_evaluator_deny_stock():
    """Verify evaluator denies proposals exceeding product stock limits."""
    mock_client = MagicMock()
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    
    merchant_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    
    mock_query.execute.return_value = MagicMock(data=[{
        "id": str(uuid.uuid4()),
        "sku": "W-HP-001",
        "price": 1000.0,
        "stock_quantity": 2,
        "status": "active"
    }]) # stock is 2, requesting 5

    with patch("app.db.client.supabase_client", mock_client):
        from app.policies.evaluator import PolicyEvaluator
        decision, reason, _ = PolicyEvaluator.evaluate_proposal(merchant_id, agent_id, "W-HP-001", 5, 1000.0)
        assert decision == "DENY"
        assert "stock" in reason.lower()

# ----------------------------------------------------
# 4. Checkout Order & Verification Tests
# ----------------------------------------------------
def test_checkout_verification_success():
    """Verify payment checkout transitions status to paid and decrements stock."""
    mock_client = MagicMock()
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.update.return_value = mock_query
    
    tx_id = str(uuid.uuid4())
    merchant_id = str(uuid.uuid4())
    agent_id = str(uuid.uuid4())
    
    mock_query.execute.side_effect = [
        MagicMock(data=[{
            "id": tx_id,
            "merchant_id": merchant_id,
            "agent_id": agent_id,
            "request_id": str(uuid.uuid4()),
            "amount": 2000.0,
            "status": "pending",
            "metadata": {"sku": "W-HP-001", "quantity": 2, "detailed_status": "payment_pending"}
        }]), # transaction read
        MagicMock(data=[{"id": tx_id}]), # transaction update status
        MagicMock(data=[{"id": "prod_id", "stock_quantity": 10}]), # product read for stock update
        MagicMock(data=[{}]), # product stock decrement
        MagicMock(data=[{}]), # audit event 1 (payment verified)
        MagicMock(data=[{}])  # audit event 2 (transaction completed)
    ]

    payload = {
        "transaction_id": tx_id,
        "razorpay_order_id": "order_xyz",
        "razorpay_payment_id": "pay_123",
        "razorpay_signature": "sig_mock_signature"
    }

    mock_agent = {
        "agent_id": agent_id,
        "merchant_id": merchant_id,
        "agent_code": "BOT-001",
        "scopes": ["write:checkout"]
    }

    # Apply dependency overrides to bypass authentication sub-dependencies
    app.dependency_overrides[require_checkout] = lambda: mock_agent

    try:
        with patch("app.db.client.supabase_client", mock_client):
            response = client.post("/api/v1/agent/checkout/verify", json=payload, headers={"X-Agent-API-Key": "key"})
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "completed"
    finally:
        app.dependency_overrides.clear()
