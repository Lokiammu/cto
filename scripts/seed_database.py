"""
Seed database with sample data for testing and development
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.config import settings
from backend.services.auth_service import get_password_hash


async def seed_database():
    """Seed database with sample data"""
    print("Connecting to MongoDB...")
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.mongodb_db_name]
    
    print("Clearing existing data...")
    await db.users.delete_many({})
    await db.products.delete_many({})
    await db.coupons.delete_many({})
    
    print("Creating sample users...")
    users = [
        {
            "email": "john@example.com",
            "username": "john",
            "hashed_password": get_password_hash("password123"),
            "full_name": "John Doe",
            "phone": "+1234567890",
            "is_active": True,
            "is_verified": True,
            "created_at": datetime.utcnow(),
            "addresses": [
                {
                    "id": "addr1",
                    "street": "123 Main St",
                    "city": "San Francisco",
                    "state": "CA",
                    "zip_code": "94102",
                    "country": "USA",
                    "is_default": True
                }
            ],
            "payment_methods": [
                {
                    "id": "pay1",
                    "type": "card",
                    "last_four": "4242",
                    "brand": "Visa",
                    "is_default": True
                }
            ],
            "loyalty_points": 1500,
            "loyalty_tier": "silver"
        },
        {
            "email": "jane@example.com",
            "username": "jane",
            "hashed_password": get_password_hash("password123"),
            "full_name": "Jane Smith",
            "phone": "+1987654321",
            "is_active": True,
            "is_verified": True,
            "created_at": datetime.utcnow(),
            "addresses": [],
            "payment_methods": [],
            "loyalty_points": 3000,
            "loyalty_tier": "gold"
        }
    ]
    
    await db.users.insert_many(users)
    print(f"Created {len(users)} users")
    
    print("Creating sample products...")
    products = [
        {
            "name": "Wireless Headphones",
            "description": "Premium noise-cancelling wireless headphones with 30-hour battery life",
            "category": "Electronics",
            "brand": "AudioTech",
            "price": 299.99,
            "images": [
                "https://images.unsplash.com/photo-1505740420928-5e560c06d30e",
                "https://images.unsplash.com/photo-1484704849700-f032a568e944"
            ],
            "colors": ["Black", "Silver", "Blue"],
            "sizes": [],
            "stock": 50,
            "rating": 4.5,
            "reviews_count": 128,
            "created_at": datetime.utcnow()
        },
        {
            "name": "Smart Watch Pro",
            "description": "Advanced fitness tracking smartwatch with heart rate monitor and GPS",
            "category": "Electronics",
            "brand": "TechWear",
            "price": 399.99,
            "images": [
                "https://images.unsplash.com/photo-1523275335684-37898b6baf30",
                "https://images.unsplash.com/photo-1546868871-7041f2a55e12"
            ],
            "colors": ["Black", "Silver", "Rose Gold"],
            "sizes": ["Small", "Medium", "Large"],
            "stock": 35,
            "rating": 4.7,
            "reviews_count": 256,
            "created_at": datetime.utcnow()
        },
        {
            "name": "Laptop Backpack",
            "description": "Durable water-resistant backpack with laptop compartment and USB charging port",
            "category": "Accessories",
            "brand": "TravelGear",
            "price": 79.99,
            "images": [
                "https://images.unsplash.com/photo-1553062407-98eeb64c6a62",
                "https://images.unsplash.com/photo-1548036328-c9fa89d128fa"
            ],
            "colors": ["Black", "Gray", "Navy"],
            "sizes": [],
            "stock": 120,
            "rating": 4.3,
            "reviews_count": 89,
            "created_at": datetime.utcnow()
        },
        {
            "name": "Mechanical Keyboard",
            "description": "RGB mechanical gaming keyboard with Cherry MX switches",
            "category": "Electronics",
            "brand": "GameTech",
            "price": 149.99,
            "images": [
                "https://images.unsplash.com/photo-1587829741301-dc798b83add3",
                "https://images.unsplash.com/photo-1595225476474-87563907a212"
            ],
            "colors": ["Black", "White"],
            "sizes": [],
            "stock": 75,
            "rating": 4.8,
            "reviews_count": 342,
            "created_at": datetime.utcnow()
        },
        {
            "name": "Running Shoes",
            "description": "Lightweight cushioned running shoes for all-day comfort",
            "category": "Footwear",
            "brand": "SportFit",
            "price": 129.99,
            "images": [
                "https://images.unsplash.com/photo-1542291026-7eec264c27ff",
                "https://images.unsplash.com/photo-1539185441755-769473a23570"
            ],
            "colors": ["Black", "White", "Red", "Blue"],
            "sizes": ["7", "8", "9", "10", "11", "12"],
            "stock": 200,
            "rating": 4.6,
            "reviews_count": 567,
            "created_at": datetime.utcnow()
        },
        {
            "name": "Coffee Maker",
            "description": "Programmable coffee maker with thermal carafe and auto-brew feature",
            "category": "Home & Kitchen",
            "brand": "BrewMaster",
            "price": 89.99,
            "images": [
                "https://images.unsplash.com/photo-1517668808822-9ebb02f2a0e6",
                "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085"
            ],
            "colors": ["Black", "Stainless Steel"],
            "sizes": [],
            "stock": 45,
            "rating": 4.4,
            "reviews_count": 178,
            "created_at": datetime.utcnow()
        },
        {
            "name": "Yoga Mat",
            "description": "Non-slip eco-friendly yoga mat with carrying strap",
            "category": "Sports",
            "brand": "ZenFit",
            "price": 39.99,
            "images": [
                "https://images.unsplash.com/photo-1601925260368-ae2f83cf8b7f",
                "https://images.unsplash.com/photo-1592432678016-e910b452ee9a"
            ],
            "colors": ["Purple", "Blue", "Pink", "Green"],
            "sizes": [],
            "stock": 150,
            "rating": 4.5,
            "reviews_count": 234,
            "created_at": datetime.utcnow()
        },
        {
            "name": "Desk Lamp LED",
            "description": "Adjustable LED desk lamp with USB charging port and touch controls",
            "category": "Home & Office",
            "brand": "LightWorks",
            "price": 54.99,
            "images": [
                "https://images.unsplash.com/photo-1565894087972-86f8c26ba2d8",
                "https://images.unsplash.com/photo-1507473885765-e6ed057f782c"
            ],
            "colors": ["Black", "White", "Silver"],
            "sizes": [],
            "stock": 90,
            "rating": 4.6,
            "reviews_count": 156,
            "created_at": datetime.utcnow()
        }
    ]
    
    await db.products.insert_many(products)
    print(f"Created {len(products)} products")
    
    print("Creating sample coupons...")
    now = datetime.utcnow()
    coupons = [
        {
            "code": "WELCOME10",
            "description": "10% off your first order",
            "discount_type": "percentage",
            "discount_value": 10.0,
            "min_purchase": 50.0,
            "max_discount": 20.0,
            "valid_from": now,
            "valid_until": now + timedelta(days=30),
            "is_active": True
        },
        {
            "code": "SUMMER25",
            "description": "25% off summer sale",
            "discount_type": "percentage",
            "discount_value": 25.0,
            "min_purchase": 100.0,
            "max_discount": 50.0,
            "valid_from": now,
            "valid_until": now + timedelta(days=60),
            "is_active": True
        },
        {
            "code": "FREESHIP",
            "description": "Free shipping on orders over $75",
            "discount_type": "fixed",
            "discount_value": 5.99,
            "min_purchase": 75.0,
            "max_discount": None,
            "valid_from": now,
            "valid_until": now + timedelta(days=90),
            "is_active": True
        }
    ]
    
    await db.coupons.insert_many(coupons)
    print(f"Created {len(coupons)} coupons")
    
    print("\nDatabase seeded successfully!")
    print("\nSample credentials:")
    print("  Email: john@example.com")
    print("  Password: password123")
    print("\n  Email: jane@example.com")
    print("  Password: password123")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(seed_database())
