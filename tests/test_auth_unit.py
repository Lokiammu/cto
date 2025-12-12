from backend.auth.utils import get_password_hash, verify_password, create_access_token, decode_token
from backend.config import config
import time
from datetime import timedelta

def test_password_hashing():
    password = "secure_password"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong_password", hashed)

def test_jwt_creation_verification():
    data = {"sub": "12345", "email": "test@example.com"}
    token = create_access_token(data)
    decoded = decode_token(token)
    assert decoded["sub"] == "12345"
    assert decoded["email"] == "test@example.com"
    assert "exp" in decoded

def test_jwt_expiry():
    data = {"sub": "12345"}
    # Create token that expires in 1 second
    token = create_access_token(data, expires_delta=timedelta(seconds=-1))
    decoded = decode_token(token)
    # Depending on how decode_token handles expiry (it should return None or raise error if verified)
    # In utils.py I implemented:
    # try: payload = jwt.decode(...); return payload; except jwt.PyJWTError: return None
    assert decoded is None
