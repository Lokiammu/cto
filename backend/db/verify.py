from pymongo import MongoClient
from backend.config import config
import sys

def verify_db():
    print(f"Connecting to MongoDB at {config.MONGO_URI} (DB: {config.DB_NAME})")
    client = MongoClient(config.MONGO_URI)
    db = client[config.DB_NAME]

    collections = db.list_collection_names()
    print(f"Collections found: {len(collections)}")
    for col_name in sorted(collections):
        count = db[col_name].count_documents({})
        indexes = list(db[col_name].list_indexes())
        print(f"- {col_name}: {count} documents, {len(indexes)} indexes")
        for idx in indexes:
            print(f"  - Index: {idx['name']} -> {idx['key']}")
            
    required_collections = [
        "users", "customers", "products", "inventory", "orders", "order_items",
        "cart", "loyalty_programs", "promotions", "channel_sessions", "conversation_logs"
    ]
    
    missing = [c for c in required_collections if c not in collections]
    if missing:
        print(f"MISSING COLLECTIONS: {missing}")
        sys.exit(1)
    else:
        print("All required collections present.")

if __name__ == "__main__":
    verify_db()
