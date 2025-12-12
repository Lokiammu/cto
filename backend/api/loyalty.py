from fastapi import APIRouter, Depends, status
from typing import List
from bson import ObjectId
from datetime import datetime, timedelta
import logging

from backend.database import get_database
from backend.models.loyalty import (
    LoyaltyProfile,
    Coupon,
    TierInfo,
    ApplyCouponRequest,
    RedeemPointsRequest
)
from backend.api.auth import get_current_user
from backend.middleware.error_handlers import NotFoundError, ValidationError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/loyalty", tags=["loyalty"])


TIER_DEFINITIONS = {
    "bronze": {
        "name": "Bronze",
        "min_points": 0,
        "discount_percentage": 0.0,
        "benefits": ["Earn 1 point per dollar", "Birthday reward"]
    },
    "silver": {
        "name": "Silver",
        "min_points": 500,
        "discount_percentage": 5.0,
        "benefits": ["Earn 1.5 points per dollar", "5% discount", "Free shipping", "Early access to sales"]
    },
    "gold": {
        "name": "Gold",
        "min_points": 2000,
        "discount_percentage": 10.0,
        "benefits": ["Earn 2 points per dollar", "10% discount", "Free shipping", "Priority support", "Exclusive products"]
    },
    "platinum": {
        "name": "Platinum",
        "min_points": 5000,
        "discount_percentage": 15.0,
        "benefits": ["Earn 3 points per dollar", "15% discount", "Free shipping", "Dedicated support", "VIP events", "Birthday month rewards"]
    }
}


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


@router.get("/profile", response_model=LoyaltyProfile)
async def get_loyalty_profile(current_user: dict = Depends(get_current_user)):
    """
    Get user's loyalty tier and points balance
    """
    db = get_database()
    user_id = str(current_user["_id"])
    
    points_balance = current_user.get("loyalty_points", 0)
    tier = get_user_tier(points_balance)
    
    # Get lifetime stats (mock for now)
    points_earned_lifetime = points_balance + 500  # Mock data
    points_redeemed_lifetime = 100  # Mock data
    
    # Get available coupons
    now = datetime.utcnow()
    cursor = db.coupons.find({
        "is_active": True,
        "valid_from": {"$lte": now},
        "valid_until": {"$gte": now},
        "$or": [
            {"user_tier": tier},
            {"user_tier": {"$exists": False}}
        ]
    })
    coupons_data = await cursor.to_list(length=20)
    
    available_coupons = []
    for coupon in coupons_data:
        available_coupons.append(Coupon(
            id=str(coupon["_id"]),
            code=coupon["code"],
            description=coupon["description"],
            discount_type=coupon["discount_type"],
            discount_value=coupon["discount_value"],
            min_purchase=coupon["min_purchase"],
            max_discount=coupon.get("max_discount"),
            valid_from=coupon["valid_from"],
            valid_until=coupon["valid_until"],
            is_active=coupon["is_active"]
        ))
    
    tier_info = TIER_DEFINITIONS[tier]
    
    return LoyaltyProfile(
        user_id=user_id,
        points_balance=points_balance,
        tier=tier,
        tier_benefits=tier_info["benefits"],
        points_earned_lifetime=points_earned_lifetime,
        points_redeemed_lifetime=points_redeemed_lifetime,
        available_coupons=available_coupons
    )


@router.get("/coupons", response_model=List[Coupon])
async def get_available_coupons(current_user: dict = Depends(get_current_user)):
    """
    Get available coupons for user based on tier
    """
    db = get_database()
    
    points_balance = current_user.get("loyalty_points", 0)
    tier = get_user_tier(points_balance)
    
    now = datetime.utcnow()
    cursor = db.coupons.find({
        "is_active": True,
        "valid_from": {"$lte": now},
        "valid_until": {"$gte": now},
        "$or": [
            {"user_tier": tier},
            {"user_tier": {"$exists": False}}
        ]
    })
    coupons_data = await cursor.to_list(length=50)
    
    coupons = []
    for coupon in coupons_data:
        coupons.append(Coupon(
            id=str(coupon["_id"]),
            code=coupon["code"],
            description=coupon["description"],
            discount_type=coupon["discount_type"],
            discount_value=coupon["discount_value"],
            min_purchase=coupon["min_purchase"],
            max_discount=coupon.get("max_discount"),
            valid_from=coupon["valid_from"],
            valid_until=coupon["valid_until"],
            is_active=coupon["is_active"]
        ))
    
    return coupons


@router.post("/apply-coupon")
async def apply_coupon(
    request: ApplyCouponRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Apply coupon code to cart or order
    """
    db = get_database()
    
    # Find coupon
    coupon = await db.coupons.find_one({
        "code": request.coupon_code.upper(),
        "is_active": True
    })
    
    if not coupon:
        raise NotFoundError("Coupon not found or expired")
    
    # Check validity
    now = datetime.utcnow()
    if coupon["valid_from"] > now or coupon["valid_until"] < now:
        raise ValidationError("Coupon is not valid at this time")
    
    # Check tier requirement
    if "user_tier" in coupon:
        user_tier = get_user_tier(current_user.get("loyalty_points", 0))
        if user_tier != coupon["user_tier"]:
            raise ValidationError("You don't meet the tier requirement for this coupon")
    
    # Get cart to check min purchase
    if request.cart_id:
        cart = await db.carts.find_one({"_id": ObjectId(request.cart_id)})
        if not cart:
            raise NotFoundError("Cart not found")
        
        subtotal = sum(item["subtotal"] for item in cart.get("items", []))
        
        if subtotal < coupon["min_purchase"]:
            raise ValidationError(f"Minimum purchase of ${coupon['min_purchase']} required")
        
        # Calculate discount
        if coupon["discount_type"] == "percentage":
            discount = subtotal * (coupon["discount_value"] / 100)
            if coupon.get("max_discount"):
                discount = min(discount, coupon["max_discount"])
        else:  # fixed
            discount = coupon["discount_value"]
        
        return {
            "message": "Coupon applied successfully",
            "discount": discount,
            "code": coupon["code"]
        }
    
    return {"message": "Coupon is valid", "coupon": coupon}


@router.post("/redeem-points")
async def redeem_points(
    request: RedeemPointsRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Redeem loyalty points for discount
    100 points = $1 discount
    """
    db = get_database()
    user_id = str(current_user["_id"])
    
    # Check points balance
    points_balance = current_user.get("loyalty_points", 0)
    
    if request.points > points_balance:
        raise ValidationError("Insufficient points balance")
    
    if request.points < 100:
        raise ValidationError("Minimum 100 points required for redemption")
    
    # Calculate discount
    discount = request.points / 100  # 100 points = $1
    
    # Deduct points
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$inc": {"loyalty_points": -request.points}}
    )
    
    logger.info(f"User {user_id} redeemed {request.points} points for ${discount} discount")
    
    return {
        "message": "Points redeemed successfully",
        "points_redeemed": request.points,
        "discount": discount,
        "remaining_points": points_balance - request.points
    }


@router.get("/tiers", response_model=List[TierInfo])
async def get_tier_definitions():
    """
    List all tier definitions and benefits
    """
    tiers = []
    for tier_key, tier_data in TIER_DEFINITIONS.items():
        tiers.append(TierInfo(
            name=tier_data["name"],
            min_points=tier_data["min_points"],
            discount_percentage=tier_data["discount_percentage"],
            benefits=tier_data["benefits"]
        ))
    
    return tiers
