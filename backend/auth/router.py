from fastapi import APIRouter, HTTPException, Depends, status, Request, Header
from fastapi.security import OAuth2PasswordBearer
from backend.auth.models import UserCreate, Token, UserBase, UserInDB
from backend.auth.repository import UserRepository
from backend.auth.utils import verify_password, create_access_token, create_refresh_token, decode_token
from backend.db.database import db
from backend.config import config
from datetime import datetime, timedelta
import time

router = APIRouter(prefix="/auth", tags=["auth"])

# Simple in-memory rate limiter
login_attempts = {}
BLOCK_TIME = 900 # 15 minutes
MAX_ATTEMPTS = 5

def check_rate_limit(request: Request):
    client_ip = request.client.host
    now = time.time()
    
    if client_ip in login_attempts:
        # Filter out old attempts
        login_attempts[client_ip] = [t for t in login_attempts[client_ip] if now - t < BLOCK_TIME]
        if len(login_attempts[client_ip]) >= MAX_ATTEMPTS:
            raise HTTPException(status_code=429, detail="Too many login attempts. Please try again later.")
    return client_ip

def record_login_attempt(ip: str):
    now = time.time()
    if ip not in login_attempts:
        login_attempts[ip] = []
    login_attempts[ip].append(now)

def get_user_repo():
    return UserRepository(db.get_db().users)

class LoginRequest(UserBase):
    password: str

@router.post("/signup", response_model=Token)
async def signup(user: UserCreate, repo: UserRepository = Depends(get_user_repo)):
    existing_user = repo.get_by_email(user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    new_user = repo.create(user)
    
    # Create tokens
    access_token = create_access_token(data={"sub": new_user["id"], "email": new_user["email"]})
    refresh_token = create_refresh_token(data={"sub": new_user["id"]})
    
    repo.add_token(new_user["id"], refresh_token)
    
    # Create customer profile (basic)
    db.get_db().customers.insert_one({
        "user_id": new_user["_id"], # ObjectId
        "loyalty_tier": "silver",
        "points": 0,
        "preferences": {},
        "browsing_history": [],
        "wishlist": []
    })

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": config.JWT_EXPIRY_MINUTES * 60
    }

@router.post("/signin", response_model=Token)
async def signin(
    login_data: LoginRequest, 
    request: Request, 
    repo: UserRepository = Depends(get_user_repo),
    x_session_id: str = Header(None)
):
    ip = check_rate_limit(request)
    
    user = repo.get_by_email(login_data.email)
    if not user or not verify_password(login_data.password, user["password_hash"]):
        record_login_attempt(ip)
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    # Create tokens
    access_token = create_access_token(data={"sub": user["id"], "email": user["email"]})
    refresh_token = create_refresh_token(data={"sub": user["id"]})
    
    repo.add_token(user["id"], refresh_token)
    
    # Update last login
    repo.collection.update_one({"_id": user["_id"]}, {"$set": {"last_login": datetime.now()}})
    
    # Session linking
    if x_session_id:
        db.get_db().channel_sessions.update_one(
            {"session_id": x_session_id},
            {"$set": {"user_id": user["_id"]}}
        )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": config.JWT_EXPIRY_MINUTES * 60
    }

@router.post("/logout")
async def logout(
    request: Request,
    repo: UserRepository = Depends(get_user_repo),
    authorization: str = Header(None)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    scheme, token = authorization.split()
    if scheme.lower() != 'bearer':
         raise HTTPException(status_code=401, detail="Invalid authentication scheme")
         
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload.get("sub")
    if user_id:
        repo.revoke_token(user_id, token)
        
    return {"message": "Successfully logged out"}
