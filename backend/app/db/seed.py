import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.client import get_db_client

def seed():
    try:
        db = get_db_client()
    except Exception as e:
        print(f"Seeding skipped: Database client not configured. Error: {e}")
        return

    print("Starting AVENIQ database seeding...")
    
    # 1. Seed merchant
    merchant_data = {
        "merchant_code": "AVENIQ_MERCHANT_001",
        "business_name": "AVENIQ Demo Commerce",
        "business_type": "eCommerce",
        "description": "AVENIQ Control Plane Demo Store",
        "website_url": "https://demo.aveniq.ai",
        "country": "India",
        "currency": "INR",
        "trust_score": 98.5,
        "status": "active"
    }
    
    m_check = db.table("merchants").select("id").eq("merchant_code", "AVENIQ_MERCHANT_001").execute()
    if m_check.data:
        merchant_id = m_check.data[0]["id"]
        print(f"Demo merchant already exists with ID: {merchant_id}")
    else:
        m_res = db.table("merchants").insert(merchant_data).execute()
        merchant_id = m_res.data[0]["id"]
        print(f"Created demo merchant with ID: {merchant_id}")
        
    # 2. Seed products
    products = [
        {
            "sku": "W-HP-001",
            "name": "Wireless Headphones",
            "description": "Noise-cancelling over-ear bluetooth headphones",
            "category": "Electronics",
            "price": 1999.00,
            "stock_quantity": 100,
            "status": "active",
            "metadata": {"brand": "AcousticTech", "color": "charcoal"}
        },
        {
            "sku": "S-WT-002",
            "name": "Smart Watch",
            "description": "Fitness tracking watch with heart rate monitor",
            "category": "Electronics",
            "price": 3499.00,
            "stock_quantity": 50,
            "status": "active",
            "metadata": {"brand": "WristSmart", "water_resistance": "5ATM"}
        },
        {
            "sku": "R-SH-003",
            "name": "Running Shoes",
            "description": "Comfortable lightweight running trainers",
            "category": "Footwear",
            "price": 2499.00,
            "stock_quantity": 75,
            "status": "active",
            "metadata": {"brand": "Stryder", "size": "UK-9"}
        },
        {
            "sku": "B-PK-004",
            "name": "Backpack",
            "description": "Waterproof laptop backpack with USB port",
            "category": "Travel",
            "price": 1299.00,
            "stock_quantity": 120,
            "status": "active",
            "metadata": {"brand": "PackAll", "capacity": "25L"}
        },
        {
            "sku": "W-BT-005",
            "name": "Water Bottle",
            "description": "Insulated stainless steel double-walled flask",
            "category": "Home",
            "price": 499.00,
            "stock_quantity": 300,
            "status": "active",
            "metadata": {"brand": "HydroFlow", "capacity": "750ml"}
        },
    ]
    
    # Clear old products referencing this merchant
    db.table("products").delete().eq("merchant_id", merchant_id).execute()
    print("Cleaned up existing product records.")
    
    for p in products:
        p["merchant_id"] = merchant_id
        db.table("products").insert(p).execute()
    print(f"Seeded {len(products)} product entries.")

    # 3. Seed policies
    policies = [
        {
            "policy_type": "spending_limit",
            "policy_name": "Maximum Order Value limit",
            "description": "Flags transactions exceeding a threshold of ₹5000",
            "rules": {"max_amount": 5000.0, "currency": "INR"},
            "priority": 10,
            "is_active": True
        },
        {
            "policy_type": "delivery",
            "policy_name": "Maximum Shipping SLA",
            "description": "Enforces delivery within a maximum of 7 days",
            "rules": {"max_delivery_days": 7},
            "priority": 20,
            "is_active": True
        },
        {
            "policy_type": "inventory",
            "policy_name": "Stock Availability Policy",
            "description": "Requires item stock quantity to be greater than zero",
            "rules": {"min_stock_required": 1},
            "priority": 30,
            "is_active": True
        }
    ]
    
    # Clear old policies referencing this merchant
    db.table("merchant_policies").delete().eq("merchant_id", merchant_id).execute()
    print("Cleaned up existing merchant policies.")
    
    for pol in policies:
        pol["merchant_id"] = merchant_id
        db.table("merchant_policies").insert(pol).execute()
    print(f"Seeded {len(policies)} merchant policies.")

    # 4. Seed agent
    agent_data = {
        "merchant_id": merchant_id,
        "agent_code": "DEMO_AGENT_001",
        "name": "ProcureBot v1",
        "description": "Autonomous purchasing agent for office supplies and gear",
        "agent_type": "buyer",
        "status": "active",
        "capabilities": {"max_single_tx": 3000}
    }
    
    a_check = db.table("ai_agents").select("id").eq("agent_code", "DEMO_AGENT_001").execute()
    if a_check.data:
        agent_id = a_check.data[0]["id"]
        print(f"Demo AI agent already exists with ID: {agent_id}")
    else:
        a_res = db.table("ai_agents").insert(agent_data).execute()
        agent_id = a_res.data[0]["id"]
        print(f"Created demo AI agent with ID: {agent_id}")

    print("AVENIQ database seeding completed successfully.")

if __name__ == "__main__":
    seed()
