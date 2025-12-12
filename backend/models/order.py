from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class OrderStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    processing = "processing"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"
    returned = "returned"


class OrderItem(BaseModel):
    product_id: str
    product_name: str
    product_image: str
    quantity: int
    price: float
    color: Optional[str] = None
    size: Optional[str] = None
    subtotal: float


class ShippingAddress(BaseModel):
    street: str
    city: str
    state: str
    zip_code: str
    country: str


class Order(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    order_number: str
    items: List[OrderItem]
    subtotal: float
    discount: float
    loyalty_discount: float
    tax: float
    shipping: float
    total: float
    status: OrderStatus = OrderStatus.pending
    payment_method: str
    payment_id: Optional[str] = None
    shipping_address: ShippingAddress
    tracking_number: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True


class OrderCreate(BaseModel):
    cart_id: str
    delivery_address_id: str
    payment_method_id: str


class OrderResponse(BaseModel):
    id: str
    order_number: str
    items: List[OrderItem]
    subtotal: float
    discount: float
    loyalty_discount: float
    tax: float
    shipping: float
    total: float
    status: OrderStatus
    payment_method: str
    shipping_address: ShippingAddress
    tracking_number: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class OrderTracking(BaseModel):
    order_id: str
    order_number: str
    status: OrderStatus
    tracking_number: Optional[str] = None
    estimated_delivery: Optional[datetime] = None
    history: List[dict]  # [{status, timestamp, location, description}]


class ReturnRequest(BaseModel):
    reason: str
    items: List[str]  # item IDs to return
    comments: Optional[str] = None
