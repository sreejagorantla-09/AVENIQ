import httpx
import sys
import io
import uuid

# Force stdout to use UTF-8 on Windows command lines
if sys.platform.startswith("win"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from app.db.client import get_db_client
from app.services.key_service import KeyService
from app.services.agent_service import AgentService

def main():
    print("====================================================")
    print("AVENIQ E2E VERIFICATION SCRIPT - PHASE 5")
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

    # 2. Get active merchant
    db = get_db_client()
    merch_res = db.table("merchants").select("*").eq("merchant_code", "AVENIQ_MERCHANT_001").execute()
    if not merch_res.data:
        print("[-] Active merchant profile not found in Supabase.")
        sys.exit(1)
    merchant = merch_res.data[0]
    merchant_id = merchant["id"]
    print(f"[+] Active merchant found: ID={merchant_id}, Code={merchant['merchant_code']}")

    # Update spending limit policy rules temporarily to set manual approval threshold
    print("[+] Temporarily setting approval threshold on spending policy to 1000 INR...")
    db.table("merchant_policies").update({
        "rules": {"currency": "INR", "max_amount": 5000.0, "requires_manual_approval_above": 1000.0}
    }).eq("policy_name", "Maximum Order Value limit").eq("merchant_id", str(merchant_id)).execute()

    # 3. Register or reuse E2E Agent
    agent_code = "E2E_VERIFIER_BOT"
    agent_res = db.table("ai_agents").select("*").eq("agent_code", agent_code).execute()
    if agent_res.data:
        agent = agent_res.data[0]
        print(f"[+] Reusing existing E2E agent: ID={agent['id']}")
    else:
        # Register new agent
        from app.schemas.models import AiAgentCreate
        agent_data = {
            "merchant_id": merchant_id,
            "agent_code": agent_code,
            "name": "E2E Phase 5 Verifier Agent",
            "description": "Autonomous script to check human-in-the-loop triggers",
            "agent_type": "Procurement",
            "status": "active",
            "capabilities": {"max_spend_per_day": 10000}
        }
        ins_res = db.table("ai_agents").insert(agent_data).execute()
        agent = ins_res.data[0]
        print(f"[+] Registered new E2E agent: ID={agent['id']}")
    
    agent_id = agent["id"]

    # 4. Generate API key for agent
    print("Creating active API key with write:proposals scopes...")
    # Clean up existing keys first to avoid duplicates
    db.table("agent_keys").delete().eq("agent_id", str(agent_id)).execute()
    
    key_res = KeyService.create_agent_key(
        agent_id=uuid.UUID(agent_id),
        name="E2E Validation Key",
        scopes=["read:passport", "read:products", "write:proposals", "write:checkout"],
        expires_in_days=1
    )
    raw_key = key_res["raw_key"]
    print(f"[+] Agent API Key generated: {raw_key[:12]}...")

    # 5. Propose purchase that triggers REQUIRES_APPROVAL
    print("\n2. Simulating Proposal that triggers REQUIRES_APPROVAL...")
    headers = {"X-Agent-API-Key": raw_key}
    # Propose buying 1 watch for 3499 INR (matching catalog price but exceeding threshold)
    proposal_payload = {"raw_request": "Buy 1 Smart Watch (S-WT-002) for 3499 INR"}
    
    prop_res = httpx.post(
        "http://localhost:8000/api/v1/agent/propose",
        headers=headers,
        json=proposal_payload
    )
    if prop_res.status_code != 200:
        print(f"[-] Proposal endpoint returned failure: {prop_res.status_code} - {prop_res.text}")
        sys.exit(1)
    
    prop_data = prop_res.json()
    print(f"[+] Proposal response: {prop_data}")
    
    assert prop_data["decision"] == "REQUIRES_APPROVAL", f"Expected REQUIRES_APPROVAL, got {prop_data['decision']}"
    assert prop_data["transaction_id"] is None, "Expected transaction_id to be None before manual approval"
    
    request_id = prop_data["request_id"]
    
    # 6. Verify agent_request & approvals entries in DB
    print("\n3. Verifying database state...")
    req_db = db.table("agent_requests").select("*").eq("id", request_id).execute().data[0]
    assert req_db["status"] == "requires_approval", f"Expected request status requires_approval, got {req_db['status']}"
    print("[+] Verified agent_request status is 'requires_approval' in Supabase.")

    app_db = db.table("approvals").select("*").eq("request_id", request_id).execute().data[0]
    assert app_db["status"] == "pending", f"Expected approval status pending, got {app_db['status']}"
    approval_id = app_db["id"]
    print(f"[+] Verified approval entry exists and is 'pending' in Supabase. Approval ID: {approval_id}")

    tx_db = db.table("transactions").select("*").eq("request_id", request_id).execute().data
    assert len(tx_db) == 0, f"Expected no transaction record to exist, found {len(tx_db)}"
    print("[+] Verified NO transaction has been created before merchant approval.")

    # 7. Check proposal polling endpoint (Requires_Approval state)
    print("\n4. Testing proposal polling GET endpoint (Pending approval)...")
    poll_res = httpx.get(
        f"http://localhost:8000/api/v1/agent/proposals/{request_id}",
        headers=headers
    )
    assert poll_res.status_code == 200, f"Expected 200, got {poll_res.status_code}"
    poll_data = poll_res.json()
    print(f"[+] Polling response: {poll_data}")
    assert poll_data["status"] == "requires_approval", f"Expected requires_approval status, got {poll_data['status']}"
    assert poll_data["transaction_id"] is None, "Expected transaction_id to be None"

    # 8. Test Security: Verify agent cannot access approvals
    print("\n5. Testing Security: Verifying Agent cannot access merchant endpoints...")
    sec_res_1 = httpx.get("http://localhost:8000/api/v1/approvals", headers=headers)
    assert sec_res_1.status_code == 403, f"Expected 403 Forbidden, got {sec_res_1.status_code}"
    print("[+] Security check: Agent credentials blocked from listing approvals queue (403).")

    sec_res_2 = httpx.post(f"http://localhost:8000/api/v1/approvals/{approval_id}/decision", headers=headers, json={"decision": "approve"})
    assert sec_res_2.status_code == 403, f"Expected 403 Forbidden, got {sec_res_2.status_code}"
    print("[+] Security check: Agent credentials blocked from deciding approvals queue (403).")

    # 9. Merchant Approves Request
    print("\n6. Merchant submitting APPROVE decision...")
    decision_res = httpx.post(
        f"http://localhost:8000/api/v1/approvals/{approval_id}/decision",
        json={"decision": "approve"}
    )
    assert decision_res.status_code == 200, f"Decision endpoint failed: {decision_res.status_code}"
    print(f"[+] Decision outcome: {decision_res.json()}")

    # 10. Verify post-approval statuses
    req_db_post = db.table("agent_requests").select("*").eq("id", request_id).execute().data[0]
    assert req_db_post["status"] == "approved", f"Expected request status approved, got {req_db_post['status']}"
    print("[+] Verified agent_request status updated to 'approved' in Supabase.")

    app_db_post = db.table("approvals").select("*").eq("id", approval_id).execute().data[0]
    assert app_db_post["status"] == "approved", f"Expected approval status approved, got {app_db_post['status']}"
    print("[+] Verified approval status updated to 'approved' in Supabase.")

    tx_db_post = db.table("transactions").select("*").eq("request_id", request_id).execute().data
    assert len(tx_db_post) == 1, f"Expected exactly 1 transaction record to exist, found {len(tx_db_post)}"
    transaction_id = tx_db_post[0]["id"]
    print(f"[+] Verified transaction created after merchant approval. Transaction ID: {transaction_id}")

    # 11. Check proposal polling endpoint (Approved state)
    print("\n7. Testing proposal polling GET endpoint (Approved)...")
    poll_res_post = httpx.get(
        f"http://localhost:8000/api/v1/agent/proposals/{request_id}",
        headers=headers
    )
    poll_data_post = poll_res_post.json()
    print(f"[+] Polling response: {poll_data_post}")
    assert poll_data_post["status"] == "approved", f"Expected approved status, got {poll_data_post['status']}"
    assert poll_data_post["transaction_id"] == transaction_id, "Expected transaction_id to match the inserted transaction"

    # ----------------------------------------------------
    # REJECTION FLOW VERIFICATION
    # ----------------------------------------------------
    print("\n8. Simulating Proposal Rejection flow...")
    prop_res_2 = httpx.post(
        "http://localhost:8000/api/v1/agent/propose",
        headers=headers,
        json={"raw_request": "Buy 1 Smart Watch (S-WT-002) for 3499 INR"}
    )
    prop_data_2 = prop_res_2.json()
    req_id_2 = prop_data_2["request_id"]

    app_db_2 = db.table("approvals").select("*").eq("request_id", req_id_2).execute().data[0]
    app_id_2 = app_db_2["id"]

    # Reject
    dec_res_2 = httpx.post(
        f"http://localhost:8000/api/v1/approvals/{app_id_2}/decision",
        json={"decision": "reject"}
    )
    assert dec_res_2.status_code == 200, f"Expected 200, got {dec_res_2.status_code}"
    
    # Confirm DB statuses
    req_db_post_2 = db.table("agent_requests").select("*").eq("id", req_id_2).execute().data[0]
    assert req_db_post_2["status"] == "denied", f"Expected request status denied, got {req_db_post_2['status']}"
    
    app_db_post_2 = db.table("approvals").select("*").eq("id", app_id_2).execute().data[0]
    assert app_db_post_2["status"] == "rejected", f"Expected approval status rejected, got {app_db_post_2['status']}"
    
    tx_db_post_2 = db.table("transactions").select("*").eq("request_id", req_id_2).execute().data
    assert len(tx_db_post_2) == 0, "Expected NO transaction to be created on rejection"
    print("[+] Verified rejection status transitions and NO transaction insertion.")

    # Check polling on rejection
    poll_res_2 = httpx.get(
        f"http://localhost:8000/api/v1/agent/proposals/{req_id_2}",
        headers=headers
    )
    poll_data_2 = poll_res_2.json()
    print(f"[+] Polling response on rejection: {poll_data_2}")
    assert poll_data_2["status"] == "denied", f"Expected denied status, got {poll_data_2['status']}"
    assert poll_data_2["transaction_id"] is None

    # Clean up test records
    print("\n9. Cleaning up test records...")
    try:
        reqs = db.table("agent_requests").select("id").eq("agent_id", str(agent_id)).execute().data
        req_ids = [r["id"] for r in reqs]
        
        for rid in req_ids:
            db.table("transactions").delete().eq("request_id", rid).execute()
            db.table("approvals").delete().eq("request_id", rid).execute()
            db.table("policy_decisions").delete().eq("request_id", rid).execute()
            
        db.table("agent_requests").delete().eq("agent_id", str(agent_id)).execute()
        db.table("agent_keys").delete().eq("agent_id", str(agent_id)).execute()
        db.table("ai_agents").delete().eq("id", str(agent_id)).execute()
        print("[+] Test agent and related requests successfully cleaned up.")
    except Exception as cleanup_err:
        print(f"[-] Cleanup warning: {cleanup_err}")

    print("[+] Restoring spending limit policy rules...")
    db.table("merchant_policies").update({
        "rules": {"currency": "INR", "max_amount": 5000.0}
    }).eq("policy_name", "Maximum Order Value limit").eq("merchant_id", str(merchant_id)).execute()

    print("\n====================================================")
    print("[+] ALL E2E VERIFICATIONS PASSED SUCCESSFULLY!")
    print("====================================================")

if __name__ == "__main__":
    main()
