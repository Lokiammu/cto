from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from bson import ObjectId


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


class Address(BaseModel):
    id: Optional[str] = None
    street: str
    city: str
    state: str
    zip_code: str
    country: str = "USA"
    is_default: bool = False


class PaymentMethod(BaseModel):
    id: Optional[str] = None
    type: str  # card, upi, gift_card
    last_four: str
    brand: Optional[str] = None
    is_default: bool = False


class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v
    
    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        return v


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None


class User(UserBase):
    id: str = Field(alias="_id")
    hashed_password: str
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    addresses: List[Address] = []
    payment_methods: List[PaymentMethod] = []
    loyalty_points: int = 0
    loyalty_tier: str = "bronze"
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    loyalty_points: int
    loyalty_tier: str
    
    class Config:
        from_attributes = True
