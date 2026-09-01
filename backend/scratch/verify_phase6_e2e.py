import httpx
import sys
import io
import uuid
from datetime import datetime, timezone, timedelta

# Force stdout to use UTF-8 on Windows command lines
if sys.platform.startswith("win"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from app.db.client import get_db_client
from app.services.key_service import KeyService
from app.services.agent_service import AgentService

def main():
    print("====================================================")
    print("AVENIQ E2E VERIFICATION SCRIPT - PHASE 6")
    print("====================================================")

    # 1. Health and Connection check
    print("1. Checking API Health & Database connectivity...")
    try:
        res = httpx.get("http://localhost:8000/api/v1/health")
        if res.status_code != 200:
            print(f"[-] API Health check failed with code {res.status_code}")
            sys.exit(1)
        data = res.json()
        print(f"[+] Health response: {data}")
        if data.get("database") != "connected":
            print("[-] Database is not connected in FastAPI config.")
            sys.exit(1)
    except Exception as e:
        print(f"[-] Failed to query API: {e}")
        sys.exit(1)

    db = get_db_client()
    merch_res = db.table("merchants").select("*").eq("merchant_code", "AVENIQ_MERCHANT_001").execute()
    if not merch_res.data:
        print("[-] Active merchant profile not found in Supabase.")
        sys.exit(1)
    merchant = merch_res.data[0]
    merchant_id = merchant["id"]
    print(f"[+] Active merchant found: ID={merchant_id}, Code={merchant['merchant_code']}")

    # Save original spending-limit policy/rules before modifying anything
    print("[+] Fetching original spending-limit policy rules...")
    orig_pol_res = db.table("merchant_policies").select("*").eq("policy_name", "Maximum Order Value limit").eq("merchant_id", str(merchant_id)).execute()
    if not orig_pol_res.data:
        print("[-] Original Maximum Order Value limit policy not found.")
        sys.exit(1)
    original_policy = orig_pol_res.data[0]
    original_rules = original_policy["rules"]
    print(f"[+] Saved original rules: {original_rules}")

    policy_id = None
    agent_id = None
    session_id = None
    test_passed = False

    try:
        # Update spending limit policy rules temporarily to increase cap
        print("[+] Temporarily setting absolute cap on spending policy to 50000 INR...")
        db.table("merchant_policies").update({
            "rules": {"currency": "INR", "max_amount": 50000.0, "requires_manual_approval_above": 1000.0}
        }).eq("id", str(original_policy["id"])).execute()

        # 2. Configure volume discount policy
        print("\n2. Configuring volume discount policy (10% off for qty >= 10)...")
        # Clean up previous E2E policy if exists
        db.table("merchant_policies").delete().eq("policy_name", "E2E Volume Policy").execute()
        
        policy_payload = {
            "merchant_id": str(merchant_id),
            "policy_name": "E2E Volume Policy",
            "policy_type": "spending_limit",
            "description": "10% volume discount on purchases of 10 or more units",
            "rules": {"type": "volume_discount", "min_qty": 10, "discount_percentage": 10.0},
            "is_active": True
        }
        policy_res = db.table("merchant_policies").insert(policy_payload).execute()
        policy_id = policy_res.data[0]["id"]
        print(f"[+] Volume discount policy active: ID={policy_id}")

        # 3. Register or reuse E2E Agent
        agent_code = "E2E_VERIFIER_BOT_PH6"
        agent_res = db.table("ai_agents").select("*").eq("agent_code", agent_code).execute()
        if agent_res.data:
            agent = agent_res.data[0]
            print(f"[+] Reusing existing E2E agent: ID={agent['id']}")
        else:
            agent_data = {
                "merchant_id": merchant_id,
                "agent_code": agent_code,
                "name": "E2E Phase 6 Verifier Agent",
                "description": "Autonomous script to check negotiations and production security",
                "agent_type": "Procurement",
                "status": "active",
                "capabilities": {"max_spend_per_day": 100000, "trusted_ips": ["*"]}
            }
            ins_res = db.table("ai_agents").insert(agent_data).execute()
            agent = ins_res.data[0]
            print(f"[+] Registered new E2E agent: ID={agent['id']}")
        
        agent_id = agent["id"]

        # 4. Generate API key for agent
        print("Creating active API key with write:proposals scopes...")
        db.table("agent_keys").delete().eq("agent_id", str(agent_id)).execute()
        
        key_res = KeyService.create_agent_key(
            agent_id=uuid.UUID(agent_id),
            name="E2E Phase 6 Validation Key",
            scopes=["read:passport", "read:products", "write:proposals", "write:checkout"],
            expires_in_days=1
        )
        raw_key = key_res["raw_key"]
        key_id = key_res["key_info"]["id"]
        print(f"[+] Agent API Key generated: {raw_key[:12]}...")

        # 5. Simulate Price Negotiation (Bargain qty = 10 below limit)
        print("\n3. Testing Price Negotiation (Bargain Qty = 10 S-WT-002)...")
        headers = {"X-Agent-API-Key": raw_key}
        nego_payload = {"raw_request": "Bargain 10 Smart Watches (S-WT-002) for 1500 INR"}
        
        res = httpx.post("http://localhost:8000/api/v1/agent/negotiate", headers=headers, json=nego_payload)
        if res.status_code != 200:
            print(f"[-] Negotiation call failed: {res.status_code} - {res.text}")
            sys.exit(1)
            
        nego_data = res.json()
        print(f"[+] Negotiation response: {nego_data}")
        session_id = nego_data["session_id"]
        counter_price = nego_data["counter_offer_price"]
        
        # Assert price is capped strictly by Python boundary (3149.1)
        if abs(counter_price - 3149.1) > 0.01:
            print(f"[-] Boundary cap validation failed. Counter price: {counter_price}, expected: 3149.1")
            sys.exit(1)
        print("[+] Boundary cap validated: Price capped deterministically by Python evaluator.")

        # 6. Verify Proxy-Aware IP Whitelisting Rejection
        print("\n4. Testing IP Whitelisting rejection...")
        db.table("ai_agents").update({
            "capabilities": {"max_spend_per_day": 100000, "trusted_ips": ["192.168.1.99"]}
        }).eq("id", str(agent_id)).execute()
        
        res_ip = httpx.post("http://localhost:8000/api/v1/agent/negotiate", headers=headers, json=nego_payload)
        print(f"[+] Spoofed IP check response code: {res_ip.status_code}")
        if res_ip.status_code != 403:
            print("[-] IP Whitelisting restriction failed to block client.")
            sys.exit(1)
        print("[+] IP Whitelisting successfully blocked unauthorized client.")
        
        # Restore whitelisting to *
        db.table("ai_agents").update({
            "capabilities": {"max_spend_per_day": 100000, "trusted_ips": ["*"]}
        }).eq("id", str(agent_id)).execute()

        # 7. Verify API Key Expiration Check
        print("\n5. Testing API Key Expiration Check...")
        past_time = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
        db.table("agent_keys").update({"expires_at": past_time}).eq("id", str(key_id)).execute()
        
        res_exp = httpx.post("http://localhost:8000/api/v1/agent/negotiate", headers=headers, json=nego_payload)
        print(f"[+] Expired key response code: {res_exp.status_code} - {res_exp.text}")
        if res_exp.status_code != 401 or "API Key has expired" not in res_exp.text:
            print("[-] API Key expiration check failed to return 401 detail.")
            sys.exit(1)
        print("[+] Expired API Key check successfully returned 401 Unauthorized.")

        # Restore key expiration to active
        future_time = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()
        db.table("agent_keys").update({"expires_at": future_time}).eq("id", str(key_id)).execute()

        # 8. Accept Negotiation Counter-Offer
        print("\n6. Testing Accept Negotiation...")
        res_accept = httpx.post(f"http://localhost:8000/api/v1/agent/negotiate/{session_id}/accept", headers=headers)
        if res_accept.status_code != 200:
            print(f"[-] Accept negotiation failed: {res_accept.status_code} - {res_accept.text}")
            sys.exit(1)
        accept_data = res_accept.json()
        print(f"[+] Accept response: {accept_data}")
        transaction_id = accept_data["transaction_id"]
        print(f"[+] Transaction created successfully: ID={transaction_id}")

        # 9. Cryptographic Audit Chain validation
        print("\n7. Verifying cryptographic chain logs...")
        res_chain = httpx.get("http://localhost:8000/api/v1/audit/verify")
        chain_data = res_chain.json()
        print(f"[+] Ledger validation result: {chain_data}")
        if not chain_data.get("valid"):
            print("[-] Cryptographic chain is invalid after negotiations.")
            sys.exit(1)
        print("[+] Cryptographic hash chain verified successfully.")

        test_passed = True

    except Exception as e:
        print(f"[-] E2E Verification encountered an error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\n8. Cleaning up E2E verification records & restoring policies...")
        if session_id:
            try:
                db.table("transactions").delete().eq("request_id", session_id).execute()
            except Exception as ex:
                print(f"[-] Error deleting transaction for session_id: {ex}")
        
        if agent_id:
            try:
                reqs = db.table("agent_requests").select("id").eq("agent_id", str(agent_id)).execute().data
                for r in reqs:
                    rid = r["id"]
                    db.table("transactions").delete().eq("request_id", rid).execute()
                    db.table("approvals").delete().eq("request_id", rid).execute()
                    db.table("policy_decisions").delete().eq("request_id", rid).execute()
                    db.table("negotiation_sessions").delete().eq("request_id", rid).execute()
                    db.table("agent_requests").delete().eq("id", rid).execute()
                
                db.table("agent_keys").delete().eq("agent_id", str(agent_id)).execute()
                db.table("ai_agents").delete().eq("id", str(agent_id)).execute()
            except Exception as ex:
                print(f"[-] Error cleaning up agent: {ex}")

        if policy_id:
            try:
                db.table("merchant_policies").delete().eq("id", str(policy_id)).execute()
            except Exception as ex:
                print(f"[-] Error deleting volume policy: {ex}")

        # Restore original spending-limit policy rules
        try:
            print(f"[+] Restoring original spending policy rules: {original_rules}")
            db.table("merchant_policies").update({"rules": original_rules}).eq("id", str(original_policy["id"])).execute()
            print("[+] Original spending policy rules restored successfully.")
        except Exception as ex:
            print(f"[-] CRITICAL error restoring original spending policy: {ex}")

    if not test_passed:
        print("\n====================================================")
        print("[-] PHASE 6 E2E VERIFICATIONS FAILED")
        print("====================================================")
        sys.exit(1)
    else:
        print("\n====================================================")
        print("[+] PHASE 6 E2E VERIFICATIONS PASSED SUCCESSFULLY!")
        print("====================================================")

if __name__ == "__main__":
    main()
