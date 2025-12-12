from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class TierInfo(BaseModel):
    name: str
    min_points: int
    discount_percentage: float
    benefits: List[str]


class Coupon(BaseModel):
    id: str
    code: str
    description: str
    discount_type: str  # percentage, fixed
    discount_value: float
    min_purchase: float
    max_discount: Optional[float] = None
    valid_from: datetime
    valid_until: datetime
    is_active: bool = True


class LoyaltyProfile(BaseModel):
    user_id: str
    points_balance: int
    tier: str
    tier_benefits: List[str]
    points_earned_lifetime: int
    points_redeemed_lifetime: int
    available_coupons: List[Coupon]


class ApplyCouponRequest(BaseModel):
    coupon_code: str
    cart_id: Optional[str] = None
    order_id: Optional[str] = None


class RedeemPointsRequest(BaseModel):
    points: int
    cart_id: str
