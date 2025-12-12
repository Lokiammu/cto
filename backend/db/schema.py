from pymongo import MongoClient, ASCENDING, DESCENDING, IndexModel
from pymongo.errors import CollectionInvalid
from backend.config import config
import sys

def create_collection_with_validator(db, collection_name, validator):
    try:
        db.create_collection(collection_name, validator=validator)
        print(f"Collection '{collection_name}' created.")
    except CollectionInvalid:
        print(f"Collection '{collection_name}' already exists. Updating validator.")
        command = {
            "collMod": collection_name,
            "validator": validator["$jsonSchema"]
        }
        try:
            db.command(command)
            print(f"Validator for '{collection_name}' updated.")
        except Exception as e:
             # Fallback if command structure is slightly different or other error
             # Note: collMod takes validator directly usually, or wrapped.
             # In pymongo `create_collection` takes `validator={...}` which usually wraps in `$jsonSchema`.
             # But `collMod` expects `validator={'$jsonSchema': ...}`.
             # The `validator` arg passed to this function is `{"$jsonSchema": ...}`
             # So we should pass `validator=validator` to collMod.
             command = {
                "collMod": collection_name,
                "validator": validator
             }
             try:
                 db.command(command)
                 print(f"Validator for '{collection_name}' updated (retry).")
             except Exception as e2:
                 print(f"Error updating validator for {collection_name}: {e2}")

def setup_schema():
    print(f"Connecting to MongoDB at {config.MONGO_URI} (DB: {config.DB_NAME})")
    client = MongoClient(config.MONGO_URI)
    db = client[config.DB_NAME]

    # 1. Users Collection
    users_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["email", "password_hash", "created_at", "updated_at"],
            "properties": {
                "email": {
                    "bsonType": "string",
                    "pattern": "^.+@.+$",
                    "description": "must be a string and match the email pattern"
                },
                "phone": {
                    "bsonType": "string",
                    "description": "must be a string"
                },
                "password_hash": {
                    "bsonType": "string",
                    "description": "must be a string"
                },
                "profile": {
                    "bsonType": "object"
                },
                "jwt_tokens": {
                    "bsonType": "array",
                    "items": {
                        "bsonType": "object",
                        "required": ["token", "created_at"],
                        "properties": {
                            "token": {"bsonType": "string"},
                            "created_at": {"bsonType": "date"},
                            "revoked": {"bsonType": "bool"}
                        }
                    }
                },
                "created_at": { "bsonType": "date" },
                "updated_at": { "bsonType": "date" }
            }
        }
    }
    create_collection_with_validator(db, "users", users_validator)
    db.users.create_index([("email", ASCENDING)], unique=True)
    db.users.create_index([("phone", ASCENDING)], unique=True, sparse=True)

    # 2. Customers Collection
    customers_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id"],
            "properties": {
                "user_id": { "bsonType": "objectId" },
                "loyalty_tier": { "bsonType": "string" },
                "points": { "bsonType": "int" },
                "preferences": { "bsonType": "object" },
                "browsing_history": { "bsonType": "array" },
                "wishlist": { "bsonType": "array" }
            }
        }
    }
    create_collection_with_validator(db, "customers", customers_validator)
    db.customers.create_index([("user_id", ASCENDING)], unique=True)

    # 3. Products Collection
    products_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["sku", "name", "price", "category"],
            "properties": {
                "sku": { "bsonType": "string" },
                "name": { "bsonType": "string" },
                "price": { "bsonType": ["double", "int", "decimal"] },
                "images": { "bsonType": "array" },
                "category": { "bsonType": "string" },
                "brand": { "bsonType": "string" },
                "colors": { "bsonType": "array" },
                "sizes": { "bsonType": "array" },
                "rating": { "bsonType": ["double", "int", "decimal"] }
            }
        }
    }
    create_collection_with_validator(db, "products", products_validator)
    db.products.create_index([("sku", ASCENDING)], unique=True)
    db.products.create_index([("category", ASCENDING)])
    db.products.create_index([("brand", ASCENDING)])

    # 4. Inventory Collection
    inventory_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["product_id", "location", "quantity_available"],
            "properties": {
                "product_id": { "bsonType": "objectId" },
                "location": { "bsonType": "string" },
                "quantity_available": { "bsonType": "int" },
                "restock_dates": { "bsonType": "array" }
            }
        }
    }
    create_collection_with_validator(db, "inventory", inventory_validator)
    db.inventory.create_index([("product_id", ASCENDING), ("location", ASCENDING)], unique=True)

    # 5. Orders Collection
    orders_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["order_number", "user_id", "items", "status", "created_at"],
            "properties": {
                "order_number": { "bsonType": "string" },
                "user_id": { "bsonType": "objectId" },
                "items": { "bsonType": "array" }, # Embedded order items for simplicity/performance or references? Ticket says "order_items" collection exists. But here it says "items" in orders. Usually normalized means linking. But MongoDB often embeds. 
                # Ticket says: "orders: ..., items, ..." AND "order_items: order_id, ...". 
                # This implies relationship. I will keep "items" in orders as a summary or array of objectIds if using separate collection, or array of objects if embedding.
                # However, ticket explicitly lists "order_items" collection.
                # I will support both or assume "items" in orders contains snapshot or references.
                # Let's assume "items" in orders is an array of sub-documents (denormalized snapshot) AND we have an order_items collection for analytics/normalized view?
                # Or maybe "items" in orders collection are just references?
                # "Schema should be normalized but denormalized where performance critical (e.g., product snapshot in order_items)"
                # This suggests order_items collection contains the snapshots.
                # So orders.items could be array of order_item_ids or just omitted if we query by order_id.
                # But typically `orders` doc has the list.
                # Let's make orders.items an array of objects which are the line items, effectively removing the need for `order_items` collection unless strict normalization is required.
                # BUT the ticket says "Create... order_items: order_id, product_id...".
                # I will create the `order_items` collection as requested. 
                # And `orders.items` will be an array of documents (snapshot) to satisfy "denormalized where performance critical".
                "status": { "bsonType": "string" },
                "fulfillment": { "bsonType": "object" },
                "tracking": { "bsonType": "object" },
                "created_at": { "bsonType": "date" }
            }
        }
    }
    create_collection_with_validator(db, "orders", orders_validator)
    db.orders.create_index([("order_number", ASCENDING)], unique=True)
    db.orders.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])

    # 6. Order Items Collection
    order_items_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["order_id", "product_id", "quantity", "unit_price"],
            "properties": {
                "order_id": { "bsonType": "objectId" },
                "product_id": { "bsonType": "objectId" },
                "quantity": { "bsonType": "int" },
                "unit_price": { "bsonType": ["double", "int", "decimal"] },
                "color": { "bsonType": "string" },
                "size": { "bsonType": "string" }
            }
        }
    }
    create_collection_with_validator(db, "order_items", order_items_validator)
    db.order_items.create_index([("order_id", ASCENDING)])
    db.order_items.create_index([("product_id", ASCENDING)])

    # 7. Cart Collection
    cart_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "items"],
            "properties": {
                "user_id": { "bsonType": "objectId" },
                "items": { "bsonType": "array" },
                "subtotal": { "bsonType": ["double", "int", "decimal"] },
                "tax": { "bsonType": ["double", "int", "decimal"] },
                "loyalty_discount": { "bsonType": ["double", "int", "decimal"] },
                "expiration": { "bsonType": "date" }
            }
        }
    }
    create_collection_with_validator(db, "cart", cart_validator)
    db.cart.create_index([("user_id", ASCENDING)], unique=True)

    # 8. Loyalty Programs Collection
    loyalty_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["tier_name"],
            "properties": {
                "tier_name": { "bsonType": "string" }, # silver, gold, platinum
                "benefits": { "bsonType": "array" },
                "point_rules": { "bsonType": "object" }
            }
        }
    }
    create_collection_with_validator(db, "loyalty_programs", loyalty_validator)
    db.loyalty_programs.create_index([("tier_name", ASCENDING)], unique=True)

    # 9. Promotions Collection
    promotions_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["code", "discount_percentage", "valid_from", "valid_until"],
            "properties": {
                "code": { "bsonType": "string" },
                "discount_percentage": { "bsonType": ["double", "int", "decimal"] },
                "applicable_to": { "bsonType": "object" },
                "valid_from": { "bsonType": "date" },
                "valid_until": { "bsonType": "date" },
                "loyalty_tier_required": { "bsonType": "string" }
            }
        }
    }
    create_collection_with_validator(db, "promotions", promotions_validator)
    db.promotions.create_index([("code", ASCENDING)], unique=True)

    # 10. Channel Sessions Collection
    sessions_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["session_id", "expires_at"],
            "properties": {
                "user_id": { "bsonType": ["objectId", "null"] },
                "session_id": { "bsonType": "string" },
                "conversation_state": { "bsonType": "object" },
                "context": { "bsonType": "object" },
                "expires_at": { "bsonType": "date" }
            }
        }
    }
    create_collection_with_validator(db, "channel_sessions", sessions_validator)
    db.channel_sessions.create_index([("session_id", ASCENDING)], unique=True)
    db.channel_sessions.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0) # TTL Index
    db.channel_sessions.create_index([("user_id", ASCENDING), ("last_activity", DESCENDING)])


    # 11. Conversation Logs Collection
    logs_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["session_id", "messages"],
            "properties": {
                "session_id": { "bsonType": "string" },
                "messages": { "bsonType": "array" },
                "tool_calls": { "bsonType": "array" },
                "timestamps": { "bsonType": "array" }
            }
        }
    }
    create_collection_with_validator(db, "conversation_logs", logs_validator)
    db.conversation_logs.create_index([("session_id", ASCENDING)])

    print("Schema setup complete.")

if __name__ == "__main__":
    try:
        setup_schema()
    except Exception as e:
        print(f"Error setting up schema: {e}")
        sys.exit(1)
