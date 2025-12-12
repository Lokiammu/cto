"""
MongoDB Database Operations for Sales Agent Tools

This module provides async MongoDB operations for all the sales agent tools.
All functions follow a consistent pattern with proper error handling and logging.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import motor.motor_asyncio

# Configure logging
logger = logging.getLogger(__name__)

# MongoDB client - will be initialized in the app startup
db_client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
db: Optional[motor.motor_asyncio.AsyncIOMotorDatabase] = None


async def initialize_database():
    """Initialize MongoDB connection"""
    global db_client, db
    
    try:
        mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGODB_DB_NAME", "sales_agent_db")
        
        db_client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
        db = db_client[db_name]
        
        # Test connection
        await db.admin.command('ping')
        logger.info(f"Connected to MongoDB: {db_name}")
        
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        raise


async def close_database():
    """Close MongoDB connection"""
    global db_client
    if db_client:
        db_client.close()
        logger.info("MongoDB connection closed")


# Tool Functions for Customer Management

async def fetch_customer_profile(user_id: str) -> Dict[str, Any]:
    """Fetch customer profile from database"""
    try:
        customer = await db.customers.find_one({"user_id": user_id})
        if customer:
            customer["_id"] = str(customer["_id"])  # Convert ObjectId to string
        return customer or {}
    except Exception as e:
        logger.error(f"Error fetching customer {user_id}: {str(e)}")
        return {}


async def update_customer_context(user_id: str, context_data: Dict[str, Any]) -> bool:
    """Update customer context with new information"""
    try:
        update_data = {
            **context_data,
            "updated_at": datetime.now()
        }
        result = await db.customers.update_one(
            {"user_id": user_id},
            {"$set": update_data},
            upsert=True
        )
        return result.acknowledged
    except Exception as e:
        logger.error(f"Error updating customer context for {user_id}: {str(e)}")
        return False


async def fetch_customer_preferences(user_id: str) -> Dict[str, Any]:
    """Fetch customer preferences for recommendations"""
    try:
        customer = await fetch_customer_profile(user_id)
        return {
            "preferences": customer.get("preferences", {}),
            "past_purchases": customer.get("past_purchases", []),
            "browsing_history": customer.get("browsing_history", []),
            "loyalty_tier": customer.get("loyalty_tier", "bronze"),
            "loyalty_points": customer.get("loyalty_points", 0)
        }
    except Exception as e:
        logger.error(f"Error fetching preferences for {user_id}: {str(e)}")
        return {}


# Tool Functions for Product Management

async def fetch_products(filters: Dict[str, Any] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch products based on filters"""
    try:
        query = filters or {}
        
        # Add active status filter
        if "status" not in query:
            query["status"] = "active"
        
        cursor = db.products.find(query).limit(limit)
        products = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string
        for product in products:
            product["_id"] = str(product["_id"])
        
        return products
    except Exception as e:
        logger.error(f"Error fetching products: {str(e)}")
        return []


async def fetch_product_by_id(product_id: str) -> Dict[str, Any]:
    """Fetch single product by ID"""
    try:
        product = await db.products.find_one({"product_id": product_id})
        if product:
            product["_id"] = str(product["_id"])
        return product or {}
    except Exception as e:
        logger.error(f"Error fetching product {product_id}: {str(e)}")
        return {}


async def search_products(query_text: str, category: str = None, limit: int = 10) -> List[Dict[str, Any]]:
    """Search products by text query"""
    try:
        search_query = {
            "$or": [
                {"name": {"$regex": query_text, "$options": "i"}},
                {"description": {"$regex": query_text, "$options": "i"}},
                {"tags": {"$regex": query_text, "$options": "i"}}
            ],
            "status": "active"
        }
        
        if category:
            search_query["category"] = category
        
        cursor = db.products.find(search_query).limit(limit)
        products = await cursor.to_list(length=limit)
        
        for product in products:
            product["_id"] = str(product["_id"])
        
        return products
    except Exception as e:
        logger.error(f"Error searching products: {str(e)}")
        return []


# Tool Functions for Inventory Management

async def check_stock(product_id: str, location: Dict[str, float] = None) -> Dict[str, Any]:
    """Check inventory stock for a product"""
    try:
        inventory = await db.inventory.find_one({"product_id": product_id})
        if not inventory:
            return {"available_quantity": 0, "fulfillment_options": []}
        
        inventory["_id"] = str(inventory["_id"])
        
        # Calculate fulfillment options based on stock levels
        fulfillment_options = []
        
        if inventory.get("warehouse_stock", 0) > 0:
            fulfillment_options.append({
                "type": "home_delivery",
                "timeline": "2-3 business days",
                "cost": 5.99,
                "available": True
            })
        
        if inventory.get("store_stock", 0) > 0:
            fulfillment_options.append({
                "type": "store_pickup",
                "timeline": "Same day",
                "cost": 0.00,
                "available": True
            })
        
        return {
            "available_quantity": inventory.get("warehouse_stock", 0) + inventory.get("store_stock", 0),
            "fulfillment_options": fulfillment_options,
            "warehouse_stock": inventory.get("warehouse_stock", 0),
            "store_stock": inventory.get("store_stock", 0),
            "last_updated": inventory.get("updated_at", datetime.now())
        }
        
    except Exception as e:
        logger.error(f"Error checking stock for {product_id}: {str(e)}")
        return {"available_quantity": 0, "fulfillment_options": []}


async def find_nearby_stores(product_id: str, customer_location: Dict[str, float], radius: float = 50.0) -> List[Dict[str, Any]]:
    """Find nearby stores with product availability"""
    try:
        if not customer_location:
            return []
        
        # Using MongoDB's geospatial query capabilities
        stores_cursor = db.stores.find({
            "location": {
                "$near": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [customer_location["lng"], customer_location["lat"]]
                    },
                    "$maxDistance": radius * 1000  # Convert km to meters
                }
            }
        })
        
        nearby_stores = await stores_cursor.to_list(length=10)
        
        # Filter stores that have the product in stock
        available_stores = []
        for store in nearby_stores:
            store["_id"] = str(store["_id"])
            
            # Check if this store has the product
            store_inventory = await db.store_inventory.find_one({
                "store_id": store["store_id"],
                "product_id": product_id
            })
            
            if store_inventory and store_inventory.get("quantity", 0) > 0:
                store_inventory["_id"] = str(store_inventory["_id"])
                available_stores.append({
                    "store": store,
                    "stock": store_inventory["quantity"],
                    "distance_km": store.get("distance_km", 0)
                })
        
        return available_stores
        
    except Exception as e:
        logger.error(f"Error finding nearby stores: {str(e)}")
        return []


async def estimate_delivery(customer_location: Dict[str, float], product_id: str) -> Dict[str, Any]:
    """Estimate delivery options and timing"""
    try:
        # Check if we have inventory for delivery
        inventory = await check_stock(product_id)
        
        if inventory["available_quantity"] == 0:
            return {"delivery_available": False, "reason": "Out of stock"}
        
        # Calculate delivery time based on location
        delivery_options = []
        
        if inventory.get("warehouse_stock", 0) > 0:
            # Standard delivery
            delivery_options.append({
                "method": "Standard Shipping",
                "timeline": "2-3 business days",
                "cost": 5.99,
                "available": True
            })
            
            # Express delivery if customer is in major city
            if _is_major_city(customer_location):
                delivery_options.append({
                    "method": "Express Shipping", 
                    "timeline": "Next business day",
                    "cost": 12.99,
                    "available": True
                })
        
        # Pickup option if nearby stores have stock
        nearby_stores = await find_nearby_stores(product_id, customer_location)
        if nearby_stores:
            delivery_options.append({
                "method": "Store Pickup",
                "timeline": "Same day",
                "cost": 0.00,
                "available": True,
                "nearest_store": nearby_stores[0]["store"]["name"] if nearby_stores else None
            })
        
        return {
            "delivery_available": True,
            "options": delivery_options,
            "estimated_days": 2 if delivery_options else None
        }
        
    except Exception as e:
        logger.error(f"Error estimating delivery: {str(e)}")
        return {"delivery_available": False, "reason": "Error calculating delivery"}


def _is_major_city(location: Dict[str, float]) -> bool:
    """Simple heuristic to check if location is a major city"""
    if not location:
        return False
    
    lat, lng = location["lat"], location["lng"]
    
    # Rough bounding boxes for major cities (could be more sophisticated)
    major_cities = [
        {"name": "New York", "lat": 40.7128, "lng": -74.0060, "radius": 0.5},
        {"name": "Los Angeles", "lat": 34.0522, "lng": -118.2437, "radius": 0.5},
        {"name": "Chicago", "lat": 41.8781, "lng": -87.6298, "radius": 0.5},
        {"name": "San Francisco", "lat": 37.7749, "lng": -122.4194, "radius": 0.3},
        {"name": "Miami", "lat": 25.7617, "lng": -80.1918, "radius": 0.3},
    ]
    
    for city in major_cities:
        import math
        distance = math.sqrt((lat - city["lat"])**2 + (lng - city["lng"])**2)
        if distance < city["radius"]:
            return True
    
    return False


# Tool Functions for Cart Management

async def add_to_cart(user_id: str, product_id: str, quantity: int, color: str = None, size: str = None) -> bool:
    """Add item to user's cart"""
    try:
        # Fetch product details
        product = await fetch_product_by_id(product_id)
        if not product:
            logger.error(f"Product {product_id} not found")
            return False
        
        # Check if item already exists in cart
        cart_item = await db.carts.find_one({
            "user_id": user_id,
            "product_id": product_id,
            "color": color,
            "size": size
        })
        
        if cart_item:
            # Update quantity
            await db.carts.update_one(
                {"_id": cart_item["_id"]},
                {"$inc": {"quantity": quantity}}
            )
        else:
            # Add new item
            cart_document = {
                "user_id": user_id,
                "product_id": product_id,
                "quantity": quantity,
                "color": color,
                "size": size,
                "price": product.get("price", 0.0),
                "added_at": datetime.now()
            }
            await db.carts.insert_one(cart_document)
        
        return True
        
    except Exception as e:
        logger.error(f"Error adding to cart for {user_id}: {str(e)}")
        return False


async def get_cart(user_id: str) -> List[Dict[str, Any]]:
    """Get user's cart items"""
    try:
        cursor = db.carts.find({"user_id": user_id})
        cart_items = await cursor.to_list(length=None)
        
        # Fetch product details for each cart item
        enriched_cart = []
        for item in cart_items:
            item["_id"] = str(item["_id"])
            product = await fetch_product_by_id(item["product_id"])
            item["product_details"] = product
            enriched_cart.append(item)
        
        return enriched_cart
        
    except Exception as e:
        logger.error(f"Error fetching cart for {user_id}: {str(e)}")
        return []


async def update_cart_item(user_id: str, product_id: str, quantity: int, color: str = None, size: str = None) -> bool:
    """Update cart item quantity"""
    try:
        if quantity <= 0:
            # Remove item if quantity is 0 or negative
            await db.carts.delete_one({
                "user_id": user_id,
                "product_id": product_id,
                "color": color,
                "size": size
            })
        else:
            # Update quantity
            await db.carts.update_one(
                {
                    "user_id": user_id,
                    "product_id": product_id,
                    "color": color,
                    "size": size
                },
                {"$set": {"quantity": quantity}}
            )
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating cart item: {str(e)}")
        return False


async def clear_cart(user_id: str) -> bool:
    """Clear user's entire cart"""
    try:
        await db.carts.delete_many({"user_id": user_id})
        return True
    except Exception as e:
        logger.error(f"Error clearing cart for {user_id}: {str(e)}")
        return False


async def calculate_cart_total(user_id: str) -> Dict[str, Any]:
    """Calculate cart total with taxes and discounts"""
    try:
        cart_items = await get_cart(user_id)
        
        subtotal = 0.0
        for item in cart_items:
            item_total = item["quantity"] * item.get("price", 0.0)
            subtotal += item_total
        
        tax = subtotal * 0.08  # 8% tax rate
        total = subtotal + tax
        
        return {
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
            "item_count": len(cart_items),
            "total_quantity": sum(item["quantity"] for item in cart_items)
        }
        
    except Exception as e:
        logger.error(f"Error calculating cart total: {str(e)}")
        return {"subtotal": 0.0, "tax": 0.0, "total": 0.0, "item_count": 0}


# Tool Functions for Loyalty Program

async def get_loyalty_profile(user_id: str) -> Dict[str, Any]:
    """Get customer loyalty program status"""
    try:
        customer = await fetch_customer_profile(user_id)
        if not customer:
            return {
                "user_id": user_id,
                "current_tier": "bronze",
                "points_balance": 0,
                "total_spent": 0.0
            }
        
        return {
            "user_id": user_id,
            "current_tier": customer.get("loyalty_tier", "bronze"),
            "points_balance": customer.get("loyalty_points", 0),
            "total_spent": customer.get("total_spent", 0.0),
            "join_date": customer.get("join_date", datetime.now()),
            "last_purchase": customer.get("last_purchase")
        }
        
    except Exception as e:
        logger.error(f"Error fetching loyalty profile for {user_id}: {str(e)}")
        return {"user_id": user_id, "current_tier": "bronze", "points_balance": 0}


async def apply_loyalty_discount(user_id: str, discount_amount: float) -> Dict[str, Any]:
    """Apply loyalty discount and update customer status"""
    try:
        customer = await fetch_customer_profile(user_id)
        if not customer:
            return {"success": False, "reason": "Customer not found"}
        
        # Calculate new points balance
        current_points = customer.get("loyalty_points", 0)
        new_points = max(0, current_points - int(discount_amount * 10))  # 10 points per $1 discount
        
        # Update customer
        await db.customers.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "loyalty_points": new_points,
                    "updated_at": datetime.now()
                }
            }
        )
        
        return {
            "success": True,
            "discount_applied": discount_amount,
            "points_deducted": int(discount_amount * 10),
            "new_points_balance": new_points
        }
        
    except Exception as e:
        logger.error(f"Error applying loyalty discount: {str(e)}")
        return {"success": False, "reason": str(e)}


async def earn_loyalty_points(user_id: str, purchase_amount: float) -> Dict[str, Any]:
    """Add loyalty points based on purchase amount"""
    try:
        customer = await fetch_customer_profile(user_id)
        if not customer:
            return {"success": False, "reason": "Customer not found"}
        
        # Calculate points earned (1 point per $1 spent)
        points_earned = int(purchase_amount)
        tier_multiplier = {
            "bronze": 1.0,
            "silver": 1.25,
            "gold": 1.5,
            "platinum": 2.0
        }
        
        multiplier = tier_multiplier.get(customer.get("loyalty_tier", "bronze"), 1.0)
        total_points_earned = int(points_earned * multiplier)
        
        current_points = customer.get("loyalty_points", 0)
        new_points = current_points + total_points_earned
        
        # Check for tier upgrade
        tiers = ["bronze", "silver", "gold", "platinum"]
        current_tier = customer.get("loyalty_tier", "bronze")
        current_tier_index = tiers.index(current_tier)
        
        new_tier = current_tier
        total_spent = customer.get("total_spent", 0.0) + purchase_amount
        
        # Simple tier progression logic
        if current_tier == "bronze" and total_spent >= 500:
            new_tier = "silver"
        elif current_tier == "silver" and total_spent >= 1500:
            new_tier = "gold"
        elif current_tier == "gold" and total_spent >= 3000:
            new_tier = "platinum"
        
        # Update customer
        await db.customers.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "loyalty_points": new_points,
                    "loyalty_tier": new_tier,
                    "total_spent": total_spent,
                    "last_purchase": datetime.now(),
                    "updated_at": datetime.now()
                }
            }
        )
        
        return {
            "success": True,
            "points_earned": total_points_earned,
            "tier_multiplier": multiplier,
            "new_points_balance": new_points,
            "tier_upgrade": new_tier != current_tier,
            "new_tier": new_tier
        }
        
    except Exception as e:
        logger.error(f"Error earning loyalty points: {str(e)}")
        return {"success": False, "reason": str(e)}


async def get_available_coupons(user_id: str) -> List[Dict[str, Any]]:
    """Get available coupons for customer"""
    try:
        customer = await fetch_customer_profile(user_id)
        if not customer:
            return []
        
        tier = customer.get("loyalty_tier", "bronze")
        
        # Define tier-based coupons
        tier_coupons = {
            "bronze": [
                {"code": "WELCOME10", "discount": 0.10, "description": "10% off first order"},
                {"code": "SAVE5", "discount": 5.00, "description": "$5 off orders over $50"}
            ],
            "silver": [
                {"code": "SILVER15", "discount": 0.15, "description": "15% off orders over $100"},
                {"code": "FREESHIP", "discount": 5.99, "description": "Free shipping"}
            ],
            "gold": [
                {"code": "GOLD20", "discount": 0.20, "description": "20% off orders over $150"},
                {"code": "EXCLUSIVE25", "discount": 25.00, "description": "$25 off orders over $200"}
            ],
            "platinum": [
                {"code": "VIP30", "discount": 0.30, "description": "30% off any order"},
                {"code": "PLATINUM50", "discount": 50.00, "description": "$50 off orders over $300"}
            ]
        }
        
        return tier_coupons.get(tier, [])
        
    except Exception as e:
        logger.error(f"Error fetching available coupons: {str(e)}")
        return []


# Tool Functions for Promotions

async def get_active_promotions() -> List[Dict[str, Any]]:
    """Get currently active promotions"""
    try:
        now = datetime.now()
        cursor = db.promotions.find({
            "start_date": {"$lte": now},
            "end_date": {"$gte": now},
            "is_active": True
        })
        
        promotions = await cursor.to_list(length=10)
        
        for promo in promotions:
            promo["_id"] = str(promo["_id"])
        
        return promotions
        
    except Exception as e:
        logger.error(f"Error fetching active promotions: {str(e)}")
        return []


# Tool Functions for Conversation Persistence

async def save_conversation_log(session_id: str, user_id: str, messages: List[Dict[str, Any]], metadata: Dict[str, Any] = None) -> bool:
    """Save conversation to database"""
    try:
        conversation_doc = {
            "session_id": session_id,
            "user_id": user_id,
            "messages": messages,
            "metadata": metadata or {},
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        await db.conversation_logs.insert_one(conversation_doc)
        return True
        
    except Exception as e:
        logger.error(f"Error saving conversation log: {str(e)}")
        return False


async def fetch_conversation_history(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch recent conversation history for user"""
    try:
        cursor = db.conversation_logs.find({"user_id": user_id}).sort("updated_at", -1).limit(limit)
        conversations = await cursor.to_list(length=limit)
        
        for conv in conversations:
            conv["_id"] = str(conv["_id"])
        
        return conversations
        
    except Exception as e:
        logger.error(f"Error fetching conversation history: {str(e)}")
        return []


async def update_channel_session(session_id: str, state_data: Dict[str, Any]) -> bool:
    """Update active channel session state"""
    try:
        await db.channel_sessions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    **state_data,
                    "updated_at": datetime.now()
                }
            },
            upsert=True
        )
        return True
        
    except Exception as e:
        logger.error(f"Error updating channel session: {str(e)}")
        return False


async def get_channel_session(session_id: str) -> Dict[str, Any]:
    """Get active channel session"""
    try:
        session = await db.channel_sessions.find_one({"session_id": session_id})
        if session:
            session["_id"] = str(session["_id"])
        return session or {}
        
    except Exception as e:
        logger.error(f"Error fetching channel session: {str(e)}")
        return {}