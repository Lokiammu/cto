from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    phone: Optional[str] = None
    profile: Optional[dict] = {}

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserInDB(UserBase):
    id: str # objectId as string
    password_hash: str
    created_at: datetime
    updated_at: datetime
    jwt_tokens: List[dict] = []

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int

class TokenData(BaseModel):
    user_id: str
    email: str
