import pytest
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from httpx import AsyncClient
from backend.main import app
from backend.config import settings
from backend.database import db


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db():
    """Create test database connection"""
    client = AsyncIOMotorClient(settings.mongodb_url)
    test_db = client["test_ecommerce_db"]
    
    # Set test database
    db.client = client
    db.db = test_db
    
    yield test_db
    
    # Cleanup
    await client.drop_database("test_ecommerce_db")
    client.close()


@pytest.fixture
async def client(test_db):
    """Create test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_user(test_db):
    """Create a test user"""
    from backend.services.auth_service import get_password_hash
    from datetime import datetime
    
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "hashed_password": get_password_hash("testpassword123"),
        "full_name": "Test User",
        "is_active": True,
        "is_verified": True,
        "created_at": datetime.utcnow(),
        "addresses": [],
        "payment_methods": [],
        "loyalty_points": 100,
        "loyalty_tier": "bronze"
    }
    
    result = await test_db.users.insert_one(user_data)
    user_data["_id"] = result.inserted_id
    
    yield user_data
    
    # Cleanup
    await test_db.users.delete_one({"_id": result.inserted_id})


@pytest.fixture
async def auth_headers(test_user):
    """Get authentication headers for test user"""
    from backend.services.auth_service import create_access_token
    
    access_token = create_access_token(
        data={"sub": str(test_user["_id"]), "username": test_user["username"]}
    )
    
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
async def test_product(test_db):
    """Create a test product"""
    from datetime import datetime
    
    product_data = {
        "name": "Test Product",
        "description": "Test product description",
        "category": "Electronics",
        "brand": "TestBrand",
        "price": 99.99,
        "images": ["https://example.com/image.jpg"],
        "colors": ["Black", "White"],
        "sizes": ["M", "L"],
        "stock": 50,
        "rating": 4.5,
        "reviews_count": 10,
        "created_at": datetime.utcnow()
    }
    
    result = await test_db.products.insert_one(product_data)
    product_data["_id"] = result.inserted_id
    
    yield product_data
    
    # Cleanup
    await test_db.products.delete_one({"_id": result.inserted_id})
