from fastapi import APIRouter, HTTPException, Path, Response
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from postgrest.exceptions import APIError
from app.schemas.models import ProductCreate, ProductResponse
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Products"])

class ProductUpdate(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    stock_quantity: Optional[int] = None
    status: Optional[str] = None
    metadata: Optional[dict] = None

@router.get("", response_model=List[ProductResponse])
def get_products():
    """
    List all active and draft products in the catalog.
    """
    try:
        return ProductService.get_all_products()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Database service not available or unconfigured")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: UUID = Path(..., description="The UUID of the product to retrieve")):
    """
    Retrieve details of a product by UUID.
    """
    try:
        product = ProductService.get_product_by_id(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product
    except HTTPException:
        raise
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Database service not available or unconfigured")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("", response_model=ProductResponse, status_code=201)
def create_product(product_data: ProductCreate):
    """
    Create a new product catalog entry.
    """
    try:
        return ProductService.create_product(product_data)
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Database service not available or unconfigured")
    except APIError as e:
        # Check specific database constraint violation codes
        # 23503 = foreign key violation
        # 23505 = unique constraint violation
        if e.code == "23503":
            raise HTTPException(
                status_code=409,
                detail=f"Conflict: The merchant_id '{product_data.merchant_id}' does not exist."
            )
        elif e.code == "23505":
            raise HTTPException(
                status_code=409,
                detail=f"Conflict: A product with SKU '{product_data.sku}' already exists."
            )
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: UUID = Path(..., description="The UUID of the product to update"),
    update_data: ProductUpdate = ...
):
    """
    Update details of a product entry.
    """
    try:
        data = {k: v for k, v in update_data.model_dump().items() if v is not None}
        if not data:
            raise HTTPException(status_code=400, detail="No update fields provided.")
            
        product = ProductService.update_product(product_id, data)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product
    except HTTPException:
        raise
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Database service not available or unconfigured")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{product_id}", status_code=200)
def delete_product(product_id: UUID = Path(..., description="The UUID of the product to archive")):
    """
    Soft delete (archive) a product.
    """
    try:
        success = ProductService.delete_product(product_id)
        if not success:
            raise HTTPException(status_code=404, detail="Product not found")
        return {"success": True, "message": "Product successfully archived"}
    except HTTPException:
        raise
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Database service not available or unconfigured")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")
