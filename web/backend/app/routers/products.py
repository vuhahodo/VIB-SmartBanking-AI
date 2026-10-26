from fastapi import APIRouter, HTTPException, status

from ..ai_engine import PRODUCTS, PRODUCTS_BY_CODE
from ..schemas import ProductOut

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
def list_products():
    return PRODUCTS


@router.get("/{product_code}", response_model=ProductOut)
def get_product(product_code: str):
    product = PRODUCTS_BY_CODE.get(product_code)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sản phẩm không tồn tại")
    return product
