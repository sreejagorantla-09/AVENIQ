import os
import sys
import io
import httpx

# Force stdout to use UTF-8 on Windows command lines to print currency symbols safely
if sys.platform.startswith("win"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def main():
    api_key = os.environ.get("AVENIQ_AGENT_API_KEY")
    if not api_key:
        print("FAIL: AVENIQ_AGENT_API_KEY environment variable is not set.")
        sys.exit(1)
        
    base_url = "http://127.0.0.1:8000/api/v1"
    headers = {
        "X-Agent-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    print("Testing GET /agent/products...")
    try:
        res_products = httpx.get(f"{base_url}/agent/products", headers=headers, timeout=10.0)
        print(f"Products status: {res_products.status_code}")
        print(f"Products response: {res_products.text}")
        
        if res_products.status_code != 200:
            print("FAIL: GET /agent/products did not return HTTP 200")
            sys.exit(1)
            
        products = res_products.json()
        skus = [p.get("sku") for p in products]
        if "S-WT-002" not in skus:
            print("FAIL: SKU 'S-WT-002' not found in products list")
            sys.exit(1)
            
        print("[+] SKU 'S-WT-002' found in catalog.")
    except Exception as e:
        print(f"FAIL: GET /agent/products request failed: {e}")
        sys.exit(1)
        
    print("\nTesting POST /agent/negotiate...")
    nego_payload = {
        "raw_request": "I want to negotiate 1 Smart Watch (sku: S-WT-002) for 3200 INR"
    }
    try:
        res_negotiate = httpx.post(f"{base_url}/agent/negotiate", headers=headers, json=nego_payload, timeout=10.0)
        print(f"Negotiate status: {res_negotiate.status_code}")
        print(f"Negotiate response: {res_negotiate.text}")
        
        if res_negotiate.status_code != 200:
            print("FAIL: POST /agent/negotiate did not return HTTP 200")
            sys.exit(1)
            
        print("\nPASS")
    except Exception as e:
        print(f"FAIL: POST /agent/negotiate request failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
