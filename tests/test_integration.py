from fastapi.testclient import TestClient
from backend.main import app
from backend.config import config
from backend.db.database import db
import pytest
from faker import Faker

fake = Faker()

# Use a TestClient as context manager to trigger startup/shutdown events
@pytest.fixture(scope="module")
def client():
    # Override DB name for testing
    original_db_name = config.DB_NAME
    config.DB_NAME = "test_ai_sales_chatbot"
    
    with TestClient(app) as c:
        yield c
        
    # Cleanup
    # We need to manually connect to drop because the client has closed the connection
    from pymongo import MongoClient
    client = MongoClient(config.MONGO_URI)
    client.drop_database("test_ai_sales_chatbot")
    config.DB_NAME = original_db_name

def test_signup(client):
    email = fake.email()
    password = "password123"
    response = client.post("/auth/signup", json={
        "email": email,
        "password": password,
        "phone": fake.phone_number()
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data

def test_signup_duplicate_email(client):
    email = fake.email()
    password = "password123"
    
    # First signup
    client.post("/auth/signup", json={
        "email": email,
        "password": password
    })
    
    # Second signup
    response = client.post("/auth/signup", json={
        "email": email,
        "password": password
    })
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

def test_signin(client):
    email = fake.email()
    password = "password123"
    
    # Signup first
    client.post("/auth/signup", json={
        "email": email,
        "password": password
    })
    
    # Signin
    response = client.post("/auth/signin", json={
        "email": email,
        "password": password
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

def test_signin_wrong_password(client):
    email = fake.email()
    password = "password123"
    
    # Signup first
    client.post("/auth/signup", json={
        "email": email,
        "password": password
    })
    
    # Signin with wrong password
    response = client.post("/auth/signin", json={
        "email": email,
        "password": "wrongpassword"
    })
    assert response.status_code == 401

def test_logout(client):
    email = fake.email()
    password = "password123"
    
    # Signup
    signup_res = client.post("/auth/signup", json={
        "email": email,
        "password": password
    })
    token = signup_res.json()["access_token"]
    
    # Logout
    response = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
