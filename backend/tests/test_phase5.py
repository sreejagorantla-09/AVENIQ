import pytest
import uuid
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.api.v1.agent_router import require_proposals
from app.services.approval_service import ApprovalService
from app.services.merchant_service import MerchantService

client = TestClient(app)

# ----------------------------------------------------
# 1. Approval Service & Decision Logic Tests
# ----------------------------------------------------
def test_get_pending_approvals():
    """Verify listing pending approvals queries approvals table."""
    mock_client = MagicMock()
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[
        {"id": "app_id", "status": "pending", "request_id": "req_id"}
    ])

    with patch("app.db.client.supabase_client", mock_client):
        res = ApprovalService.get_pending_approvals(uuid.uuid4())
        assert len(res) == 1
        assert res[0]["id"] == "app_id"
        mock_client.table.assert_called_with("approvals")

@patch("app.services.audit_service.AuditService.create_audit_event")
def test_submit_approval_decision_approve(mock_audit_event):
    """Verify approving transitions status and inserts checkout transaction."""
    mock_client = MagicMock()
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.update.return_value = mock_query
    
    app_id = uuid.uuid4()
    req_id = uuid.uuid4()
    merch_id = uuid.uuid4()
    
    # Execution returns
    mock_query.execute.side_effect = [
        MagicMock(data=[{"id": str(app_id), "request_id": str(req_id)}]),  # approvals read
        MagicMock(data=[{
            "id": str(req_id), 
            "agent_id": str(uuid.uuid4()),
            "structured_intent": {"sku": "W-HP-001", "quantity": 1, "unit_price": 1999.0}
        }]),  # requests read
        MagicMock(data=[{}]),  # approvals update status
        MagicMock(data=[{}]),  # requests update status
        MagicMock(data=[{"id": "prod_id"}]),  # product SKU lookup
        MagicMock(data=[{"id": "tx_id"}]),  # transaction insert
    ]

    with patch("app.db.client.supabase_client", mock_client):
        res = ApprovalService.submit_approval_decision(app_id, "approve", merch_id)
        assert res is not None
        assert res["status"] == "approved"
        assert res["request_id"] == str(req_id)

# ----------------------------------------------------
# 2. Scoped Proposals Retrieve API Tests
# ----------------------------------------------------
def test_get_proposal_status_endpoint():
    """Verify proposal status GET endpoint returns aggregated status and details."""
    mock_client = MagicMock()
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    
    req_id = uuid.uuid4()
    tx_id = uuid.uuid4()
    
    mock_query.execute.side_effect = [
        MagicMock(data=[{"id": str(req_id), "status": "approved"}]),  # request query
        MagicMock(data=[{"decision": "REQUIRE_APPROVAL", "reason": "budget check"}]),  # decision query
        MagicMock(data=[{"id": str(tx_id)}])  # transaction query
    ]

    mock_agent = {"scopes": ["write:proposals"]}
    app.dependency_overrides[require_proposals] = lambda: mock_agent

    try:
        with patch("app.db.client.supabase_client", mock_client):
            response = client.get(f"/api/v1/agent/proposals/{req_id}", headers={"X-Agent-API-Key": "test"})
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "approved"
            assert data["decision"] == "REQUIRE_APPROVAL"
            assert data["transaction_id"] == str(tx_id)
    finally:
        app.dependency_overrides.clear()

# ----------------------------------------------------
# 3. Dynamic Trust Score Calculation Tests
# ----------------------------------------------------
def test_recalculate_trust_score():
    """Verify trust score calculations sum failures, success payments, and audit validity."""
    mock_client = MagicMock()
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.update.return_value = mock_query
    
    merch_id = uuid.uuid4()
    
    # Return 2 failed events, 5 successful ones
    failed_mock = MagicMock(count=2)
    success_mock = MagicMock(count=5)
    
    mock_query.execute.side_effect = [
        failed_mock,  # failed events count
        success_mock,  # successful events count
        MagicMock(data=[{}])  # merchant update
    ]

    with patch("app.db.client.supabase_client", mock_client):
        with patch("app.services.audit_service.AuditService.verify_audit_chain", return_value=True):
            score = MerchantService.recalculate_trust_score(merch_id)
            # Base 100 - (2 failed * 5) + (5 success * 1) = 95.0
            assert score == 95.0
