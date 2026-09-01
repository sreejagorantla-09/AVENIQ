import httpx
import hashlib
import sys
from app.db.client import get_db_client

BASE_URL = "http://localhost:8000/api/v1"

def print_result(name, success, info=""):
    status = "PASS" if success else "FAIL"
    print(f"[{status}] {name} - {info}")

def run_verification():
    db = get_db_client()
    print("Starting Live End-to-End Verification of AVENIQ Phase 4...\n")

    # 1. Fetch active agent
    agents_res = db.table("ai_agents").select("*").eq("status", "active").execute()
    if not agents_res.data:
        print_result("Retrieve active agent", False, "No active agents found in DB. Run seed first.")
        sys.exit(1)
    agent = agents_res.data[0]
    agent_id = agent["id"]
    print_result("Retrieve active agent", True, f"Agent ID: {agent_id}, Code: {agent['agent_code']}")

    # 2. Generate Agent API Key via POST /agents/{agent_id}/keys
    payload = {
        "name": "E2E Test Key",
        "scopes": ["read:passport", "read:products", "write:proposals", "write:checkout"],
        "expires_in_days": 1
    }
    
    with httpx.Client() as client:
        res = client.post(f"{BASE_URL}/agents/{agent_id}/keys", json=payload)
        if res.status_code != 201:
            print_result("Generate Agent API Key", False, f"API key generation returned code {res.status_code}")
            sys.exit(1)
            
        key_data = res.json()
        raw_key = key_data["raw_key"]
        key_info = key_data["key_info"]
        key_id = key_info["id"]
        key_hash = key_info["key_hash"]
        key_preview = key_info["key_preview"]
        
        print_result("Generate Agent API Key", True, f"Key generated preview: {key_preview}")

        # 3. Verify key hashing and database storage security
        hashed_calculated = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        if hashed_calculated != key_hash:
            print_result("SHA-255 Hashing validation", False, "Hashed key does not match calculation.")
            sys.exit(1)
        print_result("SHA-255 Hashing validation", True, "SHA-256 calculation matches.")

        # Query DB directly to ensure raw key is NOT stored
        db_key_res = db.table("agent_keys").select("*").eq("id", key_id).execute()
        db_key = db_key_res.data[0]
        # Check raw key is not in any field
        for k, v in db_key.items():
            if v == raw_key:
                print_result("Raw key isolation", False, f"Raw key leaked in database field: {k}")
                sys.exit(1)
        print_result("Raw key isolation", True, "Raw key is NOT stored in the database.")

        # 4. Generate restricted key to test scope restrictions
        payload_restricted = {
            "name": "Restricted E2E Key",
            "scopes": ["read:products"],
            "expires_in_days": 1
        }
        res_res = client.post(f"{BASE_URL}/agents/{agent_id}/keys", json=payload_restricted)
        raw_restricted_key = res_res.json()["raw_key"]
        restricted_key_id = res_res.json()["key_info"]["id"]

        # 5. Test missing and invalid key authentication (must return 401)
        # Test missing key
        res_missing = client.get(f"{BASE_URL}/agent/passport")
        print_result("Authenticate with missing API Key", res_missing.status_code == 401, "Returned 401 as expected")

        # Test invalid key
        res_invalid = client.get(f"{BASE_URL}/agent/passport", headers={"X-Agent-API-Key": "avq_live_fakekey_xyz"})
        print_result("Authenticate with invalid API Key", res_invalid.status_code == 401, "Returned 401 as expected")

        # 6. Test scope restrictions (must return 403)
        res_forbidden = client.get(f"{BASE_URL}/agent/passport", headers={"X-Agent-API-Key": raw_restricted_key})
        print_result("Scope authorization check (Forbidden)", res_forbidden.status_code == 403, "Returned 403 as expected for insufficient scopes")

        # Clean up restricted key
        client.delete(f"{BASE_URL}/agents/keys/{restricted_key_id}")

        # 7. Test agent discovery (passport & products)
        headers = {"X-Agent-API-Key": raw_key}
        res_passport = client.get(f"{BASE_URL}/agent/passport", headers=headers)
        if res_passport.status_code != 200:
            print_result("Get Merchant Passport", False, f"Returned status code {res_passport.status_code}")
            sys.exit(1)
        passport_data = res_passport.json()
        print_result("Get Merchant Passport", True, f"Type: {passport_data['type']}, Biz Name: {passport_data['business']['name']}")

        res_products = client.get(f"{BASE_URL}/agent/products", headers=headers)
        if res_products.status_code != 200:
            print_result("List Catalog Products", False, f"Returned status code {res_products.status_code}")
            sys.exit(1)
        products = res_products.json()
        print_result("List Catalog Products", True, f"Found {len(products)} products in catalog.")

        # 8. Test proposal flows
        # Find a product SKU
        product = products[0]
        sku = product["sku"]
        price = product["price"]
        print(f"\nTesting Proposals with Product SKU: {sku}, Price: {price}")

        # A. Compliant purchase request (ALLOW)
        proposal_payload = {
            "raw_request": f"I want to purchase 1 {product['name']} (sku: {sku}) for ₹{price}."
        }
        res_propose_allow = client.post(f"{BASE_URL}/agent/propose", json=proposal_payload, headers=headers)
        if res_propose_allow.status_code != 200:
            print_result("Proposal ALLOW Flow", False, f"Returned status code {res_propose_allow.status_code}: {res_propose_allow.text}")
            sys.exit(1)
        prop_data = res_propose_allow.json()
        decision = prop_data["decision"]
        tx_id = prop_data["transaction_id"]
        print_result("Proposal ALLOW Flow", decision == "ALLOW", f"Decision: {decision}, Tx ID: {tx_id}")

        # B. Out of stock request (DENY)
        proposal_payload_deny = {
            "raw_request": f"I want to purchase 500 {product['name']} (sku: {sku}) for ₹{price}."
        }
        res_propose_deny = client.post(f"{BASE_URL}/agent/propose", json=proposal_payload_deny, headers=headers)
        prop_deny_data = res_propose_deny.json()
        print_result("Proposal DENY Flow (Stock exceed)", prop_deny_data["decision"] == "DENY", f"Decision: {prop_deny_data['decision']}, Reason: {prop_deny_data['reason']}")

        # 9. Test payment checkout order creation
        checkout_payload = {
            "transaction_id": tx_id
        }
        res_checkout = client.post(f"{BASE_URL}/agent/checkout", json=checkout_payload, headers=headers)
        if res_checkout.status_code != 200:
            print_result("Checkout Order Creation", False, f"Returned code {res_checkout.status_code}: {res_checkout.text}")
            sys.exit(1)
        checkout_data = res_checkout.json()
        order_id = checkout_data["razorpay_order_id"]
        print_result("Checkout Order Creation", order_id is not None, f"Razorpay Order ID: {order_id}")

        # 10. Test payment signature verification
        # Verify invalid signature is rejected
        verify_payload_invalid = {
            "transaction_id": tx_id,
            "razorpay_order_id": order_id,
            "razorpay_payment_id": "pay_fake123",
            "razorpay_signature": "sig_invalid_signature"
        }
        res_verify_invalid = client.post(f"{BASE_URL}/agent/checkout/verify", json=verify_payload_invalid, headers=headers)
        print_result("Payment signature rejection check", res_verify_invalid.status_code == 400, "Invalid signature correctly rejected with HTTP 400")

        # Verify valid signature verification (mock signature for sandbox verification tests)
        verify_payload_valid = {
            "transaction_id": tx_id,
            "razorpay_order_id": order_id,
            "razorpay_payment_id": "pay_fake123",
            "razorpay_signature": "sig_mock_signature"
        }
        res_verify_valid = client.post(f"{BASE_URL}/agent/checkout/verify", json=verify_payload_valid, headers=headers)
        if res_verify_valid.status_code != 200:
            print_result("Payment signature verification success", False, f"Returned code {res_verify_valid.status_code}: {res_verify_valid.text}")
            sys.exit(1)
        print_result("Payment signature verification success", True, "Signature verified and transaction marked completed.")

        # 11. Verify cryptographic audit chain integrity
        res_audit_verify = client.get(f"{BASE_URL}/audit/verify")
        audit_data = res_audit_verify.json()
        print_result("Audit ledger verification check", audit_data["valid"] is True, "Audit hash chain is 100% valid and verified.")

        # Clean up generated key
        client.delete(f"{BASE_URL}/agents/keys/{key_id}")
        print("\nVerification Complete.")

if __name__ == "__main__":
    run_verification()
