from fastapi import APIRouter, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
from bson import ObjectId
import logging

from backend.database import get_database
from backend.models.user import UserCreate, UserResponse
from backend.models.auth import Token, LoginRequest, SignupRequest, RefreshToken
from backend.services.auth_service import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token_type
)
from backend.middleware.error_handlers import AuthError, ValidationError, NotFoundError
from backend.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()

# Simple in-memory rate limiting (in production, use Redis)
login_attempts = {}


def check_rate_limit(email: str):
    """Check rate limit for login attempts"""
    now = datetime.utcnow()
    if email in login_attempts:
        attempts, last_attempt = login_attempts[email]
        if (now - last_attempt).seconds < 60 and attempts >= 5:
            raise AuthError("Too many login attempts. Please try again later.")
        if (now - last_attempt).seconds >= 60:
            login_attempts[email] = (1, now)
        else:
            login_attempts[email] = (attempts + 1, now)
    else:
        login_attempts[email] = (1, now)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    db = get_database()
    
    # Check if token is revoked
    revoked = await db.revoked_tokens.find_one({"token": token})
    if revoked:
        raise AuthError("Token has been revoked")
    
    # Decode token
    token_data = decode_token(token)
    
    # Get user from database
    user = await db.users.find_one({"_id": ObjectId(token_data.user_id)})
    if not user:
        raise NotFoundError("User not found")
    
    if not user.get("is_active", True):
        raise AuthError("User account is inactive")
    
    return user


@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
async def signup(request: SignupRequest):
    """
    Register a new user
    - Validates input
    - Hashes password
    - Returns JWT tokens
    """
    db = get_database()
    
    # Check if user already exists
    existing_user = await db.users.find_one({
        "$or": [
            {"email": request.email},
            {"username": request.username}
        ]
    })
    
    if existing_user:
        if existing_user["email"] == request.email:
            raise ValidationError("Email already registered")
        else:
            raise ValidationError("Username already taken")
    
    # Create user
    user_data = {
        "email": request.email,
        "username": request.username,
        "full_name": request.full_name,
        "hashed_password": get_password_hash(request.password),
        "is_active": True,
        "is_verified": False,
        "created_at": datetime.utcnow(),
        "addresses": [],
        "payment_methods": [],
        "loyalty_points": 0,
        "loyalty_tier": "bronze"
    }
    
    result = await db.users.insert_one(user_data)
    user_id = str(result.inserted_id)
    
    # Create tokens
    access_token = create_access_token(
        data={"sub": user_id, "username": request.username}
    )
    refresh_token = create_refresh_token(
        data={"sub": user_id, "username": request.username}
    )
    
    logger.info(f"New user registered: {request.email}")
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post("/signin", response_model=Token)
async def signin(request: LoginRequest):
    """
    Authenticate user and return JWT tokens
    - Verifies credentials
    - Rate limits login attempts
    - Returns access and refresh tokens
    """
    db = get_database()
    
    # Check rate limit
    check_rate_limit(request.email)
    
    # Find user
    user = await db.users.find_one({"email": request.email})
    if not user:
        raise AuthError("Invalid email or password")
    
    # Verify password
    if not verify_password(request.password, user["hashed_password"]):
        raise AuthError("Invalid email or password")
    
    # Check if user is active
    if not user.get("is_active", True):
        raise AuthError("User account is inactive")
    
    user_id = str(user["_id"])
    
    # Create tokens
    access_token = create_access_token(
        data={"sub": user_id, "username": user["username"]}
    )
    refresh_token = create_refresh_token(
        data={"sub": user_id, "username": user["username"]}
    )
    
    logger.info(f"User signed in: {request.email}")
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post("/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Logout user by revoking JWT token
    """
    db = get_database()
    token = credentials.credentials
    
    # Decode token to get expiration
    token_data = decode_token(token)
    
    # Add token to revoked list
    await db.revoked_tokens.insert_one({
        "token": token,
        "revoked_at": datetime.utcnow(),
        "expires_at": token_data.exp
    })
    
    logger.info(f"User logged out: {token_data.user_id}")
    
    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=Token)
async def refresh_token(request: RefreshToken):
    """
    Get new access token using refresh token
    """
    db = get_database()
    
    # Verify it's a refresh token
    if not verify_token_type(request.refresh_token, "refresh"):
        raise AuthError("Invalid refresh token")
    
    # Check if token is revoked
    revoked = await db.revoked_tokens.find_one({"token": request.refresh_token})
    if revoked:
        raise AuthError("Refresh token has been revoked")
    
    # Decode token
    token_data = decode_token(request.refresh_token)
    
    # Verify user still exists
    user = await db.users.find_one({"_id": ObjectId(token_data.user_id)})
    if not user:
        raise NotFoundError("User not found")
    
    # Create new access token
    access_token = create_access_token(
        data={"sub": token_data.user_id, "username": token_data.username}
    )
    
    return Token(
        access_token=access_token,
        refresh_token=request.refresh_token,
        token_type="bearer"
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """
    Get current user profile
    Requires JWT authentication
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
