import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_cart(client: AsyncClient, auth_headers):
    """Test getting user cart"""
    response = await client.get("/api/cart", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "items_count" in data


@pytest.mark.asyncio
async def test_add_to_cart(client: AsyncClient, auth_headers, test_product):
    """Test adding item to cart"""
    product_id = str(test_product["_id"])
    
    response = await client.post(
        "/api/cart/items",
        headers=auth_headers,
        json={
            "product_id": product_id,
            "quantity": 2,
            "color": "Black",
            "size": "M"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "message" in data
    assert data["items_count"] > 0


@pytest.mark.asyncio
async def test_add_to_cart_insufficient_stock(client: AsyncClient, auth_headers, test_product):
    """Test adding item with insufficient stock"""
    product_id = str(test_product["_id"])
    
    response = await client.post(
        "/api/cart/items",
        headers=auth_headers,
        json={
            "product_id": product_id,
            "quantity": 1000  # More than available stock
        }
    )
    
    assert response.status_code == 400
    assert "stock" in response.json()["error"].lower()


@pytest.mark.asyncio
async def test_get_cart_total(client: AsyncClient, auth_headers):
    """Test getting cart total with discounts"""
    response = await client.get("/api/cart/total", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "subtotal" in data
    assert "loyalty_discount" in data
    assert "tax" in data
    assert "shipping" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_checkout(client: AsyncClient, auth_headers, test_product, test_db, test_user):
    """Test checkout process"""
    # First, add item to cart
    product_id = str(test_product["_id"])
    await client.post(
        "/api/cart/items",
        headers=auth_headers,
        json={
            "product_id": product_id,
            "quantity": 1
        }
    )
    
    response = await client.post("/api/cart/checkout", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "total" in data
