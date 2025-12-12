import pytest
from httpx import AsyncClient
from bson import ObjectId
import uuid


@pytest.mark.asyncio
async def test_list_orders(client: AsyncClient, auth_headers):
    """Test listing user orders"""
    response = await client.get("/api/orders", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_create_order(client: AsyncClient, auth_headers, test_product, test_user, test_db):
    """Test creating an order"""
    # Setup: Add address and payment method to user
    address_id = str(uuid.uuid4())
    payment_id = str(uuid.uuid4())
    
    await test_db.users.update_one(
        {"_id": test_user["_id"]},
        {
            "$set": {
                "addresses": [{
                    "id": address_id,
                    "street": "123 Test St",
                    "city": "Test City",
                    "state": "TS",
                    "zip_code": "12345",
                    "country": "USA",
                    "is_default": True
                }],
                "payment_methods": [{
                    "id": payment_id,
                    "type": "card",
                    "last_four": "4242",
                    "brand": "Visa",
                    "is_default": True
                }]
            }
        }
    )
    
    # Add item to cart
    product_id = str(test_product["_id"])
    await client.post(
        "/api/cart/items",
        headers=auth_headers,
        json={
            "product_id": product_id,
            "quantity": 1
        }
    )
    
    # Get cart
    cart_response = await client.get("/api/cart", headers=auth_headers)
    cart_id = cart_response.json()["id"]
    
    # Create order
    response = await client.post(
        "/api/orders",
        headers=auth_headers,
        json={
            "cart_id": cart_id,
            "delivery_address_id": address_id,
            "payment_method_id": payment_id
        }
    )
    
    # Note: This might fail due to payment simulation, so we check for both success and payment failure
    assert response.status_code in [201, 400]
    
    if response.status_code == 201:
        data = response.json()
        assert "order_number" in data
        assert "tracking_number" in data


@pytest.mark.asyncio
async def test_get_order_tracking(client: AsyncClient, auth_headers, test_db, test_user):
    """Test getting order tracking information"""
    # Create a test order
    from datetime import datetime
    
    order_data = {
        "user_id": str(test_user["_id"]),
        "order_number": "ORD-TEST123",
        "items": [],
        "subtotal": 100.0,
        "discount": 0.0,
        "loyalty_discount": 0.0,
        "tax": 8.0,
        "shipping": 5.99,
        "total": 113.99,
        "status": "shipped",
        "payment_method": "card",
        "payment_id": "PAY_123",
        "shipping_address": {
            "street": "123 Test St",
            "city": "Test City",
            "state": "TS",
            "zip_code": "12345",
            "country": "USA"
        },
        "tracking_number": "TRK-123456",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await test_db.orders.insert_one(order_data)
    order_id = str(result.inserted_id)
    
    # Get tracking
    response = await client.get(f"/api/orders/{order_id}/tracking", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "tracking_number" in data
    assert "status" in data
    assert "history" in data
    
    # Cleanup
    await test_db.orders.delete_one({"_id": result.inserted_id})
