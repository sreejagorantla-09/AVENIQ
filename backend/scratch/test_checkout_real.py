import os
import sys

# Add backend folder to path
sys.path.append(r"d:\AVENIQ\backend")

from fastapi.testclient import TestClient
from app.main import app

def main():
    client = TestClient(app)
    api_key = os.environ.get("AVENIQ_AGENT_API_KEY")
    if not api_key:
        print("FAIL: AVENIQ_AGENT_API_KEY env not set.")
        return
        
    headers = {
        "X-Agent-API-Key": api_key,
        "Content-Type": "application/json"
    }
    tx_id = "203c9004-acc1-4abf-b217-58e6499eca11"
    
    print("Triggering checkout via TestClient...")
    res = client.post("/api/v1/agent/checkout", headers=headers, json={"transaction_id": tx_id})
    print("Status:", res.status_code)
    print("Response:", res.text)

if __name__ == "__main__":
    main()
