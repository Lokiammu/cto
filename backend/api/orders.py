from fastapi import APIRouter, Depends, status
from typing import List
from bson import ObjectId
from datetime import datetime, timedelta
import logging
import uuid

from backend.database import get_database
from backend.models.order import (
    Order,
    OrderCreate,
    OrderResponse,
    OrderTracking,
    OrderStatus,
    ReturnRequest
)
from backend.api.auth import get_current_user
from backend.services.payment import PaymentGateway
from backend.middleware.error_handlers import NotFoundError, ValidationError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/orders", tags=["orders"])


def calculate_loyalty_discount(user_tier: str, subtotal: float) -> float:
    """Calculate loyalty discount based on tier"""
    discount_rates = {
        "bronze": 0.0,
        "silver": 0.05,
        "gold": 0.10,
        "platinum": 0.15
    }
    rate = discount_rates.get(user_tier, 0.0)
    return subtotal * rate


def get_user_tier(points: int) -> str:
    """Determine user tier based on points"""
    if points >= 5000:
        return "platinum"
    elif points >= 2000:
        return "gold"
    elif points >= 500:
        return "silver"
    else:
        return "bronze"


@router.get("", response_model=List[OrderResponse])
async def list_orders(
    current_user: dict = Depends(get_current_user),
    limit: int = 20,
    offset: int = 0
):
    """
    List user's past orders
    Returns orders sorted by most recent first
    """
    db = get_database()
    user_id = str(current_user["_id"])
    
    cursor = db.orders.find(
        {"user_id": user_id}
    ).sort("created_at", -1).skip(offset).limit(limit)
    
    orders = await cursor.to_list(length=limit)
    
    result = []
    for order in orders:
        result.append(OrderResponse(
            id=str(order["_id"]),
            order_number=order["order_number"],
            items=order["items"],
            subtotal=order["subtotal"],
            discount=order.get("discount", 0.0),
            loyalty_discount=order.get("loyalty_discount", 0.0),
            tax=order["tax"],
            shipping=order["shipping"],
            total=order["total"],
            status=order["status"],
            payment_method=order["payment_method"],
            shipping_address=order["shipping_address"],
            tracking_number=order.get("tracking_number"),
            created_at=order["created_at"],
            updated_at=order["updated_at"]
        ))
    
    return result


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get order details by ID
    """
    db = get_database()
    user_id = str(current_user["_id"])
    
    if not ObjectId.is_valid(order_id):
        raise ValidationError("Invalid order ID")
    
    order = await db.orders.find_one({
        "_id": ObjectId(order_id),
        "user_id": user_id
    })
    
    if not order:
        raise NotFoundError("Order not found")
    
    return OrderResponse(
        id=str(order["_id"]),
        order_number=order["order_number"],
        items=order["items"],
        subtotal=order["subtotal"],
        discount=order.get("discount", 0.0),
        loyalty_discount=order.get("loyalty_discount", 0.0),
        tax=order["tax"],
        shipping=order["shipping"],
        total=order["total"],
        status=order["status"],
        payment_method=order["payment_method"],
        shipping_address=order["shipping_address"],
        tracking_number=order.get("tracking_number"),
        created_at=order["created_at"],
        updated_at=order["updated_at"]
    )


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_request: OrderCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create new order from cart
    - Validates cart
    - Processes payment
    - Creates order
    - Clears cart
    - Awards loyalty points
    """
    db = get_database()
    user_id = str(current_user["_id"])
    
    # Get cart
    cart = await db.carts.find_one({"_id": ObjectId(order_request.cart_id), "user_id": user_id})
    if not cart or not cart.get("items"):
        raise ValidationError("Cart is empty or not found")
    
    # Get address
    addresses = current_user.get("addresses", [])
    address = next((a for a in addresses if a.get("id") == order_request.delivery_address_id), None)
    if not address:
        raise NotFoundError("Delivery address not found")
    
    # Get payment method
    payment_methods = current_user.get("payment_methods", [])
    payment_method = next((p for p in payment_methods if p.get("id") == order_request.payment_method_id), None)
    if not payment_method:
        raise NotFoundError("Payment method not found")
    
    # Calculate totals
    items = cart["items"]
    subtotal = sum(item["subtotal"] for item in items)
    user_tier = get_user_tier(current_user.get("loyalty_points", 0))
    loyalty_discount = calculate_loyalty_discount(user_tier, subtotal)
    tax = (subtotal - loyalty_discount) * 0.08
    shipping = 0.0 if subtotal > 50 else 5.99
    total = subtotal - loyalty_discount + tax + shipping
    
    # Process payment
    payment_result = await PaymentGateway.process_payment(
        amount=total,
        payment_method=payment_method["type"],
        payment_details={
            "last_four": payment_method["last_four"],
            "brand": payment_method.get("brand")
        }
    )
    
    if payment_result["status"] != "success":
        raise ValidationError(f"Payment failed: {payment_result['message']}")
    
    # Create order
    order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    tracking_number = f"TRK-{uuid.uuid4().hex[:12].upper()}"
    
    order_data = {
        "user_id": user_id,
        "order_number": order_number,
        "items": items,
        "subtotal": subtotal,
        "discount": 0.0,
        "loyalty_discount": loyalty_discount,
        "tax": tax,
        "shipping": shipping,
        "total": total,
        "status": OrderStatus.confirmed,
        "payment_method": payment_method["type"],
        "payment_id": payment_result["payment_id"],
        "shipping_address": {
            "street": address["street"],
            "city": address["city"],
            "state": address["state"],
            "zip_code": address["zip_code"],
            "country": address["country"]
        },
        "tracking_number": tracking_number,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await db.orders.insert_one(order_data)
    order_id = str(result.inserted_id)
    
    # Clear cart
    await db.carts.update_one(
        {"_id": cart["_id"]},
        {"$set": {"items": [], "updated_at": datetime.utcnow()}}
    )
    
    # Award loyalty points (1 point per dollar)
    points_earned = int(total)
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$inc": {"loyalty_points": points_earned}}
    )
    
    logger.info(f"Order created: {order_number}, user: {user_id}, total: ${total}")
    
    # Return order
    order_data["_id"] = result.inserted_id
    return OrderResponse(
        id=order_id,
        order_number=order_number,
        items=items,
        subtotal=subtotal,
        discount=0.0,
        loyalty_discount=loyalty_discount,
        tax=tax,
        shipping=shipping,
        total=total,
        status=OrderStatus.confirmed,
        payment_method=payment_method["type"],
        shipping_address=order_data["shipping_address"],
        tracking_number=tracking_number,
        created_at=order_data["created_at"],
        updated_at=order_data["updated_at"]
    )


@router.get("/{order_id}/tracking", response_model=OrderTracking)
async def get_order_tracking(
    order_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get shipping status and tracking information
    """
    db = get_database()
    user_id = str(current_user["_id"])
    
    if not ObjectId.is_valid(order_id):
        raise ValidationError("Invalid order ID")
    
    order = await db.orders.find_one({
        "_id": ObjectId(order_id),
        "user_id": user_id
    })
    
    if not order:
        raise NotFoundError("Order not found")
    
    # Mock tracking history
    history = [
        {
            "status": "confirmed",
            "timestamp": order["created_at"].isoformat(),
            "location": "Order Processing Center",
            "description": "Order confirmed and being prepared"
        },
        {
            "status": "processing",
            "timestamp": (order["created_at"] + timedelta(hours=2)).isoformat(),
            "location": "Warehouse",
            "description": "Order is being packed"
        }
    ]
    
    if order["status"] in ["shipped", "delivered"]:
        history.append({
            "status": "shipped",
            "timestamp": (order["created_at"] + timedelta(days=1)).isoformat(),
            "location": "Distribution Center",
            "description": "Package shipped"
        })
    
    if order["status"] == "delivered":
        history.append({
            "status": "delivered",
            "timestamp": (order["created_at"] + timedelta(days=3)).isoformat(),
            "location": order["shipping_address"]["city"],
            "description": "Package delivered"
        })
    
    estimated_delivery = order["created_at"] + timedelta(days=5)
    
    return OrderTracking(
        order_id=order_id,
        order_number=order["order_number"],
        status=order["status"],
        tracking_number=order.get("tracking_number"),
        estimated_delivery=estimated_delivery,
        history=history
    )


@router.post("/{order_id}/return")
async def initiate_return(
    order_id: str,
    return_request: ReturnRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Initiate return request for an order
    """
    db = get_database()
    user_id = str(current_user["_id"])
    
    if not ObjectId.is_valid(order_id):
        raise ValidationError("Invalid order ID")
    
    order = await db.orders.find_one({
        "_id": ObjectId(order_id),
        "user_id": user_id
    })
    
    if not order:
        raise NotFoundError("Order not found")
    
    if order["status"] not in ["delivered"]:
        raise ValidationError("Only delivered orders can be returned")
    
    # Check if within return window (30 days)
    days_since_delivery = (datetime.utcnow() - order["created_at"]).days
    if days_since_delivery > 30:
        raise ValidationError("Return window has expired (30 days)")
    
    # Create return request
    return_id = str(uuid.uuid4())
    return_data = {
        "_id": ObjectId(return_id),
        "order_id": order_id,
        "user_id": user_id,
        "reason": return_request.reason,
        "items": return_request.items,
        "comments": return_request.comments,
        "status": "pending",
        "created_at": datetime.utcnow()
    }
    
    await db.returns.insert_one(return_data)
    
    # Update order status
    await db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {
            "$set": {
                "status": OrderStatus.returned,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    logger.info(f"Return initiated for order {order_id}, return_id: {return_id}")
    
    return {
        "message": "Return request submitted successfully",
        "return_id": return_id,
        "status": "pending"
    }
