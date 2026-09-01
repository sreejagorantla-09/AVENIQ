from typing import List, Tuple
from uuid import UUID
from app.db.client import get_db_client

class PolicyEvaluator:
    @staticmethod
    def evaluate_proposal(
        merchant_id: UUID,
        agent_id: UUID,
        sku: str,
        quantity: int,
        price: float
    ) -> Tuple[str, str, List[dict]]:
        """
        Deterministically evaluates an agent proposal against merchant limits, active policies, and catalog prices.
        Returns:
            Tuple[str, str, List[dict]]: (decision, reason, evaluated_rules)
            Decisions: ALLOW, DENY, REQUIRES_APPROVAL
        """
        db = get_db_client()
        evaluated_rules = []

        # 1. Fetch product details from DB
        prod_res = db.table("products") \
            .select("*") \
            .eq("sku", sku) \
            .eq("merchant_id", str(merchant_id)) \
            .eq("status", "active") \
            .execute()
            
        if not prod_res.data:
            return "DENY", f"Product with SKU '{sku}' is not active or does not exist in catalog.", [{"rule": "catalog_check", "status": "FAIL"}]
            
        product = prod_res.data[0]
        catalog_price = float(product["price"])
        stock_qty = int(product["stock_quantity"])
        category = product.get("category", "")

        # 2. Check stock availability
        if stock_qty < quantity:
            return "DENY", f"Insufficient stock. Requested: {quantity}, Available: {stock_qty}.", [{"rule": "stock_check", "status": "FAIL"}]
            
        evaluated_rules.append({"rule": "stock_check", "status": "PASS", "details": f"Available: {stock_qty}"})

        # 3. Check price matches catalog listing
        if price != catalog_price:
            return "DENY", f"Proposed price ₹{price} does not match catalog price ₹{catalog_price}.", [{"rule": "price_check", "status": "FAIL"}]
            
        evaluated_rules.append({"rule": "price_check", "status": "PASS", "details": f"Catalog price: {catalog_price}"})

        # 4. Fetch and evaluate merchant policies
        policy_res = db.table("merchant_policies") \
            .select("*") \
            .eq("merchant_id", str(merchant_id)) \
            .eq("is_active", True) \
            .order("priority", desc=False) \
            .execute()
            
        policies = policy_res.data or []
        total_value = quantity * price
        requires_approval = False

        for policy in policies:
            p_type = policy["policy_type"]
            p_rules = policy.get("rules", {})
            p_name = policy["policy_name"]

            # Evaluate spending limits
            if p_type == "spending_limit":
                limit_val = p_rules.get("limit_amount") or p_rules.get("max_amount")
                if limit_val is None:
                    continue
                limit = float(limit_val)
                approval_threshold = float(p_rules.get("requires_manual_approval_above") or p_rules.get("approval_threshold") or limit)
                
                # Check absolute cap
                if total_value > limit:
                    rule_entry = {"rule": p_name, "type": "spending_limit", "status": "FAIL", "details": f"Exceeded absolute cap ₹{limit}"}
                    evaluated_rules.append(rule_entry)
                    return "DENY", f"Total value ₹{total_value} exceeds absolute spending limit of ₹{limit} (Policy: '{p_name}').", evaluated_rules
                
                # Check manual approval threshold
                if total_value > approval_threshold:
                    requires_approval = True
                    rule_entry = {"rule": p_name, "type": "spending_limit", "status": "REQUIRES_APPROVAL", "details": f"Exceeds approval threshold ₹{approval_threshold}"}
                else:
                    rule_entry = {"rule": p_name, "type": "spending_limit", "status": "PASS", "details": f"Below threshold ₹{approval_threshold}"}
                
                evaluated_rules.append(rule_entry)

            # Evaluate restricted categories
            elif p_type == "restricted_categories":
                blocked = p_rules.get("blocked_categories", [])
                if category in blocked:
                    rule_entry = {"rule": p_name, "type": "category_restriction", "status": "FAIL", "details": f"Category '{category}' is blocked"}
                    evaluated_rules.append(rule_entry)
                    return "DENY", f"Purchase of category '{category}' is blocked by policy: '{p_name}'.", evaluated_rules
                
                rule_entry = {"rule": p_name, "type": "category_restriction", "status": "PASS", "details": f"Category '{category}' allowed"}
                evaluated_rules.append(rule_entry)

        # 5. Output final decision
        if requires_approval:
            return "REQUIRES_APPROVAL", f"Proposal of ₹{total_value} exceeds the automated clearance threshold and requires manual merchant approval.", evaluated_rules

        return "ALLOW", "Proposal matches all deterministic compliance and spending guidelines.", evaluated_rules

    @staticmethod
    def calculate_max_discount(merchant_id: UUID, sku: str, quantity: int) -> float:
        """
        Calculates the maximum discount percentage allowed under the active volume_discount policies.
        """
        db = get_db_client()
        policy_res = db.table("merchant_policies") \
            .select("*") \
            .eq("merchant_id", str(merchant_id)) \
            .eq("policy_type", "spending_limit") \
            .eq("is_active", True) \
            .execute()
            
        max_discount = 0.0
        has_volume_policy = False
        for policy in (policy_res.data or []):
            rules = policy.get("rules", {})
            p_name = (policy.get("policy_name") or policy.get("name") or "").lower()
            p_type = (policy.get("policy_type") or "").lower()
            
            if rules.get("type") == "volume_discount" or p_type in ("volume_discount", "discount", "negotiation") or "volume" in p_name or "discount" in p_name or "negotiation" in p_name:
                has_volume_policy = True
                min_qty = int(rules.get("min_qty") or rules.get("quantity_threshold") or 1)
                discount = float(rules.get("discount_percentage") or rules.get("discount") or rules.get("max_discount") or 10.0)
                if quantity >= min_qty:
                    max_discount = max(max_discount, discount)
                
        # Standard merchant policy allows 10% max bargaining discount if no explicit volume threshold policy restricts it
        if max_discount == 0.0 and not has_volume_policy:
            max_discount = 10.0

        return max_discount

    @classmethod
    def evaluate_proposal_negotiated(
        cls,
        merchant_id: UUID,
        agent_id: UUID,
        sku: str,
        quantity: int,
        price: float
    ) -> Tuple[str, str, List[dict]]:
        """
        Validates a final negotiated price proposal before checkout against catalog price, stock,
        limits, and maximum allowed volume discount.
        """
        db = get_db_client()
        evaluated_rules = []

        # 1. Fetch product
        prod_res = db.table("products").select("*").eq("sku", sku).eq("merchant_id", str(merchant_id)).eq("status", "active").execute()
        if not prod_res.data:
            return "DENY", f"Product SKU '{sku}' is inactive.", [{"rule": "catalog_check", "status": "FAIL"}]
            
        product = prod_res.data[0]
        catalog_price = float(product["price"])
        stock_qty = int(product["stock_quantity"])

        # 2. Concurrency Stock Guard check
        if stock_qty < quantity:
            return "DENY", f"Concurrency Guard: Insufficient stock. Requested: {quantity}, Available: {stock_qty}.", [{"rule": "stock_check", "status": "FAIL"}]

        # 3. Check price is valid within maximum allowed volume discount
        max_disc = cls.calculate_max_discount(merchant_id, sku, quantity)
        minimum_price = catalog_price * (1 - max_disc / 100.0)

        # Allow matches up to minimum_price boundaries
        if price < minimum_price:
            return "DENY", f"Negotiated price ₹{price} is below the authorized minimum boundary ₹{minimum_price} (Max allowed discount: {max_disc}%).", [{"rule": "negotiated_price_check", "status": "FAIL"}]

        # 4. Check spending limit caps
        policy_res = db.table("merchant_policies") \
            .select("*") \
            .eq("merchant_id", str(merchant_id)) \
            .eq("is_active", True) \
            .execute()
            
        total_value = quantity * price
        for policy in (policy_res.data or []):
            if policy["policy_type"] == "spending_limit":
                p_rules = policy.get("rules", {})
                limit_val = p_rules.get("limit_amount") or p_rules.get("max_amount")
                if limit_val is None:
                    continue
                limit = float(limit_val)
                if total_value > limit:
                    return "DENY", f"Negotiated total value ₹{total_value} exceeds absolute spending limit of ₹{limit}.", [{"rule": "spending_limit_check", "status": "FAIL"}]

        return "ALLOW", "Negotiated proposal satisfies final compliance validations.", evaluated_rules
