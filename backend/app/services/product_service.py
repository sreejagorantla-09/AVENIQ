from typing import List, Optional
from uuid import UUID
from app.db.client import get_db_client
from app.schemas.models import ProductCreate, AuditEventCreate
from app.services.audit_service import AuditService

class ProductService:
    @staticmethod
    def get_all_products() -> List[dict]:
        """
        Retrieves all active or draft products from the database (excluding archived).
        """
        db = get_db_client()
        # Exclude archived products from standard list
        response = db.table("products").select("*").neq("status", "archived").execute()
        return response.data

    @staticmethod
    def get_product_by_id(product_id: UUID) -> Optional[dict]:
        """
        Retrieves a single product by its UUID.
        """
        db = get_db_client()
        response = db.table("products").select("*").eq("id", str(product_id)).execute()
        if response.data:
            return response.data[0]
        return None

    @staticmethod
    def create_product(product_data: ProductCreate) -> dict:
        """
        Inserts a new product into the database and generates a PRODUCT_CREATED audit event.
        """
        db = get_db_client()
        data = {
            "merchant_id": str(product_data.merchant_id),
            "sku": product_data.sku,
            "name": product_data.name,
            "description": product_data.description,
            "category": product_data.category,
            "price": product_data.price,
            "currency": product_data.currency,
            "stock_quantity": product_data.stock_quantity,
            "status": product_data.status,
            "metadata": product_data.metadata
        }
        response = db.table("products").insert(data).execute()
        new_product = response.data[0]
        
        # Audit event
        audit_data = AuditEventCreate(
            merchant_id=product_data.merchant_id,
            event_type="PRODUCT_CREATED",
            actor_type="merchant",
            actor_id="merchant-admin",
            entity_type="product",
            entity_id=new_product["id"],
            action="create_product",
            decision="ALLOW",
            details={"sku": product_data.sku, "name": product_data.name}
        )
        AuditService.create_audit_event(audit_data)
        
        return new_product

    @staticmethod
    def update_product(product_id: UUID, product_data: dict) -> Optional[dict]:
        """
        Updates product attributes and generates a PRODUCT_UPDATED audit event.
        """
        db = get_db_client()
        # Fetch current record for merchant context
        current_res = db.table("products").select("*").eq("id", str(product_id)).execute()
        if not current_res.data:
            return None
        current_product = current_res.data[0]
        
        response = db.table("products").update(product_data).eq("id", str(product_id)).execute()
        if response.data:
            updated_product = response.data[0]
            # Audit event
            audit_data = AuditEventCreate(
                merchant_id=UUID(current_product["merchant_id"]),
                event_type="PRODUCT_UPDATED",
                actor_type="merchant",
                actor_id="merchant-admin",
                entity_type="product",
                entity_id=str(product_id),
                action="update_product",
                decision="ALLOW",
                details={"updated_fields": list(product_data.keys()), "sku": current_product["sku"]}
            )
            AuditService.create_audit_event(audit_data)
            return updated_product
        return None

    @staticmethod
    def delete_product(product_id: UUID) -> bool:
        """
        Soft deletes (archives) a product in the database and generates a PRODUCT_DELETED audit event.
        """
        db = get_db_client()
        # Fetch current record
        current_res = db.table("products").select("*").eq("id", str(product_id)).execute()
        if not current_res.data:
            return False
        current_product = current_res.data[0]
        
        # Soft delete by setting status to archived
        response = db.table("products").update({"status": "archived"}).eq("id", str(product_id)).execute()
        if response.data:
            # Audit event
            audit_data = AuditEventCreate(
                merchant_id=UUID(current_product["merchant_id"]),
                event_type="PRODUCT_DELETED",
                actor_type="merchant",
                actor_id="merchant-admin",
                entity_type="product",
                entity_id=str(product_id),
                action="archive_product",
                decision="ALLOW",
                details={"sku": current_product["sku"], "name": current_product["name"]}
            )
            AuditService.create_audit_event(audit_data)
            return True
        return False
