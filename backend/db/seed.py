import random
from datetime import datetime, timedelta
from pymongo import MongoClient
from faker import Faker
import bcrypt
from backend.config import config
import sys

fake = Faker('en_IN') # Using Indian locale as currency mentioned is INR

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=config.BCRYPT_COST)).decode('utf-8')

def seed_data():
    print(f"Connecting to MongoDB at {config.MONGO_URI} (DB: {config.DB_NAME})")
    client = MongoClient(config.MONGO_URI)
    db = client[config.DB_NAME]

    # Clear existing data
    print("Clearing existing data...")
    db.users.delete_many({})
    db.customers.delete_many({})
    db.products.delete_many({})
    db.inventory.delete_many({})
    db.orders.delete_many({})
    db.order_items.delete_many({})
    db.cart.delete_many({})
    db.loyalty_programs.delete_many({})
    db.promotions.delete_many({})
    db.channel_sessions.delete_many({})
    db.conversation_logs.delete_many({})

    # 1. Loyalty Programs
    print("Seeding Loyalty Programs...")
    loyalty_programs = [
        {
            "tier_name": "silver",
            "benefits": ["1 point per 100 INR", "Birthday discount 5%"],
            "point_rules": {"spend_conversion": 0.01}
        },
        {
            "tier_name": "gold",
            "benefits": ["1.5 points per 100 INR", "Birthday discount 10%", "Free shipping"],
            "point_rules": {"spend_conversion": 0.015}
        },
        {
            "tier_name": "platinum",
            "benefits": ["2 points per 100 INR", "Birthday discount 15%", "Free shipping", "Priority support"],
            "point_rules": {"spend_conversion": 0.02}
        }
    ]
    db.loyalty_programs.insert_many(loyalty_programs)

    # 2. Products
    print("Seeding Products...")
    categories = ["Clothing", "Shoes", "Accessories"]
    brands = ["Nike", "Adidas", "Puma", "Zara", "H&M", "FabIndia", "Manyavar"]
    products = []
    
    for _ in range(40):
        category = random.choice(categories)
        brand = random.choice(brands)
        name = f"{brand} {fake.color_name()} {category} {fake.word()}"
        price = random.randint(500, 15000)
        
        product = {
            "sku": fake.unique.ean13(),
            "name": name,
            "price": price,
            "images": [fake.image_url(), fake.image_url()],
            "category": category,
            "brand": brand,
            "colors": [fake.color_name(), fake.color_name()],
            "sizes": ["S", "M", "L", "XL"] if category == "Clothing" else ["6", "7", "8", "9", "10"],
            "rating": round(random.uniform(3.0, 5.0), 1)
        }
        products.append(product)
    
    result_products = db.products.insert_many(products)
    product_ids = result_products.inserted_ids

    # 3. Inventory
    print("Seeding Inventory...")
    locations = ["Warehouse", "Store A", "Store B", "Store C"]
    inventory_items = []
    
    for p_id in product_ids:
        for loc in locations:
            inventory_items.append({
                "product_id": p_id,
                "location": loc,
                "quantity_available": random.randint(0, 100),
                "restock_dates": [datetime.now() + timedelta(days=random.randint(5, 30))]
            })
    db.inventory.insert_many(inventory_items)

    # 4. Promotions
    print("Seeding Promotions...")
    promotions = [
        {
            "code": "WELCOME10",
            "discount_percentage": 10,
            "applicable_to": {"all": True},
            "valid_from": datetime.now() - timedelta(days=30),
            "valid_until": datetime.now() + timedelta(days=365),
            "loyalty_tier_required": "silver"
        },
        {
            "code": "SUMMER20",
            "discount_percentage": 20,
            "applicable_to": {"category": "Clothing"},
            "valid_from": datetime.now() - timedelta(days=10),
            "valid_until": datetime.now() + timedelta(days=60),
            "loyalty_tier_required": "silver"
        },
        {
            "code": "GOLDVIP",
            "discount_percentage": 25,
            "applicable_to": {"all": True},
            "valid_from": datetime.now() - timedelta(days=30),
            "valid_until": datetime.now() + timedelta(days=365),
            "loyalty_tier_required": "gold"
        },
         {
            "code": "FESTIVE30",
            "discount_percentage": 30,
            "applicable_to": {"brand": "FabIndia"},
            "valid_from": datetime.now() - timedelta(days=5),
            "valid_until": datetime.now() + timedelta(days=15),
            "loyalty_tier_required": "silver"
        }
    ]
    db.promotions.insert_many(promotions)

    # 5. Users and Customers
    print("Seeding Users and Customers...")
    users = []
    customers = []
    
    # Create a specific user for testing
    test_password = "password123"
    test_email = "test@example.com"
    test_user = {
        "email": test_email,
        "phone": fake.phone_number(),
        "password_hash": hash_password(test_password),
        "profile": {
            "first_name": "Test",
            "last_name": "User",
            "address": fake.address()
        },
        "jwt_tokens": [],
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    users.append(test_user)

    for _ in range(15):
        email = fake.unique.email()
        password = "password123"
        user = {
            "email": email,
            "phone": fake.phone_number(),
            "password_hash": hash_password(password),
            "profile": {
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "address": fake.address()
            },
            "jwt_tokens": [],
            "created_at": datetime.now() - timedelta(days=random.randint(1, 700)),
            "updated_at": datetime.now()
        }
        users.append(user)
    
    result_users = db.users.insert_many(users)
    user_ids = result_users.inserted_ids

    for i, u_id in enumerate(user_ids):
        # assign loyalty tier
        tier = random.choice(["silver", "silver", "silver", "gold", "gold", "platinum"])
        
        customer = {
            "user_id": u_id,
            "loyalty_tier": tier,
            "points": random.randint(0, 5000),
            "preferences": {
                "favorite_categories": random.choices(categories, k=2),
                "newsletter": random.choice([True, False])
            },
            "browsing_history": [], # Populate if needed
            "wishlist": [] # Populate if needed
        }
        customers.append(customer)
    
    db.customers.insert_many(customers)

    # 6. Orders and Order Items
    print("Seeding Orders...")
    
    # Get products list from db to have IDs
    all_products = list(db.products.find())
    
    for u_id in user_ids:
        # 3-15 orders per customer
        num_orders = random.randint(3, 15)
        for _ in range(num_orders):
            order_items_list = []
            num_items = random.randint(1, 5)
            order_total = 0
            
            # Select random products
            selected_products = random.choices(all_products, k=num_items)
            
            created_at = datetime.now() - timedelta(days=random.randint(1, 365))
            order_number = fake.unique.bothify(text='ORD-####-####')
            order_id = None # Will assign after inserting order? No, usually create order first?
            # Or use ObjectId.
            
            # We construct the order object
            # items in orders collection
            
            for prod in selected_products:
                qty = random.randint(1, 3)
                price = prod['price']
                item_total = price * qty
                order_total += item_total
                
                item = {
                    "product_id": prod['_id'],
                    "quantity": qty,
                    "unit_price": price,
                    "color": random.choice(prod['colors']),
                    "size": random.choice(prod['sizes'])
                }
                order_items_list.append(item)
            
            order = {
                "order_number": order_number,
                "user_id": u_id,
                "items": order_items_list,
                "status": random.choice(["Delivered", "Delivered", "Delivered", "Shipped", "Processing", "Cancelled"]),
                "fulfillment": {
                    "courier": random.choice(["FedEx", "DHL", "BlueDart"]),
                    "tracking_number": fake.bothify(text='TRK##########')
                },
                "tracking": {},
                "created_at": created_at
            }
            
            res_order = db.orders.insert_one(order)
            order_id = res_order.inserted_id
            
            # Insert into order_items collection
            for item in order_items_list:
                db_item = item.copy()
                db_item["order_id"] = order_id
                db.order_items.insert_one(db_item)

    print("Seeding complete.")

if __name__ == "__main__":
    seed_data()
