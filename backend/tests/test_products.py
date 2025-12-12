import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_products(client: AsyncClient, test_product):
    """Test listing products"""
    response = await client.get("/api/products")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    
    # Verify product structure
    product = data[0]
    assert "id" in product
    assert "name" in product
    assert "price" in product
    assert "stock_status" in product


@pytest.mark.asyncio
async def test_get_product(client: AsyncClient, test_product):
    """Test getting single product"""
    product_id = str(test_product["_id"])
    response = await client.get(f"/api/products/{product_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == product_id
    assert data["name"] == test_product["name"]


@pytest.mark.asyncio
async def test_get_product_not_found(client: AsyncClient):
    """Test getting non-existent product"""
    response = await client.get("/api/products/507f1f77bcf86cd799439011")
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_search_products(client: AsyncClient, test_product):
    """Test product search"""
    response = await client.get("/api/products/search?q=Test")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_inventory(client: AsyncClient, test_product):
    """Test getting product inventory"""
    product_id = str(test_product["_id"])
    response = await client.get(f"/api/products/inventory/{product_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert "product_id" in data
    assert "warehouse_stock" in data
    assert "store_stock" in data
    assert "total_available" in data


@pytest.mark.asyncio
async def test_filter_products_by_category(client: AsyncClient, test_product):
    """Test filtering products by category"""
    response = await client.get(f"/api/products?category={test_product['category']}")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_filter_products_by_price(client: AsyncClient, test_product):
    """Test filtering products by price range"""
    response = await client.get("/api/products?min_price=50&max_price=150")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
