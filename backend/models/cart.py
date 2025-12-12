from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class CartItem(BaseModel):
    id: str
    product_id: str
    product_name: str
    product_image: str
    quantity: int
    price: float
    color: Optional[str] = None
    size: Optional[str] = None
    subtotal: float


class CartItemCreate(BaseModel):
    product_id: str
    quantity: int = 1
    color: Optional[str] = None
    size: Optional[str] = None


class CartItemUpdate(BaseModel):
    quantity: int


class Cart(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    items: List[CartItem] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True


class CartResponse(BaseModel):
    id: str
    items: List[CartItem]
    subtotal: float
    discount: float
    loyalty_discount: float
    total: float
    items_count: int
    
    class Config:
        from_attributes = True


class CartTotal(BaseModel):
    subtotal: float
    discount: float
    loyalty_discount: float
    tax: float
    shipping: float
    total: float
