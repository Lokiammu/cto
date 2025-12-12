from fastapi import APIRouter, Depends, status
from typing import List
from bson import ObjectId
from datetime import datetime
import logging
import uuid

from backend.database import get_database
from backend.models.user import UserResponse, UserUpdate, Address, PaymentMethod
from backend.api.auth import get_current_user
from backend.middleware.error_handlers import NotFoundError, ValidationError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/profile", response_model=UserResponse)
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """
    Get user profile information
    """
    return UserResponse(
        id=str(current_user["_id"]),
        email=current_user["email"],
        username=current_user["username"],
        full_name=current_user.get("full_name"),
        phone=current_user.get("phone"),
        is_active=current_user.get("is_active", True),
        is_verified=current_user.get("is_verified", False),
        created_at=current_user["created_at"],
        loyalty_points=current_user.get("loyalty_points", 0),
        loyalty_tier=current_user.get("loyalty_tier", "bronze")
    )


@router.put("/profile", response_model=UserResponse)
async def update_user_profile(
    update: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update user profile information
    """
    db = get_database()
    user_id = str(current_user["_id"])
    
    update_data = {}
    if update.full_name is not None:
        update_data["full_name"] = update.full_name
    if update.phone is not None:
        update_data["phone"] = update.phone
    
    if not update_data:
        raise ValidationError("No fields to update")
    
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_data}
    )
    
    # Fetch updated user
    updated_user = await db.users.find_one({"_id": ObjectId(user_id)})
    
    return UserResponse(
        id=str(updated_user["_id"]),
        email=updated_user["email"],
        username=updated_user["username"],
        full_name=updated_user.get("full_name"),
        phone=updated_user.get("phone"),
        is_active=updated_user.get("is_active", True),
        is_verified=updated_user.get("is_verified", False),
        created_at=updated_user["created_at"],
        loyalty_points=updated_user.get("loyalty_points", 0),
        loyalty_tier=updated_user.get("loyalty_tier", "bronze")
    )


@router.get("/addresses", response_model=List[Address])
async def list_addresses(current_user: dict = Depends(get_current_user)):
    """
    List saved addresses for user
    """
    addresses = current_user.get("addresses", [])
    return addresses


@router.post("/addresses", response_model=Address, status_code=status.HTTP_201_CREATED)
async def add_address(
    address: Address,
    current_user: dict = Depends(get_current_user)
):
    """
    Add new address to user profile
    """
    db = get_database()
    user_id = str(current_user["_id"])
    
    # Generate ID for address
    address_id = str(uuid.uuid4())
    address_data = address.dict()
    address_data["id"] = address_id
    
    # If this is set as default, unset other defaults
    if address.is_default:
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"addresses.$[].is_default": False}}
        )
    
    # Add address
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$push": {"addresses": address_data}}
    )
    
    logger.info(f"Address added for user {user_id}")
    
    return Address(**address_data)


@router.delete("/addresses/{address_id}")
async def delete_address(
    address_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete an address
    """
    db = get_database()
    user_id = str(current_user["_id"])
    
    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$pull": {"addresses": {"id": address_id}}}
    )
    
    if result.modified_count == 0:
        raise NotFoundError("Address not found")
    
    return {"message": "Address deleted successfully"}


@router.get("/payment-methods", response_model=List[PaymentMethod])
async def list_payment_methods(current_user: dict = Depends(get_current_user)):
    """
    List saved payment methods for user
    """
    payment_methods = current_user.get("payment_methods", [])
    return payment_methods


@router.post("/payment-methods", response_model=PaymentMethod, status_code=status.HTTP_201_CREATED)
async def add_payment_method(
    payment_method: PaymentMethod,
    current_user: dict = Depends(get_current_user)
):
    """
    Add new payment method to user profile
    Mock implementation - in production, integrate with payment processor
    """
    db = get_database()
    user_id = str(current_user["_id"])
    
    # Generate ID for payment method
    payment_id = str(uuid.uuid4())
    payment_data = payment_method.dict()
    payment_data["id"] = payment_id
    
    # Validate payment method type
    valid_types = ["card", "upi", "gift_card"]
    if payment_method.type not in valid_types:
        raise ValidationError(f"Payment method type must be one of: {', '.join(valid_types)}")
    
    # If this is set as default, unset other defaults
    if payment_method.is_default:
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"payment_methods.$[].is_default": False}}
        )
    
    # Add payment method
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$push": {"payment_methods": payment_data}}
    )
    
    logger.info(f"Payment method added for user {user_id}")
    
    return PaymentMethod(**payment_data)


@router.delete("/payment-methods/{payment_id}")
async def delete_payment_method(
    payment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a payment method
    """
    db = get_database()
    user_id = str(current_user["_id"])
    
    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$pull": {"payment_methods": {"id": payment_id}}}
    )
    
    if result.modified_count == 0:
        raise NotFoundError("Payment method not found")
    
    return {"message": "Payment method deleted successfully"}
