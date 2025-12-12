import logging
import random
from datetime import datetime
from backend.database import get_database

logger = logging.getLogger(__name__)


async def sync_inventory():
    """
    Sync inventory from external source (mock implementation)
    In production, this would call external inventory management system
    """
    try:
        db = get_database()
        
        # Get all products
        cursor = db.products.find({})
        products = await cursor.to_list(length=1000)
        
        updated_count = 0
        for product in products:
            # Simulate random stock changes (mock)
            # In production, fetch real stock from external system
            current_stock = product.get("stock", 0)
            
            # Randomly update some products
            if random.random() < 0.1:  # 10% chance of update
                # Simulate stock change (-5 to +10)
                stock_change = random.randint(-5, 10)
                new_stock = max(0, current_stock + stock_change)
                
                await db.products.update_one(
                    {"_id": product["_id"]},
                    {
                        "$set": {
                            "stock": new_stock,
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
                updated_count += 1
        
        logger.info(f"Inventory sync completed: {updated_count} products updated")
    except Exception as e:
        logger.error(f"Error syncing inventory: {e}")


async def check_low_stock_alerts():
    """
    Check for low stock products and send alerts
    """
    try:
        db = get_database()
        
        # Find products with low stock (< 10)
        cursor = db.products.find({"stock": {"$lt": 10, "$gt": 0}})
        low_stock_products = await cursor.to_list(length=100)
        
        if low_stock_products:
            logger.warning(f"Low stock alert: {len(low_stock_products)} products below threshold")
            # In production, send email/notification to inventory manager
        
    except Exception as e:
        logger.error(f"Error checking low stock: {e}")
