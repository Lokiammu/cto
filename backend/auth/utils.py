import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from backend.config import config

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=config.BCRYPT_COST)).decode('utf-8')

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=config.JWT_EXPIRY_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, config.JWT_SECRET, algorithm="HS256")
    return encoded_jwt

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=config.REFRESH_TOKEN_EXPIRY_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, config.JWT_SECRET, algorithm="HS256")
    return encoded_jwt

def decode_token(token: str):
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.PyJWTError:
        return None
