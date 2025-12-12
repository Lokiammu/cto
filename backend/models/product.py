from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class Product(BaseModel):
    id: str = Field(alias="_id")
    name: str
    description: str
    category: str
    brand: str
    price: float
    images: List[str] = []
    colors: List[str] = []
    sizes: List[str] = []
    stock: int
    rating: float = 0.0
    reviews_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True


class ProductResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    brand: str
    price: float
    images: List[str]
    colors: List[str]
    sizes: List[str]
    stock: int
    stock_status: str  # in_stock, low_stock, out_of_stock
    rating: float
    reviews_count: int
    
    class Config:
        from_attributes = True


class ProductFilter(BaseModel):
    category: Optional[str] = None
    brand: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    search: Optional[str] = None
    limit: int = 20
    offset: int = 0


class InventoryResponse(BaseModel):
    product_id: str
    warehouse_stock: int
    store_stock: List[dict]  # [{store_name, location, stock}]
    total_available: int
    last_updated: datetime
