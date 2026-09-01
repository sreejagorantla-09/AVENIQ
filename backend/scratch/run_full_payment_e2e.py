import sys
import io
import os
import uuid
import httpx

# Ensure UTF-8 output on Windows
if sys.platform.startswith("win"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Add backend directory to sys.path
backend_dir = r"d:\AVENIQ\backend"
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from app.main import app
from fastapi.testclient import TestClient
from app.db.client import get_db_client
from app.services.key_service import KeyService

def main():
    print("====================================================")
    print("AVENIQ FULL PAYMENT E2E FLOW VERIFICATION")
    print("====================================================")
    
    client = TestClient(app)
    
    # 1. Health check
    print("\n1. Verifying API Health...")
    res = client.get("/api/v1/health")
    print(f"Health status: {res.status_code}, body: {res.json()}")
    assert res.status_code == 200
    assert res.json().get("database") == "connected"
    
    db = get_db_client()
    
    # 2. Get active agent ProcureBot v1
    agent_id = "08cfe168-585d-42c3-8fb1-68012fb5284e"
    print(f"\n2. Using registered agent: ProcureBot v1 (ID: {agent_id})")
    
    # 3. Create fresh API key with all 4 scopes
    print("\n3. Generating fresh API key with all authorization scopes...")
    key_res = KeyService.create_agent_key(
        agent_id=uuid.UUID(agent_id),
        name="E2E Full Payment Flow Key",
        scopes=["read:passport", "read:products", "write:proposals", "write:checkout"],
        expires_in_days=1
    )
    raw_key = key_res["raw_key"]
    print(f"[+] API Key generated: {raw_key[:12]}...")
    
    bearer_headers = {
        "Authorization": f"Bearer {raw_key}",
        "Content-Type": "application/json"
    }

    # Verify key works on GET /agent/products
    prod_check = client.get("/api/v1/agent/products", headers=bearer_headers)
    print(f"[+] Product catalog check via Bearer auth: {prod_check.status_code} (Count: {len(prod_check.json())})")
    assert prod_check.status_code == 200

    # ----------------------------------------------------
    # FLOW A: Synchronous Checkout Verification Flow
    # ----------------------------------------------------
    print("\n----------------------------------------------------")
    print("FLOW A: Synchronous Checkout & Verification")
    print("----------------------------------------------------")

    # A1: Negotiate
    print("A1. Starting negotiation for SKU S-WT-002...")
    nego_payload = {"raw_request": "Bargain 1 Smart Watch (sku: S-WT-002) for 3200 INR"}
    res_nego = client.post("/api/v1/agent/negotiate", headers=bearer_headers, json=nego_payload)
    print(f"[+] Negotiate status: {res_nego.status_code}, response: {res_nego.json()}")
    assert res_nego.status_code == 200
    session_id_a = res_nego.json()["session_id"]

    # A2: Accept Negotiation
    print(f"A2. Accepting negotiation session {session_id_a}...")
    res_accept_a = client.post(f"/api/v1/agent/negotiate/{session_id_a}/accept", headers=bearer_headers)
    print(f"[+] Accept status: {res_accept_a.status_code}, response: {res_accept_a.json()}")
    assert res_accept_a.status_code == 200
    tx_id_a = res_accept_a.json()["transaction_id"]
    print(f"[+] Created Transaction A: ID={tx_id_a}")

    # A3: Verify Transaction A initial status in DB
    tx_a_db = db.table("transactions").select("*").eq("id", tx_id_a).execute().data[0]
    print(f"[+] Transaction A DB status: '{tx_a_db['status']}', detailed_status: '{tx_a_db['metadata'].get('detailed_status')}'")
    assert tx_a_db["status"] == "pending"
    assert tx_a_db["metadata"].get("detailed_status") == "payment_pending"

    # A4: Trigger Checkout Order Creation for Transaction A
    print(f"A4. Triggering checkout order creation for Transaction A ({tx_id_a})...")
    res_co_a = client.post("/api/v1/agent/checkout", headers=bearer_headers, json={"transaction_id": tx_id_a})
    print(f"[+] Checkout status: {res_co_a.status_code}, response: {res_co_a.json()}")
    assert res_co_a.status_code == 200
    order_id_a = res_co_a.json()["razorpay_order_id"]
    print(f"[+] Order created for Transaction A: {order_id_a}")

    # A5: Verify Synchronous Payment Checkout Verification
    print(f"A5. Executing synchronous payment verification for Transaction A...")
    verify_payload_a = {
        "transaction_id": tx_id_a,
        "razorpay_order_id": order_id_a,
        "razorpay_payment_id": "pay_sync_e2e_001",
        "razorpay_signature": "sig_mock_signature"
    }
    res_verify_a = client.post("/api/v1/agent/checkout/verify", headers=bearer_headers, json=verify_payload_a)
    print(f"[+] Payment verification status: {res_verify_a.status_code}, response: {res_verify_a.json()}")
    assert res_verify_a.status_code == 200

    # A6: Verify Transaction A final status in DB
    tx_a_final = db.table("transactions").select("*").eq("id", tx_id_a).execute().data[0]
    print(f"[+] Transaction A Final DB status: '{tx_a_final['status']}', detailed_status: '{tx_a_final['metadata'].get('detailed_status')}', provider_tx_id: '{tx_a_final['provider_transaction_id']}'")
    assert tx_a_final["status"] == "completed"
    assert tx_a_final["metadata"].get("detailed_status") == "paid"
    assert tx_a_final["provider_transaction_id"] == "pay_sync_e2e_001"

    # ----------------------------------------------------
    # FLOW B: Asynchronous Payment Webhook Settlement
    # ----------------------------------------------------
    print("\n----------------------------------------------------")
    print("FLOW B: Asynchronous Payment Webhook Settlement")
    print("----------------------------------------------------")

    # Get stock of product S-WT-002 before Flow B
    prod_before = db.table("products").select("stock_quantity").eq("sku", "S-WT-002").execute().data[0]
    stock_before = int(prod_before["stock_quantity"])
    print(f"[+] Product S-WT-002 stock quantity before webhook settlement: {stock_before}")

    # B1: Negotiate
    print("B1. Starting negotiation for SKU S-WT-002 (qty 1)...")
    res_nego_b = client.post("/api/v1/agent/negotiate", headers=bearer_headers, json=nego_payload)
    assert res_nego_b.status_code == 200
    session_id_b = res_nego_b.json()["session_id"]

    # B2: Accept Negotiation
    print(f"B2. Accepting negotiation session {session_id_b}...")
    res_accept_b = client.post(f"/api/v1/agent/negotiate/{session_id_b}/accept", headers=bearer_headers)
    assert res_accept_b.status_code == 200
    tx_id_b = res_accept_b.json()["transaction_id"]
    print(f"[+] Created Transaction B: ID={tx_id_b}")

    # B3: Trigger Checkout Order Creation for Transaction B
    print(f"B3. Triggering checkout order creation for Transaction B...")
    res_co_b = client.post("/api/v1/agent/checkout", headers=bearer_headers, json={"transaction_id": tx_id_b})
    assert res_co_b.status_code == 200
    order_id_b = res_co_b.json()["razorpay_order_id"]
    print(f"[+] Order created for Transaction B: {order_id_b}")

    # B4: Send Razorpay Webhook Event payment.captured
    print(f"B4. Sending Razorpay payment.captured webhook for Order ID: {order_id_b}...")
    import json
    from app.core.config import settings
    
    webhook_dict = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_webhook_e2e_002",
                    "order_id": order_id_b,
                    "amount": 349900,
                    "currency": "INR",
                    "status": "captured"
                }
            }
        }
    }
    body_bytes = json.dumps(webhook_dict).encode("utf-8")
    
    headers_wh = {"Content-Type": "application/json"}
    if settings.RAZORPAY_WEBHOOK_SECRET:
        import hmac, hashlib
        sig = hmac.new(settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
        headers_wh["X-Razorpay-Signature"] = sig

    res_wh = client.post("/api/v1/payments/webhook", content=body_bytes, headers=headers_wh)
    print(f"[+] Webhook response status: {res_wh.status_code}, response: {res_wh.text}")
    assert res_wh.status_code == 200

    # B5: Verify Transaction B final status in DB
    tx_b_final = db.table("transactions").select("*").eq("id", tx_id_b).execute().data[0]
    print(f"[+] Transaction B Final DB status: '{tx_b_final['status']}', detailed_status: '{tx_b_final['metadata'].get('detailed_status')}', provider_tx_id: '{tx_b_final['provider_transaction_id']}'")
    assert tx_b_final["status"] == "completed"
    assert tx_b_final["metadata"].get("detailed_status") == "paid"
    assert tx_b_final["provider_transaction_id"] == "pay_webhook_e2e_002"

    # B6: Verify Stock Quantity Decrement
    prod_after = db.table("products").select("stock_quantity").eq("sku", "S-WT-002").execute().data[0]
    stock_after = int(prod_after["stock_quantity"])
    print(f"[+] Product S-WT-002 stock quantity after webhook settlement: {stock_after}")
    assert stock_after == stock_before - 1

    # ----------------------------------------------------
    # AUDIT TRAIL & CRYPTOGRAPHIC INTEGRITY
    # ----------------------------------------------------
    print("\n----------------------------------------------------")
    print("VERIFYING AUDIT TRAIL & CRYPTOGRAPHIC INTEGRITY")
    print("----------------------------------------------------")
    res_audit = client.get("/api/v1/audit/verify")
    print(f"[+] Ledger validation result: {res_audit.json()}")
    assert res_audit.status_code == 200
    assert res_audit.json().get("valid") is True

    print("\n====================================================")
    print("[SUCCESS] ALL AVENIQ E2E PAYMENT FLOW TESTS PASSED!")
    print("====================================================")

if __name__ == "__main__":
    main()
