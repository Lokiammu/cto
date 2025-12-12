import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_signup(client: AsyncClient, test_db):
    """Test user signup"""
    response = await client.post("/api/auth/signup", json={
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "securepassword123",
        "full_name": "New User"
    })
    
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    
    # Verify user was created in database
    user = await test_db.users.find_one({"email": "newuser@example.com"})
    assert user is not None
    assert user["username"] == "newuser"
    
    # Cleanup
    await test_db.users.delete_one({"email": "newuser@example.com"})


@pytest.mark.asyncio
async def test_signup_duplicate_email(client: AsyncClient, test_user):
    """Test signup with duplicate email"""
    response = await client.post("/api/auth/signup", json={
        "email": test_user["email"],
        "username": "differentuser",
        "password": "password123"
    })
    
    assert response.status_code == 400
    assert "already registered" in response.json()["error"].lower()


@pytest.mark.asyncio
async def test_signin(client: AsyncClient, test_user):
    """Test user signin"""
    response = await client.post("/api/auth/signin", json={
        "email": test_user["email"],
        "password": "testpassword123"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_signin_invalid_password(client: AsyncClient, test_user):
    """Test signin with invalid password"""
    response = await client.post("/api/auth/signin", json={
        "email": test_user["email"],
        "password": "wrongpassword"
    })
    
    assert response.status_code == 401
    assert "invalid" in response.json()["error"].lower()


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, auth_headers):
    """Test get current user profile"""
    response = await client.get("/api/auth/me", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "email" in data
    assert "username" in data


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, auth_headers):
    """Test user logout"""
    response = await client.post("/api/auth/logout", headers=auth_headers)
    
    assert response.status_code == 200
    assert "logged out" in response.json()["message"].lower()


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, test_user):
    """Test token refresh"""
    from backend.services.auth_service import create_refresh_token
    
    refresh_token = create_refresh_token(
        data={"sub": str(test_user["_id"]), "username": test_user["username"]}
    )
    
    response = await client.post("/api/auth/refresh", json={
        "refresh_token": refresh_token
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
