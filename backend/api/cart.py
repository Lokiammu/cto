from fastapi import APIRouter, Depends, status
from typing import List
from bson import ObjectId
from datetime import datetime
import logging
import uuid

from backend.database import get_database
from backend.models.cart import (
    CartResponse,
    CartItemCreate,
    CartItemUpdate,
    CartTotal,
    CartItem
)
from backend.api.auth import get_current_user
from backend.middleware.error_handlers import NotFoundError, ValidationError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cart", tags=["cart"])


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


@router.get("", response_model=CartResponse)
async def get_cart(current_user: dict = Depends(get_current_user)):
    """
    Get user's current cart
    Requires JWT authentication
    """
    db = get_database()
    user_id = str(current_user["_id"])
    
    # Find or create cart
    cart = await db.carts.find_one({"user_id": user_id})
    
    if not cart:
        # Create empty cart
        cart_data = {
            "user_id": user_id,
            "items": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = await db.carts.insert_one(cart_data)
        cart_data["_id"] = result.inserted_id
        cart = cart_data
    
    # Calculate totals
    items = cart.get("items", [])
    subtotal = sum(item["subtotal"] for item in items)
    discount = 0.0
    loyalty_discount = calculate_loyalty_discount(
        current_user.get("loyalty_tier", "bronze"),
        subtotal
    )
    total = subtotal - discount - loyalty_discount
    
    return CartResponse(
        id=str(cart["_id"]),
        items=items,
        subtotal=subtotal,
        discount=discount,
        loyalty_discount=loyalty_discount,
        total=total,
        items_count=len(items)
    )


@router.post("/items", status_code=status.HTTP_201_CREATED)
async def add_to_cart(
    item: CartItemCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Add item to cart
    - Validates product exists
    - Checks stock availability
    - Updates quantity if item already in cart
    """
    db = get_database()
    user_id = str(current_user["_id"])
    
    # Validate product
    if not ObjectId.is_valid(item.product_id):
        raise ValidationError("Invalid product ID")
    
    product = await db.products.find_one({"_id": ObjectId(item.product_id)})
    if not product:
        raise NotFoundError("Product not found")
    
    # Check stock
    if product.get("stock", 0) < item.quantity:
        raise ValidationError("Insufficient stock")
    
    # Find or create cart
    cart = await db.carts.find_one({"user_id": user_id})
    
    if not cart:
        cart_data = {
            "user_id": user_id,
            "items": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = await db.carts.insert_one(cart_data)
        cart = await db.carts.find_one({"_id": result.inserted_id})
    
    # Check if item already in cart
    items = cart.get("items", [])
    existing_item = None
    
    for idx, cart_item in enumerate(items):
        if (cart_item["product_id"] == item.product_id and
            cart_item.get("color") == item.color and
            cart_item.get("size") == item.size):
            existing_item = idx
            break
    
    if existing_item is not None:
        # Update quantity
        new_quantity = items[existing_item]["quantity"] + item.quantity
        if product.get("stock", 0) < new_quantity:
            raise ValidationError("Insufficient stock")
        
        items[existing_item]["quantity"] = new_quantity
        items[existing_item]["subtotal"] = new_quantity * product["price"]
    else:
        # Add new item
        cart_item = CartItem(
            id=str(uuid.uuid4()),
            product_id=item.product_id,
            product_name=product["name"],
            product_image=product.get("images", [""])[0] if product.get("images") else "",
            quantity=item.quantity,
            price=product["price"],
            color=item.color,
            size=item.size,
            subtotal=item.quantity * product["price"]
        )
        items.append(cart_item.dict())
    
    # Update cart
    await db.carts.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "items": items,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return {"message": "Item added to cart", "items_count": len(items)}


@router.put("/items/{item_id}")
async def update_cart_item(
    item_id: str,
    update: CartItemUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update item quantity in cart
    """
    db = get_database()
    user_id = str(current_user["_id"])
    
    cart = await db.carts.find_one({"user_id": user_id})
    if not cart:
        raise NotFoundError("Cart not found")
    
    items = cart.get("items", [])
    item_found = False
    
    for idx, cart_item in enumerate(items):
        if cart_item["id"] == item_id:
            # Validate stock
            product = await db.products.find_one({"_id": ObjectId(cart_item["product_id"])})
            if not product:
                raise NotFoundError("Product not found")
            
            if product.get("stock", 0) < update.quantity:
                raise ValidationError("Insufficient stock")
            
            # Update quantity
            items[idx]["quantity"] = update.quantity
            items[idx]["subtotal"] = update.quantity * cart_item["price"]
            item_found = True
            break
    
    if not item_found:
        raise NotFoundError("Item not found in cart")
    
    # Update cart
    await db.carts.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "items": items,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return {"message": "Cart item updated"}


@router.delete("/items/{item_id}")
async def remove_from_cart(
    item_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Remove item from cart
    """
    db = get_database()
    user_id = str(current_user["_id"])
    
    cart = await db.carts.find_one({"user_id": user_id})
    if not cart:
        raise NotFoundError("Cart not found")
    
    items = cart.get("items", [])
    items = [item for item in items if item["id"] != item_id]
    
    # Update cart
    await db.carts.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "items": items,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return {"message": "Item removed from cart", "items_count": len(items)}


@router.get("/total", response_model=CartTotal)
async def get_cart_total(current_user: dict = Depends(get_current_user)):
    """
    Get cart total with loyalty discount applied
    """
    db = get_database()
    user_id = str(current_user["_id"])
    
    cart = await db.carts.find_one({"user_id": user_id})
    
    if not cart or not cart.get("items"):
        return CartTotal(
            subtotal=0.0,
            discount=0.0,
            loyalty_discount=0.0,
            tax=0.0,
            shipping=0.0,
            total=0.0
        )
    
    items = cart.get("items", [])
    subtotal = sum(item["subtotal"] for item in items)
    discount = 0.0
    loyalty_discount = calculate_loyalty_discount(
        current_user.get("loyalty_tier", "bronze"),
        subtotal
    )
    tax = (subtotal - discount - loyalty_discount) * 0.08  # 8% tax
    shipping = 0.0 if subtotal > 50 else 5.99  # Free shipping over $50
    total = subtotal - discount - loyalty_discount + tax + shipping
    
    return CartTotal(
        subtotal=subtotal,
        discount=discount,
        loyalty_discount=loyalty_discount,
        tax=tax,
        shipping=shipping,
        total=total
    )


@router.post("/checkout")
async def checkout(current_user: dict = Depends(get_current_user)):
    """
    Proceed to payment
    Returns checkout session details
    """
    db = get_database()
    user_id = str(current_user["_id"])
    
    cart = await db.carts.find_one({"user_id": user_id})
    
    if not cart or not cart.get("items"):
        raise ValidationError("Cart is empty")
    
    # Calculate totals
    items = cart.get("items", [])
    subtotal = sum(item["subtotal"] for item in items)
    loyalty_discount = calculate_loyalty_discount(
        current_user.get("loyalty_tier", "bronze"),
        subtotal
    )
    tax = (subtotal - loyalty_discount) * 0.08
    shipping = 0.0 if subtotal > 50 else 5.99
    total = subtotal - loyalty_discount + tax + shipping
    
    checkout_session = {
        "session_id": str(uuid.uuid4()),
        "cart_id": str(cart["_id"]),
        "items": items,
        "subtotal": subtotal,
        "loyalty_discount": loyalty_discount,
        "tax": tax,
        "shipping": shipping,
        "total": total
    }
    
    return checkout_session
