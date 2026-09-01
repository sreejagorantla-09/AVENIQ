import re
import json
import logging
import httpx
from typing import Optional, Tuple
from app.core.config import settings

logger = logging.getLogger("aveniq.ai")

class IntentParser:
    @classmethod
    def parse_intent(cls, raw_request: str) -> Tuple[Optional[str], int, float]:
        """
        Parses a natural-language transaction proposal into structured fields (sku, quantity, unit_price).
        First attempts to use Gemini AI REST endpoint. If unconfigured or failing, falls back to a regex parser.
        Returns:
            Tuple[Optional[str], int, float]: (sku, quantity, unit_price)
        """
        # Try Gemini AI first
        if settings.GEMINI_API_KEY:
            try:
                sku, qty, price = cls._parse_with_gemini(raw_request)
                if sku:
                    logger.info(f"Gemini parsed intent successfully: SKU={sku}, Qty={qty}, Price={price}")
                    return sku, qty, price
            except Exception as e:
                logger.error(f"Gemini parsing failed: {e}. Falling back to regex parser.")

        # Fallback to Regex Parser
        logger.info("Using deterministic regex fallback parser.")
        return cls._parse_with_regex(raw_request)

    @classmethod
    def _parse_with_gemini(cls, raw_request: str) -> Tuple[Optional[str], int, float]:
        """
        Calls Gemini API directly using HTTP client.
        """
        prompt = f"""
Analyze the following natural language request from a commerce agent and convert it into a structured JSON response matching the schema.

Schema:
{{
  "sku": "string (the product SKU, e.g., 'S-WT-002')",
  "quantity": "integer (number of items requested, default to 1)",
  "unit_price": "float (price per unit proposed, default to 0.0 if not specified)"
}}

If the SKU is not specified but the product name is given, map it based on these catalog items:
- "Wireless Headphones": SKU is "W-HP-001"
- "Smart Watch": SKU is "S-WT-002"
- "Running Shoes": SKU is "R-SH-003"
- "Backpack": SKU is "B-PK-004"
- "Water Bottle": SKU is "W-BT-005"

If the request is not related to purchasing or you cannot parse the SKU, set "sku" to null.

Request: "{raw_request}"

Return ONLY valid JSON. No markdown backticks.
"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }
        
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                raise Exception(f"Gemini API returned code {response.status_code}: {response.text}")
                
            res_data = response.json()
            text_response = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
            
            # Clean up potential markdown formatting block wrapper
            if text_response.startswith("```json"):
                text_response = text_response[7:]
            if text_response.endswith("```"):
                text_response = text_response[:-3]
            text_response = text_response.strip()
            
            data = json.loads(text_response)
            sku = data.get("sku")
            quantity = int(data.get("quantity", 1))
            unit_price = float(data.get("unit_price", 0.0))
            return sku, quantity, unit_price

    @classmethod
    def _parse_with_regex(cls, raw_request: str) -> Tuple[Optional[str], int, float]:
        """
        Regex fallback to extract quantity, SKU (matching S-WT-002 format), and optional price.
        """
        # Look for standard SKUs like W-HP-001 or S-WT-002
        sku_match = re.search(r'\b([A-Z]-[A-Z]{2}-\d{3})\b', raw_request)
        sku = sku_match.group(1) if sku_match else None
        
        # If no explicit SKU match, check for product names
        if not sku:
            req_lower = raw_request.lower()
            if "headphone" in req_lower:
                sku = "W-HP-001"
            elif "watch" in req_lower:
                sku = "S-WT-002"
            elif "shoe" in req_lower:
                sku = "R-SH-003"
            elif "backpack" in req_lower:
                sku = "B-PK-004"
            elif "bottle" in req_lower:
                sku = "W-BT-005"

        # Match quantity (default 1 if not found)
        qty_match = re.search(r'\b(buy|purchase|get|want|bargain|negotiate)\s+(\d+)\b', raw_request, re.IGNORECASE)
        quantity = int(qty_match.group(2)) if qty_match else 1
        
        # Match price using structured patterns
        price = 0.0
        # 1. Search specifically for currency symbols first (₹, Rs, INR)
        price_match = re.search(r'(?:₹|rs\.?|inr\.?\s*)(\d+(?:\.\d{1,2})?)', raw_request, re.IGNORECASE)
        # 2. If not found, check for pattern "for <number>"
        if not price_match:
            price_match = re.search(r'\bfor\s+(\d+(?:\.\d{1,2})?)', raw_request, re.IGNORECASE)
            
        if price_match:
            try:
                price = float(price_match.group(1))
            except ValueError:
                pass
        else:
            # 3. Disambiguation check (look for numbers not matching quantity)
            for val in re.findall(r'\b(\d+(?:\.\d{1,2})?)\b', raw_request):
                try:
                    f_val = float(val)
                    if f_val != quantity:
                        price = f_val
                        break
                except ValueError:
                    pass

        return sku, quantity, price

    @classmethod
    def generate_approval_recommendation(cls, raw_request: str, policy_reason: str, rule_details: dict) -> str:
        """
        Generates an AI recommendation summary to assist the merchant with human-in-the-loop decisions.
        """
        if not settings.GEMINI_API_KEY:
            return f"Deterministic Policy Flagged: {policy_reason}."

        try:
            prompt = f"""
You are the AVENIQ Policy Reasoning Assistant. A purchase proposal has been flagged for human review.
Generate a concise, merchant-friendly recommendation (2-3 sentences max) explaining:
1. What the agent requested and what policy boundary was exceeded.
2. An analysis of whether this looks like a normal procurement request or a potential policy exploit.
3. A clear recommendation to approve or reject with a concise business justification.

Proposal Raw Request: "{raw_request}"
Policy Flag Reason: "{policy_reason}"
Policy Configuration Rules: {json.dumps(rule_details)}

Return ONLY the recommendation summary. No JSON wrappers, no markdown formatting blocks.
"""
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    res_data = response.json()
                    text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    return text
        except Exception as e:
            logger.error(f"Failed to generate Gemini recommendation: {e}")
            
        return f"Policy Flagged: {policy_reason}. Budget limit exceeded according to configured policy rules."

    @classmethod
    def generate_negotiation_counter_offer(cls, raw_request: str, catalog_price: float, counter_price: float, discount_pct: float) -> str:
        """
        Generates a conversational counter-offer response from the merchant vendor bot to the AI buyer agent.
        """
        if not settings.GEMINI_API_KEY:
            return f"Catalog price is ₹{catalog_price}. We can offer a volume discount at ₹{counter_price} per unit ({discount_pct}% off). Do you accept?"

        try:
            prompt = f"""
You are the AVENIQ Procurement Negotiator. An AI agent is bargaining for a purchase discount.
Generate a polite, professional vendor response (2 sentences max) stating:
1. The catalog listing price is ₹{catalog_price}.
2. We can offer a {discount_pct}% volume discount at ₹{counter_price} per unit.
3. Ask if the buyer agent wants to accept this offer.

Agent Prompt: "{raw_request}"

Return ONLY the response message. No markdown wrappers, no json blocks.
"""
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    res_data = response.json()
                    return res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            logger.error(f"Gemini negotiation response generation failed: {e}")
            
        return f"Catalog price is ₹{catalog_price}. We can offer a volume discount at ₹{counter_price} per unit ({discount_pct}% off). Do you accept?"
