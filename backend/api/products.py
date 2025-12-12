from fastapi import APIRouter, Query, Depends
from typing import List, Optional
from bson import ObjectId
import logging

from backend.database import get_database
from backend.models.product import ProductResponse, ProductFilter, InventoryResponse
from backend.middleware.error_handlers import NotFoundError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/products", tags=["products"])


def get_stock_status(stock: int) -> str:
    """Determine stock status"""
    if stock == 0:
        return "out_of_stock"
    elif stock < 10:
        return "low_stock"
    else:
        return "in_stock"


@router.get("", response_model=List[ProductResponse])
async def list_products(
    category: Optional[str] = None,
    brand: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    search: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    List all products with pagination and filters
    - Supports filtering by category, brand, price range
    - Full-text search on name and description
    - Returns paginated results
    """
    db = get_database()
    
    # Build query
    query = {}
    
    if category:
        query["category"] = category
    
    if brand:
        query["brand"] = brand
    
    if min_price is not None or max_price is not None:
        query["price"] = {}
        if min_price is not None:
            query["price"]["$gte"] = min_price
        if max_price is not None:
            query["price"]["$lte"] = max_price
    
    if search:
        query["$text"] = {"$search": search}
    
    # Execute query
    cursor = db.products.find(query).skip(offset).limit(limit)
    products = await cursor.to_list(length=limit)
    
    # Format response
    result = []
    for product in products:
        result.append(ProductResponse(
            id=str(product["_id"]),
            name=product["name"],
            description=product["description"],
            category=product["category"],
            brand=product["brand"],
            price=product["price"],
            images=product.get("images", []),
            colors=product.get("colors", []),
            sizes=product.get("sizes", []),
            stock=product.get("stock", 0),
            stock_status=get_stock_status(product.get("stock", 0)),
            rating=product.get("rating", 0.0),
            reviews_count=product.get("reviews_count", 0)
        ))
    
    return result


@router.get("/search", response_model=List[ProductResponse])
async def search_products(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Search products by name or category (fuzzy matching)
    Uses MongoDB text search
    """
    db = get_database()
    
    # Text search
    cursor = db.products.find(
        {"$text": {"$search": q}},
        {"score": {"$meta": "textScore"}}
    ).sort([("score", {"$meta": "textScore"})]).limit(limit)
    
    products = await cursor.to_list(length=limit)
    
    # Format response
    result = []
    for product in products:
        result.append(ProductResponse(
            id=str(product["_id"]),
            name=product["name"],
            description=product["description"],
            category=product["category"],
            brand=product["brand"],
            price=product["price"],
            images=product.get("images", []),
            colors=product.get("colors", []),
            sizes=product.get("sizes", []),
            stock=product.get("stock", 0),
            stock_status=get_stock_status(product.get("stock", 0)),
            rating=product.get("rating", 0.0),
            reviews_count=product.get("reviews_count", 0)
        ))
    
    return result


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str):
    """
    Get single product details by ID
    """
    db = get_database()
    
    if not ObjectId.is_valid(product_id):
        raise NotFoundError("Invalid product ID")
    
    product = await db.products.find_one({"_id": ObjectId(product_id)})
    
    if not product:
        raise NotFoundError("Product not found")
    
    return ProductResponse(
        id=str(product["_id"]),
        name=product["name"],
        description=product["description"],
        category=product["category"],
        brand=product["brand"],
        price=product["price"],
        images=product.get("images", []),
        colors=product.get("colors", []),
        sizes=product.get("sizes", []),
        stock=product.get("stock", 0),
        stock_status=get_stock_status(product.get("stock", 0)),
        rating=product.get("rating", 0.0),
        reviews_count=product.get("reviews_count", 0)
    )


@router.get("/inventory/{product_id}", response_model=InventoryResponse)
async def get_inventory(product_id: str):
    """
    Check stock levels by product
    Returns warehouse and nearby store stock levels
    """
    db = get_database()
    
    if not ObjectId.is_valid(product_id):
        raise NotFoundError("Invalid product ID")
    
    product = await db.products.find_one({"_id": ObjectId(product_id)})
    
    if not product:
        raise NotFoundError("Product not found")
    
    # Mock store stock data
    # In production, this would query a real inventory system
    warehouse_stock = product.get("stock", 0)
    store_stock = [
        {"store_name": "Downtown Store", "location": "123 Main St", "stock": 5},
        {"store_name": "Mall Location", "location": "456 Shopping Blvd", "stock": 3},
        {"store_name": "Airport Store", "location": "789 Airport Rd", "stock": 8},
    ]
    
    total_available = warehouse_stock + sum(s["stock"] for s in store_stock)
    
    return InventoryResponse(
        product_id=product_id,
        warehouse_stock=warehouse_stock,
        store_stock=store_stock,
        total_available=total_available,
        last_updated=product.get("updated_at", product.get("created_at"))
    )
