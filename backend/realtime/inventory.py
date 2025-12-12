import asyncio
import logging
from datetime import datetime
from backend.database import get_database
from backend.websocket.manager import connection_manager

logger = logging.getLogger(__name__)


class InventoryChangeListener:
    """Listen for inventory changes using MongoDB Change Streams"""
    
    def __init__(self):
        self.running = False
        self.task = None
    
    async def start(self):
        """Start listening for inventory changes"""
        if self.running:
            logger.warning("Inventory listener already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._listen())
        logger.info("Inventory change listener started")
    
    async def stop(self):
        """Stop listening for inventory changes"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Inventory change listener stopped")
    
    async def _listen(self):
        """Listen for changes in products collection"""
        try:
            db = get_database()
            
            # Watch for updates to stock field in products collection
            pipeline = [
                {
                    "$match": {
                        "operationType": {"$in": ["update", "replace"]},
                        "updateDescription.updatedFields.stock": {"$exists": True}
                    }
                }
            ]
            
            async with db.products.watch(pipeline) as change_stream:
                logger.info("Watching products collection for inventory changes")
                
                async for change in change_stream:
                    if not self.running:
                        break
                    
                    try:
                        await self._handle_change(change)
                    except Exception as e:
                        logger.error(f"Error handling inventory change: {e}")
        
        except Exception as e:
            logger.error(f"Inventory change listener error: {e}")
            if self.running:
                # Restart listener after a delay
                await asyncio.sleep(5)
                if self.running:
                    logger.info("Restarting inventory change listener")
                    self.task = asyncio.create_task(self._listen())
    
    async def _handle_change(self, change):
        """Handle inventory change event"""
        try:
            product_id = str(change["documentKey"]["_id"])
            updated_fields = change.get("updateDescription", {}).get("updatedFields", {})
            
            new_quantity = updated_fields.get("stock")
            
            if new_quantity is not None:
                # Broadcast update to all connected WebSocket clients
                message = {
                    "type": "inventory_update",
                    "product_id": product_id,
                    "new_quantity": new_quantity,
                    "location": "warehouse",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                await connection_manager.broadcast(message)
                logger.info(f"Broadcast inventory update: product={product_id}, stock={new_quantity}")
        
        except Exception as e:
            logger.error(f"Error processing inventory change: {e}")


# Global inventory listener instance
inventory_listener = InventoryChangeListener()


async def start_inventory_listener():
    """Start the inventory change listener"""
    await inventory_listener.start()


async def stop_inventory_listener():
    """Stop the inventory change listener"""
    await inventory_listener.stop()
