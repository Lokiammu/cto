"""
Cart Agent

This agent specializes in shopping cart management, including adding/removing items,
calculating totals, applying discounts, and facilitating the checkout process.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .state import ConversationState
from .utils import (
    log_agent_execution, format_currency, format_cart_summary,
    calculate_cart_metrics, calculate_tax_amount, calculate_loyalty_discount
)
from ..llm.mistral_client import get_mistral_client
from ..tools.database_tools import (
    fetch_product_by_id, add_to_cart, get_cart, update_cart_item,
    clear_cart, calculate_cart_total, apply_loyalty_discount, get_loyalty_profile
)

# Configure logging
logger = logging.getLogger(__name__)


class CartAgent:
    """
    Shopping cart management specialist agent.
    
    This agent handles all cart operations including adding items, updating quantities,
    calculating totals with taxes and discounts, and facilitating checkout.
    """
    
    def __init__(self):
        self.mistral_client = None
    
    async def initialize(self):
        """Initialize the cart agent"""
        self.mistral_client = get_mistral_client()
    
    @log_agent_execution("CartAgent.process")
    async def process(self, state: ConversationState) -> Dict[str, Any]:
        """Main processing function for the cart agent"""
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting cart process for user: {state.user_id}")
            
            # Step 1: Determine cart action from user intent
            cart_action = await self._determine_cart_action(state)
            
            if cart_action == "add_item":
                result = await self._add_item_to_cart(state)
            elif cart_action == "update_item":
                result = await self._update_cart_item(state)
            elif cart_action == "remove_item":
                result = await self._remove_item_from_cart(state)
            elif cart_action == "view_cart":
                result = await self._view_cart(state)
            elif cart_action == "checkout":
                result = await self._process_checkout(state)
            elif cart_action == "clear_cart":
                result = await self._clear_cart(state)
            else:
                result = await self._provide_cart_assistance(state)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Cart process completed in {processing_time:.2f}s")
            
            return {
                "content": result["content"],
                "data": {
                    **result.get("data", {}),
                    "cart_action": cart_action,
                    "cart_items_count": len(state.cart_items)
                },
                "confidence": result.get("confidence", 0.8),
                "processing_time": processing_time
            }
            
        except Exception as e:
            logger.error(f"Error in cart process: {str(e)}")
            return {
                "content": "I'm having trouble managing your cart right now. Please try again or contact support if the problem persists.",
                "data": {"error": str(e)},
                "confidence": 0.1,
                "processing_time": (datetime.now() - start_time).total_seconds()
            }
    
    async def _determine_cart_action(self, state: ConversationState) -> str:
        """Determine what cart action to perform based on user intent and message"""
        try:
            latest_message = None
            for msg in reversed(state.messages):
                if msg.role == "user":
                    latest_message = msg.content
                    break
            
            if not latest_message:
                return "view_cart"
            
            message_lower = latest_message.lower()
            
            # Add item patterns
            add_patterns = [
                "add", "buy", "purchase", "get", "order",
                "add to cart", "put in cart", "add it"
            ]
            if any(pattern in message_lower for pattern in add_patterns):
                return "add_item"
            
            # Update item patterns
            update_patterns = [
                "change", "update", "modify", "increase", "decrease",
                "quantity", "qty", "more", "less", "remove one"
            ]
            if any(pattern in message_lower for pattern in update_patterns):
                if "remove" in message_lower or "delete" in message_lower:
                    return "remove_item"
                else:
                    return "update_item"
            
            # Remove item patterns
            remove_patterns = [
                "remove", "delete", "cancel", "don't want", "remove from cart"
            ]
            if any(pattern in message_lower for pattern in remove_patterns):
                return "remove_item"
            
            # Checkout patterns
            checkout_patterns = [
                "checkout", "buy now", "purchase now", "complete order",
                "proceed to payment", "ready to buy", "finalize"
            ]
            if any(pattern in message_lower for pattern in checkout_patterns):
                return "checkout"
            
            # View cart patterns
            view_patterns = [
                "show cart", "view cart", "cart total", "what's in my cart",
                "my cart", "cart contents", "check cart"
            ]
            if any(pattern in message_lower for pattern in view_patterns):
                return "view_cart"
            
            # Clear cart patterns
            clear_patterns = [
                "clear cart", "empty cart", "remove all", "start over"
            ]
            if any(pattern in message_lower for pattern in clear_patterns):
                return "clear_cart"
            
            # If user has items in cart and mentions common cart words
            cart_words = ["cart", "order", "total", "checkout", "buy", "purchase"]
            if state.cart_items and any(word in message_lower for word in cart_words):
                return "view_cart"
            
            # Default to adding item if no clear intent
            return "add_item"
            
        except Exception as e:
            logger.error(f"Error determining cart action: {str(e)}")
            return "view_cart"
    
    async def _add_item_to_cart(self, state: ConversationState) -> Dict[str, Any]:
        """Add item to cart"""
        try:
            # Extract product information
            product_info = await self._extract_product_info_from_message(state)
            
            if not product_info:
                return {
                    "content": "I'd be happy to add an item to your cart! Could you please specify which product you'd like to add? You can mention the product name or ID.",
                    "data": {"clarification_needed": True},
                    "confidence": 1.0
                }
            
            # Validate and fetch product
            product = await fetch_product_by_id(product_info["product_id"])
            if not product:
                return {
                    "content": f"I couldn't find the product '{product_info.get('product_name', 'Unknown')}'. Could you please check the product name or ID and try again?",
                    "data": {"product_not_found": True, "searched_product": product_info},
                    "confidence": 0.9
                }
            
            # Add to cart in database
            success = await add_to_cart(
                user_id=state.user_id,
                product_id=product_info["product_id"],
                quantity=product_info.get("quantity", 1),
                color=product_info.get("color"),
                size=product_info.get("size")
            )
            
            if not success:
                return {
                    "content": "I had trouble adding the item to your cart. Please try again.",
                    "data": {"db_error": True},
                    "confidence": 0.1
                }
            
            # Add to local state
            cart_item = state.add_to_cart(
                product_id=product["product_id"],
                quantity=product_info.get("quantity", 1),
                price=product.get("price", 0.0),
                name=product.get("name", "Unknown Product"),
                color=product_info.get("color"),
                size=product_info.get("size")
            )
            
            # Calculate new cart totals
            cart_metrics = calculate_cart_metrics([item.dict() for item in state.cart_items])
            tax = calculate_tax_amount(cart_metrics["subtotal"])
            loyalty_benefits = calculate_loyalty_discount(
                cart_metrics["subtotal"], 
                state.customer_context.loyalty_tier if state.customer_context else "bronze"
            )
            total = cart_metrics["subtotal"] + tax - loyalty_benefits["discount_amount"]
            
            # Generate response
            response = f"✅ Added **{product.get('name', 'Item')}** to your cart!\n\n"
            response += f"📦 **Cart Summary:**\n"
            response += f"• Items: {cart_metrics['total_items']} ({cart_metrics['total_quantity']} total quantity)\n"
            response += f"• Subtotal: {format_currency(cart_metrics['subtotal'])}\n"
            if loyalty_benefits["discount_amount"] > 0:
                response += f"• Loyalty Discount: -{format_currency(loyalty_benefits['discount_amount'])} ({loyalty_benefits['tier']} member)\n"
            response += f"• Tax: {format_currency(tax)}\n"
            response += f"• **Total: {format_currency(total)}**\n\n"
            response += "What would you like to do next?"
            
            return {
                "content": response,
                "data": {
                    "added_item": {
                        "product_id": product["product_id"],
                        "name": product.get("name"),
                        "quantity": product_info.get("quantity", 1),
                        "price": product.get("price", 0.0)
                    },
                    "cart_metrics": cart_metrics,
                    "loyalty_benefits": loyalty_benefits,
                    "total_with_tax": total
                },
                "confidence": 0.9
            }
            
        except Exception as e:
            logger.error(f"Error adding item to cart: {str(e)}")
            return {
                "content": "I encountered an error while adding the item to your cart. Please try again.",
                "data": {"error": str(e)},
                "confidence": 0.1
            }
    
    async def _update_cart_item(self, state: ConversationState) -> Dict[str, Any]:
        """Update item quantity in cart"""
        try:
            # Extract update information
            update_info = await self._extract_cart_update_info(state)
            
            if not update_info:
                return {
                    "content": "I'd be happy to update your cart! Could you please specify which item you want to change and the new quantity?",
                    "data": {"clarification_needed": True},
                    "confidence": 1.0
                }
            
            # Find the item in cart
            target_item = None
            for item in state.cart_items:
                if item.product_id == update_info["product_id"]:
                    target_item = item
                    break
            
            if not target_item:
                return {
                    "content": f"I couldn't find '{update_info.get('product_name', 'that item')}' in your cart. Would you like to see what's currently in your cart?",
                    "data": {"item_not_in_cart": True, "searched_product": update_info},
                    "confidence": 0.9
                }
            
            # Update in database
            success = await update_cart_item(
                user_id=state.user_id,
                product_id=target_item.product_id,
                quantity=update_info.get("quantity", 1),
                color=target_item.color,
                size=target_item.size
            )
            
            if not success:
                return {
                    "content": "I had trouble updating your cart. Please try again.",
                    "data": {"db_error": True},
                    "confidence": 0.1
                }
            
            # Update local state
            # Remove old item and add updated one
            state.cart_items = [item for item in state.cart_items if item.product_id != target_item.product_id]
            
            if update_info.get("quantity", 1) > 0:
                # Add updated item back
                updated_item = state.add_to_cart(
                    product_id=target_item.product_id,
                    quantity=update_info.get("quantity", 1),
                    price=target_item.price,
                    name=target_item.name,
                    color=target_item.color,
                    size=target_item.size
                )
            
            # Calculate new totals
            cart_metrics = calculate_cart_metrics([item.dict() for item in state.cart_items])
            
            response = f"✅ Updated **{target_item.name}** quantity to {update_info.get('quantity', 1)}\n\n"
            
            if len(state.cart_items) == 0:
                response += "🛒 Your cart is now empty."
            else:
                response += format_cart_summary([item.dict() for item in state.cart_items], cart_metrics["subtotal"])
                response += f"\n\n**Total: {format_currency(cart_metrics['subtotal'])}**"
            
            response += "\n\nWhat would you like to do next?"
            
            return {
                "content": response,
                "data": {
                    "updated_item": {
                        "product_id": target_item.product_id,
                        "old_quantity": target_item.quantity,
                        "new_quantity": update_info.get("quantity", 1)
                    },
                    "cart_metrics": cart_metrics
                },
                "confidence": 0.9
            }
            
        except Exception as e:
            logger.error(f"Error updating cart item: {str(e)}")
            return {
                "content": "I encountered an error while updating your cart. Please try again.",
                "data": {"error": str(e)},
                "confidence": 0.1
            }
    
    async def _remove_item_from_cart(self, state: ConversationState) -> Dict[str, Any]:
        """Remove item from cart"""
        try:
            # Extract removal information
            remove_info = await self._extract_cart_removal_info(state)
            
            if not remove_info and not state.cart_items:
                return {
                    "content": "Your cart is already empty. Would you like to browse our products instead?",
                    "data": {"empty_cart": True},
                    "confidence": 1.0
                }
            
            if not remove_info:
                if len(state.cart_items) == 1:
                    # Only one item, remove it
                    item = state.cart_items[0]
                    remove_info = {"product_id": item.product_id}
                else:
                    # Multiple items, need clarification
                    cart_list = []
                    for i, item in enumerate(state.cart_items, 1):
                        cart_list.append(f"{i}. {item.name} (x{item.quantity})")
                    
                    return {
                        "content": "I'd be happy to remove an item from your cart! Which item would you like to remove?\n\n" + "\n".join(cart_list),
                        "data": {
                            "cart_items": [{"name": item.name, "product_id": item.product_id} for item in state.cart_items],
                            "clarification_needed": True
                        },
                        "confidence": 1.0
                    }
            
            # Find and remove item
            item_to_remove = None
            for item in state.cart_items:
                if item.product_id == remove_info["product_id"]:
                    item_to_remove = item
                    break
            
            if not item_to_remove:
                return {
                    "content": f"I couldn't find that item in your cart. Here's what's currently in your cart:\n\n" + 
                              format_cart_summary([item.dict() for item in state.cart_items], sum(item.quantity * item.price for item in state.cart_items)),
                    "data": {"item_not_found": True},
                    "confidence": 0.8
                }
            
            # Remove from database
            success = await update_cart_item(
                user_id=state.user_id,
                product_id=item_to_remove.product_id,
                quantity=0,  # Setting to 0 will remove the item
                color=item_to_remove.color,
                size=item_to_remove.size
            )
            
            if not success:
                return {
                    "content": "I had trouble removing the item from your cart. Please try again.",
                    "data": {"db_error": True},
                    "confidence": 0.1
                }
            
            # Remove from local state
            state.cart_items = [item for item in state.cart_items if item.product_id != item_to_remove.product_id]
            
            # Calculate new totals
            cart_metrics = calculate_cart_metrics([item.dict() for item in state.cart_items])
            
            response = f"✅ Removed **{item_to_remove.name}** from your cart.\n\n"
            
            if len(state.cart_items) == 0:
                response += "🛒 Your cart is now empty."
            else:
                response += format_cart_summary([item.dict() for item in state.cart_items], cart_metrics["subtotal"])
                response += f"\n\n**Total: {format_currency(cart_metrics['subtotal'])}**"
            
            response += "\n\nIs there anything else I can help you with?"
            
            return {
                "content": response,
                "data": {
                    "removed_item": {
                        "product_id": item_to_remove.product_id,
                        "name": item_to_remove.name,
                        "quantity": item_to_remove.quantity
                    },
                    "cart_metrics": cart_metrics
                },
                "confidence": 0.9
            }
            
        except Exception as e:
            logger.error(f"Error removing item from cart: {str(e)}")
            return {
                "content": "I encountered an error while removing the item from your cart. Please try again.",
                "data": {"error": str(e)},
                "confidence": 0.1
            }
    
    async def _view_cart(self, state: ConversationState) -> Dict[str, Any]:
        """View current cart contents"""
        try:
            # Get cart from database
            db_cart = await get_cart(state.user_id)
            
            # Sync with local state
            if len(db_cart) != len(state.cart_items):
                state.cart_items = []
                for item in db_cart:
                    state.add_to_cart(
                        product_id=item["product_id"],
                        quantity=item["quantity"],
                        price=item.get("price", 0.0),
                        name=item.get("product_details", {}).get("name", "Unknown Product"),
                        color=item.get("color"),
                        size=item.get("size")
                    )
            
            # Calculate totals
            cart_metrics = calculate_cart_metrics([item.dict() for item in state.cart_items])
            
            if len(state.cart_items) == 0:
                response = "🛒 Your cart is currently empty.\n\nWould you like me to show you some products to add to your cart?"
                return {
                    "content": response,
                    "data": {"empty_cart": True},
                    "confidence": 1.0
                }
            
            # Use Mistral to generate cart summary
            cart_summary = await self.mistral_client.process_cart(state)
            
            response = f"🛒 **Your Cart**\n\n"
            response += format_cart_summary([item.dict() for item in state.cart_items], cart_metrics["subtotal"])
            
            # Add loyalty benefits if applicable
            if state.customer_context and state.customer_context.loyalty_tier in ["gold", "platinum"]:
                loyalty_discount = cart_metrics["subtotal"] * 0.05
                response += f"\n\n💎 **{state.customer_context.loyalty_tier.title()} Member Benefits:**"
                response += f"\n• Loyalty discount: -{format_currency(loyalty_discount)}"
            
            response += f"\n\n**Subtotal: {format_currency(cart_metrics['subtotal'])}**"
            response += f"\n**Tax (8%): {format_currency(cart_metrics['subtotal'] * 0.08)}**"
            
            total_with_tax = cart_metrics["subtotal"] + (cart_metrics["subtotal"] * 0.08)
            response += f"\n\n**Total: {format_currency(total_with_tax)}**"
            
            response += f"\n\nItems: {cart_metrics['total_quantity']} | Products: {cart_metrics['total_items']}"
            response += "\n\nWould you like to proceed to checkout or continue shopping?"
            
            return {
                "content": response,
                "data": {
                    "cart_items": [item.dict() for item in state.cart_items],
                    "cart_metrics": cart_metrics,
                    "loyalty_benefits": cart_summary.get("total_savings", 0)
                },
                "confidence": 1.0
            }
            
        except Exception as e:
            logger.error(f"Error viewing cart: {str(e)}")
            return {
                "content": "I had trouble loading your cart. Please try again.",
                "data": {"error": str(e)},
                "confidence": 0.1
            }
    
    async def _process_checkout(self, state: ConversationState) -> Dict[str, Any]:
        """Process checkout initiation"""
        try:
            if not state.cart_items:
                return {
                    "content": "Your cart is empty. Please add some items before proceeding to checkout.",
                    "data": {"empty_cart": True},
                    "confidence": 1.0
                }
            
            # Calculate final totals
            cart_metrics = calculate_cart_metrics([item.dict() for item in state.cart_items])
            subtotal = cart_metrics["subtotal"]
            tax = calculate_tax_amount(subtotal)
            loyalty_benefits = calculate_loyalty_discount(subtotal, state.customer_context.loyalty_tier if state.customer_context else "bronze")
            total = subtotal + tax - loyalty_benefits["discount_amount"]
            
            # Generate checkout summary
            response = f"🛒 **Checkout Summary**\n\n"
            response += f"**Items:** {cart_metrics['total_quantity']} items ({cart_metrics['total_items']} products)\n"
            response += f"**Subtotal:** {format_currency(subtotal)}\n"
            
            if loyalty_benefits["discount_amount"] > 0:
                response += f"**Loyalty Discount:** -{format_currency(loyalty_benefits['discount_amount'])} ({loyalty_benefits['tier']} member)\n"
            
            response += f"**Tax:** {format_currency(tax)}\n"
            response += f"**Shipping:** Free (orders over $50)\n"
            response += f"**Total:** {format_currency(total)}\n\n"
            
            response += "✅ Ready to complete your purchase?\n\n"
            response += "I'll redirect you to our secure checkout page where you can:\n"
            response += "• Enter your shipping address\n"
            response += "• Choose payment method\n"
            response += "• Review order details\n"
            response += "• Apply any additional coupons\n\n"
            response += "Would you like to proceed to checkout?"
            
            return {
                "content": response,
                "data": {
                    "checkout_summary": {
                        "subtotal": subtotal,
                        "tax": tax,
                        "loyalty_discount": loyalty_benefits["discount_amount"],
                        "total": total,
                        "items_count": cart_metrics['total_quantity']
                    },
                    "ready_for_checkout": True
                },
                "confidence": 0.9
            }
            
        except Exception as e:
            logger.error(f"Error processing checkout: {str(e)}")
            return {
                "content": "I encountered an error while preparing your checkout. Please try again.",
                "data": {"error": str(e)},
                "confidence": 0.1
            }
    
    async def _clear_cart(self, state: ConversationState) -> Dict[str, Any]:
        """Clear entire cart"""
        try:
            # Clear from database
            success = await clear_cart(state.user_id)
            
            if not success:
                return {
                    "content": "I had trouble clearing your cart. Please try again.",
                    "data": {"db_error": True},
                    "confidence": 0.1
                }
            
            # Clear local state
            state.cart_items = []
            
            response = "✅ Your cart has been cleared.\n\nReady to start fresh? I can help you find products or answer any questions you have!"
            
            return {
                "content": response,
                "data": {"cart_cleared": True},
                "confidence": 0.9
            }
            
        except Exception as e:
            logger.error(f"Error clearing cart: {str(e)}")
            return {
                "content": "I encountered an error while clearing your cart. Please try again.",
                "data": {"error": str(e)},
                "confidence": 0.1
            }
    
    async def _provide_cart_assistance(self, state: ConversationState) -> Dict[str, Any]:
        """Provide general cart assistance when intent is unclear"""
        try:
            if state.cart_items:
                cart_summary = []
                for item in state.cart_items[:3]:  # Show first 3 items
                    cart_summary.append(f"• {item.name} (x{item.quantity}) - {format_currency(item.quantity * item.price)}")
                
                if len(state.cart_items) > 3:
                    cart_summary.append(f"... and {len(state.cart_items) - 3} more items")
                
                response = "I can help you with your cart! Here's what I can do:\n\n"
                response += "🛒 **Current Items:**\n" + "\n".join(cart_summary) + "\n\n"
                response += "**I can help you:**\n"
                response += "• Add more items\n"
                response += "• Update quantities\n"
                response += "• Remove items\n"
                response += "• Calculate totals\n"
                response += "• Proceed to checkout\n\n"
                response += "What would you like to do?"
            else:
                response = "I'd be happy to help you with your cart! You can:\n\n"
                response += "• Ask me to add items to your cart\n"
                response += "• Browse products and get recommendations\n"
                response += "• Check what's in your cart\n\n"
                response += "What would you like to do?"
            
            return {
                "content": response,
                "data": {
                    "cart_items": [item.dict() for item in state.cart_items],
                    "assistance_provided": True
                },
                "confidence": 0.8
            }
            
        except Exception as e:
            logger.error(f"Error providing cart assistance: {str(e)}")
            return {
                "content": "I'm here to help with your shopping cart. What would you like to do?",
                "data": {"error": str(e)},
                "confidence": 0.5
            }
    
    async def _extract_product_info_from_message(self, state: ConversationState) -> Dict[str, Any]:
        """Extract product information from user message"""
        # This is a simplified version - in practice, this could be more sophisticated
        # using NLP or pattern matching
        
        latest_message = None
        for msg in reversed(state.messages):
            if msg.role == "user":
                latest_message = msg.content
                break
        
        if not latest_message:
            return {}
        
        import re
        
        # Look for product mentions
        product_info = {
            "product_id": None,
            "product_name": None,
            "quantity": 1,
            "color": None,
            "size": None
        }
        
        # Extract quantity
        quantity_match = re.search(r'(\d+)\s*(?:x|pcs?|pieces?|units?)', latest_message, re.IGNORECASE)
        if quantity_match:
            product_info["quantity"] = int(quantity_match.group(1))
        
        # Look for specific product references
        # This is a basic implementation - could be enhanced with actual product search
        if "laptop" in latest_message.lower():
            product_info["product_id"] = "LAPTOP001"
            product_info["product_name"] = "Laptop"
        elif "phone" in latest_message.lower():
            product_info["product_id"] = "PHONE001"
            product_info["product_name"] = "Phone"
        # Add more patterns as needed
        
        return product_info if product_info["product_id"] else {}
    
    async def _extract_cart_update_info(self, state: ConversationState) -> Dict[str, Any]:
        """Extract cart update information from user message"""
        # Simplified implementation
        latest_message = None
        for msg in reversed(state.messages):
            if msg.role == "user":
                latest_message = msg.content
                break
        
        if not latest_message:
            return {}
        
        # Extract quantity changes
        import re
        quantity_patterns = [
            r'change\s+(?:qty|quantity)\s+to\s+(\d+)',
            r'update\s+to\s+(\d+)',
            r'set\s+quantity\s+to\s+(\d+)',
            r'(\d+)\s+(?:more|less|fewer)'
        ]
        
        for pattern in quantity_patterns:
            match = re.search(pattern, latest_message, re.IGNORECASE)
            if match:
                return {
                    "product_id": state.cart_items[0].product_id if state.cart_items else None,  # Simplified
                    "quantity": int(match.group(1))
                }
        
        return {}
    
    async def _extract_cart_removal_info(self, state: ConversationState) -> Dict[str, Any]:
        """Extract cart removal information from user message"""
        # Simplified implementation
        latest_message = None
        for msg in reversed(state.messages):
            if msg.role == "user":
                latest_message = msg.content
                break
        
        if not latest_message:
            return {}
        
        # Look for specific product mentions to remove
        for item in state.cart_items:
            if item.name.lower() in latest_message.lower():
                return {"product_id": item.product_id}
        
        return {}


# Global instance
_cart_agent: Optional[CartAgent] = None


async def get_cart_agent() -> CartAgent:
    """Get or create global cart agent instance"""
    global _cart_agent
    
    if _cart_agent is None:
        _cart_agent = CartAgent()
        await _cart_agent.initialize()
    
    return _cart_agent