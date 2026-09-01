import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    """
    Test that the health endpoint returns status 200 and expected payload when unconfigured.
    """
    with patch("app.api.v1.health.supabase_client", None):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

def test_agent_passport_discovery_manifest():
    """
    Test public /.well-known/agent-passport.json discovery endpoint returns valid manifest.
    """
    response = client.get("/.well-known/agent-passport.json")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "AVENIQ"
    assert data["version"] == "1.0.0"
    assert "authentication" in data
    assert "endpoints" in data
    assert "capabilities" in data
    assert "payments" in data
    assert "razorpay" in data["payments"]["supported_providers"]
    assert data["payments"]["currency"] == "INR"
    assert "read:passport" in data["authentication"]["scopes"]
    assert "write:checkout" in data["authentication"]["scopes"]
