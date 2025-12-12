"""
Shared Utilities and Type Definitions for LangGraph Sales Agent System

This module contains common utilities, type definitions, and helper functions
used across all agents in the sales system.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable, TypeVar, Union
from datetime import datetime, timedelta
from functools import wraps
from enum import Enum
import json
import uuid


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Type Definitions
T = TypeVar('T')
AgentState = Dict[str, Any]


class IntentType(Enum):
    """Enumeration of possible user intents"""
    GREETING = "greeting"
    BROWSE = "browse"
    SEARCH = "search"
    RECOMMEND = "recommend"
    ADD_TO_CART = "add_to_cart"
    CHECKOUT = "checkout"
    INVENTORY_CHECK = "inventory_check"
    LOYALTY = "loyalty"
    SUPPORT = "support"
    GENERAL_CHAT = "general_chat"


class AgentType(Enum):
    """Enumeration of available agents"""
    SALES_ORCHESTRATOR = "sales_orchestrator"
    RECOMMENDATION_AGENT = "recommendation_agent"
    INVENTORY_AGENT = "inventory_agent"
    CART_AGENT = "cart_agent"
    LOYALTY_AGENT = "loyalty_agent"


class FulfillmentType(Enum):
    """Types of order fulfillment"""
    HOME_DELIVERY = "home_delivery"
    STORE_PICKUP = "store_pickup"
    EXPRESS_DELIVERY = "express_delivery"


class LoyaltyTier(Enum):
    """Customer loyalty tiers"""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


# Utility Functions

def generate_session_id() -> str:
    """Generate a unique session identifier"""
    return str(uuid.uuid4())


def generate_message_id() -> str:
    """Generate a unique message identifier"""
    return str(uuid.uuid4())


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format amount as currency string"""
    symbols = {"USD": "$", "EUR": "€", "GBP": "£"}
    symbol = symbols.get(currency, "$")
    return f"{symbol}{amount:.2f}"


def format_datetime(dt: datetime) -> str:
    """Format datetime as readable string"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def parse_json_safely(json_string: str, default: Any = None) -> Any:
    """Safely parse JSON string with fallback"""
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError):
        return default


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def calculate_cart_metrics(cart_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate summary metrics for cart items"""
    if not cart_items:
        return {
            "total_items": 0,
            "total_quantity": 0,
            "subtotal": 0.0,
            "average_item_price": 0.0
        }
    
    total_items = len(cart_items)
    total_quantity = sum(item.get("quantity", 0) for item in cart_items)
    subtotal = sum(item.get("quantity", 0) * item.get("price", 0.0) for item in cart_items)
    average_item_price = subtotal / total_quantity if total_items > 0 else 0.0
    
    return {
        "total_items": total_items,
        "total_quantity": total_quantity,
        "subtotal": subtotal,
        "average_item_price": average_item_price
    }


def calculate_tax_amount(subtotal: float, tax_rate: float = 0.08) -> float:
    """Calculate tax amount based on subtotal and tax rate"""
    return subtotal * tax_rate


def calculate_loyalty_discount(subtotal: float, tier: str) -> Dict[str, Any]:
    """Calculate loyalty discount based on customer tier"""
    tier_discounts = {
        "bronze": 0.0,
        "silver": 0.05,  # 5%
        "gold": 0.10,    # 10%
        "platinum": 0.15 # 15%
    }
    
    discount_rate = tier_discounts.get(tier.lower(), 0.0)
    discount_amount = subtotal * discount_rate
    
    return {
        "discount_rate": discount_rate,
        "discount_amount": discount_amount,
        "tier": tier.lower()
    }


def estimate_delivery_time(location: Optional[Dict[str, float]], method: str) -> str:
    """Estimate delivery time based on location and method"""
    if method == "store_pickup":
        return "Same day (within 4 hours)"
    elif method == "express_delivery":
        return "Next business day"
    elif method == "home_delivery":
        if location and _is_major_city(location):
            return "1-2 business days"
        else:
            return "2-3 business days"
    else:
        return "3-5 business days"


def _is_major_city(location: Dict[str, float]) -> bool:
    """Check if location is in a major city area"""
    if not location:
        return False
    
    lat, lng = location["lat"], location["lng"]
    
    # Major city coordinates (simplified)
    major_cities = [
        {"lat": 40.7128, "lng": -74.0060, "radius": 0.5},  # New York
        {"lat": 34.0522, "lng": -118.2437, "radius": 0.5}, # Los Angeles
        {"lat": 41.8781, "lng": -87.6298, "radius": 0.5},  # Chicago
        {"lat": 37.7749, "lng": -122.4194, "radius": 0.3}, # San Francisco
        {"lat": 25.7617, "lng": -80.1918, "radius": 0.3},  # Miami
    ]
    
    for city in major_cities:
        import math
        distance = math.sqrt((lat - city["lat"])**2 + (lng - city["lng"])**2)
        if distance < city["radius"]:
            return True
    
    return False


def validate_email(email: str) -> bool:
    """Basic email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_phone_number(phone: str) -> bool:
    """Basic phone number validation"""
    import re
    pattern = r'^\+?1?-?\.?\s?\(?(\d{3})\)?[\s\-\.]?(\d{3})[\s\-\.]?(\d{4})$'
    return re.match(pattern, phone) is not None


def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two coordinates in kilometers"""
    import math
    
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    
    a = (math.sin(delta_lat / 2) * math.sin(delta_lat / 2) +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lng / 2) * math.sin(delta_lng / 2))
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    
    return distance


# Decorators

def async_retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator for retrying async functions with exponential backoff"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = delay * (backoff ** attempt)
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}: {str(e)}")
            
            raise last_exception
        
        return wrapper
    return decorator


def log_agent_execution(agent_name: str):
    """Decorator to log agent execution"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = datetime.now()
            logger.info(f"Starting {agent_name} execution")
            
            try:
                result = await func(*args, **kwargs)
                execution_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"{agent_name} completed successfully in {execution_time:.2f}s")
                return result
            except Exception as e:
                execution_time = (datetime.now() - start_time).total_seconds()
                logger.error(f"{agent_name} failed after {execution_time:.2f}s: {str(e)}")
                raise
        
        return wrapper
    return decorator


def validate_input(required_fields: List[str]):
    """Decorator to validate required input fields"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(state: AgentState, *args, **kwargs):
            missing_fields = []
            for field in required_fields:
                if field not in state or state[field] is None:
                    missing_fields.append(field)
            
            if missing_fields:
                raise ValueError(f"Missing required fields in state: {missing_fields}")
            
            return await func(state, *args, **kwargs)
        
        return wrapper
    return decorator


# Reducer Functions for LangGraph State Management

def add_message_reducer(state: AgentState, message: Dict[str, Any]) -> AgentState:
    """Reducer to add message to conversation"""
    messages = state.get("messages", [])
    messages.append({
        **message,
        "timestamp": datetime.now().isoformat(),
        "id": generate_message_id()
    })
    return {**state, "messages": messages}


def update_intent_reducer(state: AgentState, intent: str, confidence: float = 1.0) -> AgentState:
    """Reducer to update current intent"""
    return {
        **state,
        "current_intent": intent,
        "intent_confidence": confidence,
        "last_intent_update": datetime.now().isoformat()
    }


def add_agent_response_reducer(state: AgentState, agent_name: str, content: str, data: Dict[str, Any] = None) -> AgentState:
    """Reducer to add agent response"""
    responses = state.get("agent_responses", [])
    responses.append({
        "agent_name": agent_name,
        "content": content,
        "data": data or {},
        "timestamp": datetime.now().isoformat()
    })
    return {
        **state,
        "agent_responses": responses,
        "last_agent": agent_name,
        "last_response": content
    }


def update_cart_reducer(state: AgentState, action: str, item_data: Dict[str, Any]) -> AgentState:
    """Reducer to update cart state"""
    cart_items = state.get("cart_items", [])
    
    if action == "add":
        cart_items.append({
            **item_data,
            "added_at": datetime.now().isoformat()
        })
    elif action == "remove":
        cart_items = [item for item in cart_items if item.get("product_id") != item_data.get("product_id")]
    elif action == "update":
        for item in cart_items:
            if item.get("product_id") == item_data.get("product_id"):
                item.update(item_data)
    
    return {
        **state,
        "cart_items": cart_items,
        "cart_updated_at": datetime.now().isoformat()
    }


def add_error_reducer(state: AgentState, error_message: str, agent_name: str = None) -> AgentState:
    """Reducer to add error information"""
    errors = state.get("errors", [])
    errors.append({
        "message": error_message,
        "agent": agent_name,
        "timestamp": datetime.now().isoformat()
    })
    error_count = state.get("error_count", 0) + 1
    
    return {
        **state,
        "errors": errors,
        "error_count": error_count,
        "has_errors": True
    }


def update_metadata_reducer(state: AgentState, metadata: Dict[str, Any]) -> AgentState:
    """Reducer to update metadata"""
    current_metadata = state.get("metadata", {})
    updated_metadata = {**current_metadata, **metadata}
    
    return {
        **state,
        "metadata": updated_metadata,
        "updated_at": datetime.now().isoformat()
    }


# Response Formatting Functions

def format_product_list(products: List[Dict[str, Any]], max_items: int = 5) -> str:
    """Format product list as readable text"""
    if not products:
        return "No products found."
    
    formatted = []
    for i, product in enumerate(products[:max_items], 1):
        name = product.get("name", "Unknown Product")
        price = product.get("price", 0.0)
        formatted.append(f"{i}. {name} - {format_currency(price)}")
    
    if len(products) > max_items:
        formatted.append(f"... and {len(products) - max_items} more products")
    
    return "\n".join(formatted)


def format_cart_summary(cart_items: List[Dict[str, Any]], total: float) -> str:
    """Format cart summary"""
    if not cart_items:
        return "Your cart is empty."
    
    summary = ["Your cart contains:"]
    for item in cart_items:
        name = item.get("name", "Unknown Item")
        quantity = item.get("quantity", 1)
        price = item.get("price", 0.0)
        item_total = quantity * price
        summary.append(f"• {name} (x{quantity}) - {format_currency(item_total)}")
    
    summary.append(f"\nTotal: {format_currency(total)}")
    return "\n".join(summary)


def format_fulfillment_options(options: List[Dict[str, Any]]) -> str:
    """Format fulfillment options"""
    if not options:
        return "No fulfillment options available."
    
    formatted = []
    for option in options:
        method = option.get("method", "Unknown")
        timeline = option.get("timeline", "Unknown timeline")
        cost = option.get("cost", 0.0)
        cost_text = format_currency(cost) if cost > 0 else "Free"
        formatted.append(f"• {method}: {timeline} ({cost_text})")
    
    return "\n".join(formatted)


# Configuration Constants

SUPPORTED_CHANNELS = ["web", "mobile", "whatsapp", "telegram", "sms", "email"]
SUPPORTED_CURRENCIES = ["USD", "EUR", "GBP", "CAD", "AUD"]
DEFAULT_TAX_RATE = 0.08
DEFAULT_DELIVERY_COST = 5.99
MAX_CART_ITEMS = 50
MAX_CONVERSATION_HISTORY = 100

# Timeout constants (in seconds)
AGENT_TIMEOUT = 30
DATABASE_TIMEOUT = 10
LLM_TIMEOUT = 45
TOTAL_WORKFLOW_TIMEOUT = 120