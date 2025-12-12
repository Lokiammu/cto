"""
Inventory Agent

This agent specializes in checking product availability, managing inventory queries,
and providing fulfillment options (delivery, pickup) based on customer location.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .state import ConversationState, InventoryStatus
from .utils import log_agent_execution, format_fulfillment_options, estimate_delivery_time
from ..llm.mistral_client import get_mistral_client
from ..tools.database_tools import (
    fetch_product_by_id, check_stock, find_nearby_stores, 
    estimate_delivery
)

# Configure logging
logger = logging.getLogger(__name__)


class InventoryAgent:
    """
    Inventory and fulfillment specialist agent.
    
    This agent checks product availability, determines best fulfillment options,
    and provides delivery estimates based on customer location and preferences.
    """
    
    def __init__(self):
        self.mistral_client = None
    
    async def initialize(self):
        """Initialize the inventory agent"""
        self.mistral_client = get_mistral_client()
    
    @log_agent_execution("InventoryAgent.process")
    async def process(self, state: ConversationState) -> Dict[str, Any]:
        """Main processing function for the inventory agent"""
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting inventory check for user: {state.user_id}")
            
            # Step 1: Extract product information from user message
            product_info = await self._extract_product_info(state)
            
            if not product_info.get("product_id"):
                return await self._handle_missing_product_info(state, start_time)
            
            # Step 2: Check inventory status
            inventory_status = await self._check_inventory_status(product_info, state)
            
            # Step 3: Get fulfillment options
            fulfillment_options = await self._get_fulfillment_options(product_info, state, inventory_status)
            
            # Step 4: Generate response using Mistral for natural language
            response = await self._generate_inventory_response(
                product_info, inventory_status, fulfillment_options, state
            )
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Inventory check completed in {processing_time:.2f}s")
            
            return {
                "content": response,
                "data": {
                    "product_info": product_info,
                    "inventory_status": inventory_status.dict(),
                    "fulfillment_options": fulfillment_options,
                    "customer_location": state.customer_context.location if state.customer_context else None
                },
                "confidence": self._calculate_confidence(inventory_status),
                "processing_time": processing_time
            }
            
        except Exception as e:
            logger.error(f"Error in inventory process: {str(e)}")
            return {
                "content": "I'm having trouble checking product availability right now. Please try again or contact support.",
                "data": {"error": str(e)},
                "confidence": 0.1,
                "processing_time": (datetime.now() - start_time).total_seconds()
            }
    
    async def _extract_product_info(self, state: ConversationState) -> Dict[str, Any]:
        """Extract product information from user message and state"""
        product_info = {
            "product_id": None,
            "product_name": None,
            "requested_quantity": 1
        }
        
        try:
            # Look for product information in recent messages
            latest_message = None
            for msg in reversed(state.messages):
                if msg.role == "user":
                    latest_message = msg.content
                    break
            
            if not latest_message:
                return product_info
            
            # Extract product name/ID from message
            import re
            
            # Look for product ID pattern (e.g., "product ABC123" or "item xyz")
            product_id_patterns = [
                r'product\s+([A-Za-z0-9_-]+)',
                r'item\s+([A-Za-z0-9_-]+)',
                r'product\s+id[:\s]+([A-Za-z0-9_-]+)',
                r'item\s+id[:\s]+([A-Za-z0-9_-]+)'
            ]
            
            for pattern in product_id_patterns:
                match = re.search(pattern, latest_message, re.IGNORECASE)
                if match:
                    product_info["product_id"] = match.group(1).upper()
                    break
            
            # If no product ID found, look for product name
            if not product_info["product_id"]:
                # Check if user is asking about items in their cart
                for item in state.cart_items:
                    if item.name.lower() in latest_message.lower():
                        product_info["product_id"] = item.product_id
                        product_info["product_name"] = item.name
                        product_info["requested_quantity"] = item.quantity
                        break
            
            # Look for quantity indicators
            quantity_patterns = [
                r'(\d+)\s+(?:pcs?|pieces?|units?|items?)',
                r'(?:how\s+many|qty|quantity)[:\s]*(\d+)',
                r'(\d+)\s+available'
            ]
            
            for pattern in quantity_patterns:
                match = re.search(pattern, latest_message, re.IGNORECASE)
                if match:
                    product_info["requested_quantity"] = int(match.group(1))
                    break
            
            # If still no product info, try to find from recent browsing or cart
            if not product_info["product_id"] and state.cart_items:
                # Default to first cart item if user asks about "it" or "this item"
                if any(word in latest_message.lower() for word in ["it", "this", "the item"]):
                    first_item = state.cart_items[0]
                    product_info["product_id"] = first_item.product_id
                    product_info["product_name"] = first_item.name
                    product_info["requested_quantity"] = first_item.quantity
            
            logger.info(f"Extracted product info: {product_info}")
            
        except Exception as e:
            logger.error(f"Error extracting product info: {str(e)}")
        
        return product_info
    
    async def _handle_missing_product_info(self, state: ConversationState, start_time: datetime) -> Dict[str, Any]:
        """Handle cases where product information is missing"""
        try:
            # Check if user has items in cart
            if state.cart_items:
                cart_summary = []
                for item in state.cart_items:
                    cart_summary.append(f"{item.name} (x{item.quantity})")
                
                response = f"I can check availability for items in your cart:\n" + "\n".join([f"• {item}" for item in cart_summary])
                response += "\n\nWhich item would you like me to check availability for?"
                
                return {
                    "content": response,
                    "data": {
                        "cart_items": [{"name": item.name, "product_id": item.product_id} for item in state.cart_items],
                        "clarification_needed": True
                    },
                    "confidence": 0.8,
                    "processing_time": (datetime.now() - start_time).total_seconds()
                }
            else:
                response = "I'd be happy to check product availability for you! Could you please tell me which product you're interested in? You can mention the product name or ID."
                
                return {
                    "content": response,
                    "data": {"clarification_needed": True},
                    "confidence": 1.0,
                    "processing_time": (datetime.now() - start_time).total_seconds()
                }
                
        except Exception as e:
            logger.error(f"Error handling missing product info: {str(e)}")
            return {
                "content": "I need more information to check availability. Could you please specify which product you'd like me to check?",
                "data": {"clarification_needed": True},
                "confidence": 1.0,
                "processing_time": (datetime.now() - start_time).total_seconds()
            }
    
    async def _check_inventory_status(self, product_info: Dict[str, Any], state: ConversationState) -> InventoryStatus:
        """Check inventory status for the specified product"""
        try:
            product_id = product_info["product_id"]
            customer_location = state.customer_context.location if state.customer_context else None
            
            # Check stock availability
            stock_data = await check_stock(product_id, customer_location)
            
            # Get product details
            product_details = await fetch_product_by_id(product_id)
            
            # Find nearby stores if location available
            nearby_stores = []
            if customer_location:
                nearby_stores = await find_nearby_stores(product_id, customer_location)
            
            # Use Mistral to analyze inventory data
            inventory_analysis = await self.mistral_client.check_inventory(
                product_id=product_id,
                state=state,
                inventory_data=[
                    {
                        "warehouse_stock": stock_data.get("warehouse_stock", 0),
                        "store_stock": stock_data.get("store_stock", 0),
                        "product_name": product_details.get("name", "Unknown Product")
                    }
                ]
            )
            
            # Combine stock data with Mistral analysis
            final_status = InventoryStatus(
                product_id=product_id,
                available_quantity=inventory_analysis.available_quantity or stock_data.get("available_quantity", 0),
                fulfillment_options=inventory_analysis.fulfillment_options or stock_data.get("fulfillment_options", []),
                estimated_delivery=inventory_analysis.estimated_delivery,
                nearest_stores=[store["store"] for store in nearby_stores[:3]]  # Top 3 nearby stores
            )
            
            logger.info(f"Inventory status checked for {product_id}: {final_status.available_quantity} units available")
            
            return final_status
            
        except Exception as e:
            logger.error(f"Error checking inventory status: {str(e)}")
            return InventoryStatus(
                product_id=product_info["product_id"],
                available_quantity=0,
                fulfillment_options=[]
            )
    
    async def _get_fulfillment_options(
        self, 
        product_info: Dict[str, Any], 
        state: ConversationState, 
        inventory_status: InventoryStatus
    ) -> List[Dict[str, Any]]:
        """Get available fulfillment options"""
        try:
            fulfillment_options = []
            customer_location = state.customer_context.location if state.customer_context else None
            requested_qty = product_info.get("requested_quantity", 1)
            
            # Home delivery option
            if inventory_status.available_quantity >= requested_qty:
                delivery_estimate = await estimate_delivery(customer_location, product_info["product_id"])
                
                if delivery_estimate.get("delivery_available"):
                    for option in delivery_estimate.get("options", []):
                        fulfillment_options.append({
                            "type": "home_delivery",
                            "method": option.get("method", "Standard Shipping"),
                            "timeline": option.get("timeline", "2-3 business days"),
                            "cost": option.get("cost", 5.99),
                            "available": option.get("available", True)
                        })
            
            # Store pickup option
            if inventory_status.nearest_stores:
                nearest_store = inventory_status.nearest_stores[0]
                fulfillment_options.append({
                    "type": "store_pickup",
                    "method": "Store Pickup",
                    "timeline": "Same day (within 4 hours)",
                    "cost": 0.00,
                    "available": True,
                    "store_name": nearest_store.get("name", "Nearest Store"),
                    "store_address": nearest_store.get("address", "Address not available")
                })
            
            # If no specific options from analysis, provide defaults
            if not fulfillment_options:
                if inventory_status.available_quantity > 0:
                    fulfillment_options.append({
                        "type": "home_delivery",
                        "method": "Standard Shipping",
                        "timeline": "2-3 business days",
                        "cost": 5.99,
                        "available": True
                    })
                else:
                    fulfillment_options.append({
                        "type": "backorder",
                        "method": "Backorder",
                        "timeline": "1-2 weeks",
                        "cost": 0.00,
                        "available": True
                    })
            
            return fulfillment_options
            
        except Exception as e:
            logger.error(f"Error getting fulfillment options: {str(e)}")
            return [{
                "type": "standard",
                "method": "Standard Shipping",
                "timeline": "3-5 business days",
                "cost": 5.99,
                "available": True
            }]
    
    async def _generate_inventory_response(
        self,
        product_info: Dict[str, Any],
        inventory_status: InventoryStatus,
        fulfillment_options: List[Dict[str, Any]],
        state: ConversationState
    ) -> str:
        """Generate natural language response about inventory status"""
        try:
            product_name = product_info.get("product_name", "the product")
            requested_qty = product_info.get("requested_quantity", 1)
            
            # Build response based on availability
            if inventory_status.available_quantity >= requested_qty:
                # Product is available
                response = f"Great news! **{product_name}** is in stock! 📦\n\n"
                
                if inventory_status.available_quantity >= 10:
                    response += f"We have plenty available ({inventory_status.available_quantity} units in stock).\n\n"
                elif inventory_status.available_quantity >= requested_qty:
                    response += f"We have {inventory_status.available_quantity} units available, which covers your request of {requested_qty}.\n\n"
                
                # Add fulfillment options
                response += "Here are your fulfillment options:\n\n"
                
                for option in fulfillment_options:
                    cost_text = "Free" if option["cost"] == 0 else f"${option['cost']:.2f}"
                    response += f"• **{option['method']}**: {option['timeline']} ({cost_text})\n"
                
                # Add store pickup info if available
                if any(opt["type"] == "store_pickup" for opt in fulfillment_options):
                    pickup_option = next(opt for opt in fulfillment_options if opt["type"] == "store_pickup")
                    store_name = pickup_option.get("store_name", "our store")
                    response += f"\n📍 **Store Pickup**: Available at {store_name} today!"
                
                # Call to action
                response += f"\n\nWould you like me to add {product_name} to your cart, or do you need more information?"
                
            elif inventory_status.available_quantity > 0:
                # Limited stock
                response = f"**{product_name}** is currently in limited stock. ⚠️\n\n"
                response += f"We currently have {inventory_status.available_quantity} units available (you requested {requested_qty}).\n\n"
                
                if fulfillment_options:
                    response += "Here's what's available:\n\n"
                    for option in fulfillment_options:
                        response += f"• **{option['method']}**: {option['timeline']}\n"
                    
                    response += f"\nI recommend ordering soon as stock is limited!"
                
            else:
                # Out of stock
                response = f"Unfortunately, **{product_name}** is currently out of stock. 😔\n\n"
                
                if fulfillment_options:
                    backorder_option = next((opt for opt in fulfillment_options if "backorder" in opt.get("type", "")), None)
                    if backorder_option:
                        response += f"However, you can place a backorder for {backorder_option['timeline']}.\n\n"
                
                response += "Here are some alternatives:\n"
                response += "• I can notify you when it's back in stock\n"
                response += "• I can show you similar products that are available\n"
                response += "• You can check back later for updates\n\n"
                response += "What would you prefer?"
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating inventory response: {str(e)}")
            return f"Product availability for {product_info.get('product_name', 'your item')}: {inventory_status.available_quantity} in stock. Would you like to proceed with this item?"
    
    def _calculate_confidence(self, inventory_status: InventoryStatus) -> float:
        """Calculate confidence score for the inventory check"""
        try:
            base_confidence = 0.8
            
            # Boost confidence if we have detailed fulfillment options
            if len(inventory_status.fulfillment_options) > 1:
                base_confidence += 0.1
            
            # Boost confidence if we have store locations
            if inventory_status.nearest_stores:
                base_confidence += 0.1
            
            # Reduce confidence if low stock
            if inventory_status.available_quantity == 0:
                base_confidence -= 0.2
            
            return max(0.1, min(1.0, base_confidence))
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {str(e)}")
            return 0.5
    
    async def check_product_availability(
        self, 
        product_id: str, 
        user_id: str = None, 
        location: Dict[str, float] = None,
        quantity: int = 1
    ) -> Dict[str, Any]:
        """Public method to check product availability"""
        try:
            # Create a mock state for processing
            state = ConversationState(
                user_id=user_id or "anonymous",
                channel="api",
                customer_context=type('obj', (object,), {
                    'location': location
                })() if location else None
            )
            
            product_info = {
                "product_id": product_id,
                "requested_quantity": quantity
            }
            
            inventory_status = await self._check_inventory_status(product_info, state)
            fulfillment_options = await self._get_fulfillment_options(product_info, state, inventory_status)
            
            return {
                "product_id": product_id,
                "available_quantity": inventory_status.available_quantity,
                "fulfillment_options": fulfillment_options,
                "can_fulfill": inventory_status.available_quantity >= quantity
            }
            
        except Exception as e:
            logger.error(f"Error in check_product_availability: {str(e)}")
            return {"error": str(e), "available_quantity": 0, "can_fulfill": False}


# Global instance
_inventory_agent: Optional[InventoryAgent] = None


async def get_inventory_agent() -> InventoryAgent:
    """Get or create global inventory agent instance"""
    global _inventory_agent
    
    if _inventory_agent is None:
        _inventory_agent = InventoryAgent()
        await _inventory_agent.initialize()
    
    return _inventory_agent