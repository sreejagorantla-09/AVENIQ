import pytest
import anyio
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from fastapi import HTTPException
from app.policies.evaluator import PolicyEvaluator
from app.db.client import get_db_client
from app.services.negotiation_service import NegotiationService
from app.api.dependencies import get_current_agent

# Dummy request class for testing IP whitelisting
class MockRequest:
    def __init__(self, host="127.0.0.1", headers=None):
        self.client = type("Client", (object,), {"host": host})()
        self.headers = headers or {}

def test_calculate_max_discount(monkeypatch):
    """Test max discount matches the merchant policy threshold limits."""
    mock_policies = [
        {
            "policy_type": "spending_limit",
            "policy_name": "E2E Volume Discount Policy",
            "is_active": True,
            "rules": {"type": "volume_discount", "min_qty": 5, "discount_percentage": 10.0}
        },
        {
            "policy_type": "spending_limit",
            "policy_name": "E2E Volume Discount Policy",
            "is_active": True,
            "rules": {"type": "volume_discount", "min_qty": 10, "discount_percentage": 15.0}
        }
    ]

    class MockDb:
        def table(self, name):
            return self
        def select(self, *args, **kwargs):
            return self
        def eq(self, *args, **kwargs):
            return self
        def execute(self):
            return type("Res", (object,), {"data": mock_policies})()

    monkeypatch.setattr("app.policies.evaluator.get_db_client", lambda: MockDb())

    # Qty 2 -> No discount
    assert PolicyEvaluator.calculate_max_discount(uuid4(), "SKU-1", 2) == 0.0
    # Qty 7 -> 10%
    assert PolicyEvaluator.calculate_max_discount(uuid4(), "SKU-1", 7) == 10.0
    # Qty 15 -> 15% (highest discount)
    assert PolicyEvaluator.calculate_max_discount(uuid4(), "SKU-1", 15) == 15.0

def test_evaluate_negotiated_pricing_boundaries(monkeypatch):
    """Test evaluate_proposal_negotiated rejects prices below allowed threshold."""
    mock_product = {
        "price": 2000.0,
        "stock_quantity": 20,
        "status": "active",
        "id": str(uuid4())
    }

    class MockDb:
        def __init__(self, table_name=None):
            self.table_name = table_name
        def table(self, name):
            return MockDb(name)
        def select(self, *args, **kwargs):
            return self
        def eq(self, *args, **kwargs):
            return self
        def execute(self):
            if self.table_name == "products":
                return type("Res", (object,), {"data": [mock_product]})()
            return type("Res", (object,), {"data": []})()

    monkeypatch.setattr("app.policies.evaluator.get_db_client", lambda: MockDb())
    monkeypatch.setattr(PolicyEvaluator, "calculate_max_discount", lambda m, s, q: 10.0) # 10% off of 2000 is 1800 minimum

    # Price 1900 -> ALLOW (above 1800 min)
    dec, reason, rules = PolicyEvaluator.evaluate_proposal_negotiated(uuid4(), uuid4(), "SKU-1", 1, 1900.0)
    assert dec == "ALLOW"

    # Price 1750 -> DENY (below 1800 min)
    dec, reason, rules = PolicyEvaluator.evaluate_proposal_negotiated(uuid4(), uuid4(), "SKU-1", 1, 1750.0)
    assert dec == "DENY"
    assert "below the authorized minimum boundary" in reason

def test_concurrency_stock_check(monkeypatch):
    """Test evaluate_proposal_negotiated fails if stock quantity is insufficient."""
    mock_product = {
        "price": 2000.0,
        "stock_quantity": 2, # Only 2 available
        "status": "active",
        "id": str(uuid4())
    }

    class MockDb:
        def __init__(self, table_name=None):
            self.table_name = table_name
        def table(self, name):
            return MockDb(name)
        def select(self, *args, **kwargs):
            return self
        def eq(self, *args, **kwargs):
            return self
        def execute(self):
            if self.table_name == "products":
                return type("Res", (object,), {"data": [mock_product]})()
            return type("Res", (object,), {"data": []})()

    monkeypatch.setattr("app.policies.evaluator.get_db_client", lambda: MockDb())
    monkeypatch.setattr(PolicyEvaluator, "calculate_max_discount", lambda m, s, q: 0.0)

    # Quantity 3 -> DENY due to stock guard
    dec, reason, rules = PolicyEvaluator.evaluate_proposal_negotiated(uuid4(), uuid4(), "SKU-1", 3, 2000.0)
    assert dec == "DENY"
    assert "Concurrency Guard: Insufficient stock" in reason

def test_api_key_expiration(monkeypatch):
    """Test that expired API keys raise HTTP 401 Unauthorized."""
    async def run_test():
        expired_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        mock_key_data = [{
            "id": str(uuid4()),
            "agent_id": str(uuid4()),
            "is_active": True,
            "expires_at": expired_time,
            "scopes": ["read:passport"],
            "ai_agents": {
                "merchant_id": str(uuid4()),
                "agent_code": "TEST_AGENT",
                "status": "active",
                "capabilities": {"trusted_ips": ["*"]}
            }
        }]

        class MockDb:
            def table(self, name):
                return self
            def select(self, *args, **kwargs):
                return self
            def eq(self, *args, **kwargs):
                return self
            def execute(self):
                return type("Res", (object,), {"data": mock_key_data})()

        monkeypatch.setattr("app.api.dependencies.get_db_client", lambda: MockDb())

        req = MockRequest()
        with pytest.raises(HTTPException) as exc_info:
            await get_current_agent(request=req, x_agent_api_key="expired-key")
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "API Key has expired."

    anyio.run(run_test)

def test_proxy_aware_ip_whitelisting(monkeypatch):
    """Test whitelisting blocks requests from unlisted IPs or spoofed proxy configurations."""
    async def run_test():
        mock_key_data = [{
            "id": str(uuid4()),
            "agent_id": str(uuid4()),
            "is_active": True,
            "expires_at": None,
            "scopes": ["read:passport"],
            "ai_agents": {
                "merchant_id": str(uuid4()),
                "agent_code": "TEST_AGENT",
                "status": "active",
                "capabilities": {"trusted_ips": ["192.168.1.10"]} # Only allow 192.168.1.10
            }
        }]

        class MockDb:
            def table(self, name):
                return self
            def select(self, *args, **kwargs):
                return self
            def eq(self, *args, **kwargs):
                return self
            def execute(self):
                return type("Res", (object,), {"data": mock_key_data})()

        monkeypatch.setattr("app.api.dependencies.get_db_client", lambda: MockDb())
        monkeypatch.setattr("app.api.dependencies.settings", type("Settings", (object,), {"TRUSTED_PROXY": False})())

        # Case 1: Client IP matches whitelisted address (without proxy trust)
        req_ok = MockRequest(host="192.168.1.10")
        agent_info = await get_current_agent(request=req_ok, x_agent_api_key="valid-key")
        assert agent_info["agent_code"] == "TEST_AGENT"

        # Case 2: Client IP is mismatch
        req_fail = MockRequest(host="192.168.1.20")
        with pytest.raises(HTTPException) as exc:
            await get_current_agent(request=req_fail, x_agent_api_key="valid-key")
        assert exc.value.status_code == 403
        assert "not permitted by whitelisting rules" in exc.value.detail

        # Case 3: Spoofed X-Forwarded-For when TRUSTED_PROXY is False (Must fall back to socket host and ignore spoof header)
        req_spoof = MockRequest(host="192.168.1.20", headers={"X-Forwarded-For": "192.168.1.10"})
        with pytest.raises(HTTPException) as exc:
            await get_current_agent(request=req_spoof, x_agent_api_key="valid-key")
        assert exc.value.status_code == 403 # Rejected because socket host is 1.20

        # Case 4: Valid proxy header when TRUSTED_PROXY is True
        monkeypatch.setattr("app.api.dependencies.settings", type("Settings", (object,), {"TRUSTED_PROXY": True})())
        req_proxy_ok = MockRequest(host="10.0.0.1", headers={"X-Forwarded-For": "192.168.1.10, 10.0.0.1"})
        agent_info_proxy = await get_current_agent(request=req_proxy_ok, x_agent_api_key="valid-key")
        assert agent_info_proxy["agent_code"] == "TEST_AGENT"

    anyio.run(run_test)
