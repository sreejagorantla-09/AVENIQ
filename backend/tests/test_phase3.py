import pytest
import uuid
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# ----------------------------------------------------
# 1. Dashboard Stats Endpoint Tests
# ----------------------------------------------------
def test_dashboard_stats_endpoint():
    """Test dashboard stats endpoint maps Supabase queries correctly."""
    mock_client = MagicMock()
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.limit.return_value = mock_query
    
    # Mock data return for count and execute
    # Return count = 5 for tables
    mock_query.execute.side_effect = [
        MagicMock(data=[{"status": "active"}, {"status": "archived"}]), # products
        MagicMock(count=2, data=[{}, {}]), # agents
        MagicMock(count=10, data=[{}] * 10), # requests
        MagicMock(count=3, data=[{}, {}, {}]), # policies
        MagicMock(data=[{"event_type": "TEST_EVENT", "actor_id": "test", "actor_type": "user", "action": "test", "decision": "ALLOW", "created_at": "2026-08-27T10:00:00Z", "event_hash": "abc"}]) # recent audit
    ]

    with patch("app.api.v1.dashboard.supabase_client", mock_client):
        response = client.get("/api/v1/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_products"] == 2
        assert data["active_products"] == 1
        assert data["total_agents"] == 2
        assert data["total_requests"] == 10
        assert data["total_policies"] == 3
        assert len(data["recent_activity"]) == 1
        assert data["health"]["database"] == "connected"

# ----------------------------------------------------
# 2. Merchants / Passport Endpoint Tests
# ----------------------------------------------------
def test_get_active_merchant_success():
    """Test active merchant query."""
    mock_client = MagicMock()
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[{
        "id": str(uuid.uuid4()),
        "merchant_code": "AVENIQ_MERCHANT_001",
        "business_name": "Test Brand",
        "business_type": "Retail",
        "country": "IN",
        "currency": "INR",
        "trust_score": 98.5,
        "status": "active",
        "created_at": "2026-08-27T10:00:00Z",
        "updated_at": "2026-08-27T10:00:00Z"
    }])

    with patch("app.db.client.supabase_client", mock_client):
        response = client.get("/api/v1/merchants/active")
        assert response.status_code == 200
        data = response.json()
        assert data["business_name"] == "Test Brand"
        assert data["merchant_code"] == "AVENIQ_MERCHANT_001"

def test_get_current_merchant_production_and_development(monkeypatch):
    """Verify get_current_merchant allows fallback in development but strictly returns HTTP 401 in production."""
    import anyio
    from fastapi import HTTPException
    from app.api.dependencies import get_current_merchant

    # Case 1: ENV = "production", missing headers -> Must raise HTTP 401
    monkeypatch.setattr("app.api.dependencies.settings", type("Settings", (object,), {"ENV": "production"})())
    async def run_prod_test():
        with pytest.raises(HTTPException) as exc:
            await get_current_merchant(x_merchant_id=None, x_merchant_api_key=None)
        assert exc.value.status_code == 401
        assert "Missing Merchant Identification headers" in exc.value.detail

    anyio.run(run_prod_test)

    # Case 2: ENV = "development", missing headers -> Allows fallback query
    mock_merchant = {"id": "m_id", "merchant_code": "AVENIQ_MERCHANT_001", "status": "active"}
    class MockDb:
        def table(self, name):
            return self
        def select(self, *args):
            return self
        def eq(self, *args):
            return self
        def execute(self):
            return type("Res", (object,), {"data": [mock_merchant]})()

    monkeypatch.setattr("app.api.dependencies.get_db_client", lambda: MockDb())
    monkeypatch.setattr("app.api.dependencies.settings", type("Settings", (object,), {"ENV": "development"})())

    async def run_dev_test():
        m = await get_current_merchant(x_merchant_id=None, x_merchant_api_key=None)
        assert m["merchant_code"] == "AVENIQ_MERCHANT_001"

    anyio.run(run_dev_test)

# ----------------------------------------------------
# 3. Product CRUD Endpoint Tests
# ----------------------------------------------------
def test_create_product_api():
    """Test POST /api/v1/products creates entry and logs audit event."""
    mock_client = MagicMock()
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.insert.return_value = mock_query
    
    merchant_id = str(uuid.uuid4())
    product_id = str(uuid.uuid4())
    
    mock_query.execute.side_effect = [
        MagicMock(data=[{
            "id": product_id,
            "merchant_id": merchant_id,
            "sku": "TEST-SKU-1",
            "name": "Test Item",
            "price": 100.0,
            "currency": "INR",
            "stock_quantity": 10,
            "status": "active",
            "metadata": {},
            "created_at": "2026-08-27T10:00:00Z",
            "updated_at": "2026-08-27T10:00:00Z"
        }]), # product insert return
        MagicMock(data=[{"id": str(uuid.uuid4()), "event_hash": "xyz"}]) # audit insert return
    ]

    payload = {
        "merchant_id": merchant_id,
        "sku": "TEST-SKU-1",
        "name": "Test Item",
        "price": 100.0,
        "stock_quantity": 10,
        "status": "active"
    }

    with patch("app.db.client.supabase_client", mock_client), \
         patch("app.services.audit_service.AuditService.create_audit_event", return_value={"id": str(uuid.uuid4()), "event_hash": "xyz"}):
        response = client.post("/api/v1/products", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == product_id
        assert data["sku"] == "TEST-SKU-1"

def test_update_product_api():
    """Test PUT /api/v1/products/{id} updates values and logs audit event."""
    mock_client = MagicMock()
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.update.return_value = mock_query
    
    product_id = str(uuid.uuid4())
    merchant_id = str(uuid.uuid4())
    
    mock_query.execute.side_effect = [
        MagicMock(data=[{"merchant_id": merchant_id, "sku": "SKU-OLD"}]), # current product read
        MagicMock(data=[{
            "id": product_id,
            "merchant_id": merchant_id,
            "sku": "SKU-OLD",
            "name": "Updated Name",
            "price": 150.0,
            "currency": "INR",
            "stock_quantity": 12,
            "status": "active",
            "created_at": "2026-08-27T10:00:00Z",
            "updated_at": "2026-08-27T10:00:00Z"
        }]), # product update return
        MagicMock(data=[{"id": str(uuid.uuid4()), "event_hash": "xyz"}]) # audit insert return
    ]

    payload = {
        "name": "Updated Name",
        "price": 150.0,
        "stock_quantity": 12
    }

    with patch("app.db.client.supabase_client", mock_client), \
         patch("app.services.audit_service.AuditService.create_audit_event", return_value={"id": str(uuid.uuid4()), "event_hash": "xyz"}):
        response = client.put(f"/api/v1/products/{product_id}", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["price"] == 150.0

def test_delete_product_api():
    """Test DELETE /api/v1/products/{id} soft archives product entry."""
    mock_client = MagicMock()
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.update.return_value = mock_query
    
    product_id = str(uuid.uuid4())
    merchant_id = str(uuid.uuid4())
    
    mock_query.execute.side_effect = [
        MagicMock(data=[{"merchant_id": merchant_id, "sku": "SKU-OLD", "name": "Item"}]), # current product read
        MagicMock(data=[{"id": product_id, "status": "archived"}]), # product soft delete return
        MagicMock(data=[{"id": str(uuid.uuid4()), "event_hash": "xyz"}]) # audit insert return
    ]

    with patch("app.db.client.supabase_client", mock_client), \
         patch("app.services.audit_service.AuditService.create_audit_event", return_value={"id": str(uuid.uuid4()), "event_hash": "xyz"}):
        response = client.delete(f"/api/v1/products/{product_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "archived" in data["message"]

# ----------------------------------------------------
# 4. Integrations Status Check Tests
# ----------------------------------------------------
def test_integrations_status_all_connected():
    """Test integrations check when all keys are present."""
    mock_client = MagicMock()
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[])

    with patch("app.api.v1.integrations.settings") as mock_settings, \
         patch("app.api.v1.integrations.supabase_client", mock_client):
        mock_settings.SUPABASE_URL = "https://example.supabase.co"
        mock_settings.SUPABASE_SECRET_KEY = "testsecret"
        mock_settings.GEMINI_API_KEY = "geminikey"
        mock_settings.RAZORPAY_KEY_ID = "rzpid"
        mock_settings.RAZORPAY_KEY_SECRET = "rzpsecret"
        
        response = client.get("/api/v1/integrations/status")
        assert response.status_code == 200
        data = response.json()
        assert data["supabase"]["status"] == "connected"
        assert data["gemini"]["status"] == "connected"
        assert data["razorpay"]["status"] == "connected"
