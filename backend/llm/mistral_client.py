"""
Mistral LLM Integration for Sales Agent System

This module provides a robust wrapper around the Mistral API with features like:
- Model selection and configuration
- Streaming support for real-time responses  
- Retry logic with exponential backoff
- Error handling for rate limits and timeouts
- Prompt template management
"""

import os
import json
import asyncio
import time
from typing import Dict, List, Any, Optional, AsyncGenerator, Union
from datetime import datetime
import logging
from dataclasses import dataclass

from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatCompletionChunk
from jinja2 import Template

from .state import IntentAnalysis, ProductRecommendation, InventoryStatus, LoyaltyStatus


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MistralConfig:
    """Configuration for Mistral client"""
    api_key: str
    model: str = "mistral-large-latest"
    temperature: float = 0.7
    max_tokens: int = 1000
    timeout: int = 30
    max_retries: int = 3
    base_retry_delay: float = 1.0


class PromptTemplateManager:
    """Manages prompt templates for different agents"""
    
    def __init__(self):
        self.templates = {
            "sales_agent_system": """
You are a friendly and knowledgeable sales assistant for an e-commerce platform. 
Your goal is to help customers find products, make purchasing decisions, and have a great shopping experience.

Context:
- Customer: {{ customer_name|default('Customer') }}
- Session ID: {{ session_id }}
- Channel: {{ channel }}
- Current intent: {{ current_intent|default('general_chat') }}
- Cart items: {{ cart_items|length if cart_items else 0 }}
- Loyalty tier: {{ loyalty_tier|default('bronze') }}

Recent conversation:
{% for message in recent_messages %}
{{ message.role }}: {{ message.content }}
{% endfor %}

Instructions:
1. Analyze the customer's intent and respond appropriately
2. Be helpful, friendly, and sales-oriented
3. Ask clarifying questions when needed
4. Recommend products based on their preferences
5. Help with cart management and checkout process
6. Apply loyalty benefits when appropriate

Respond naturally and conversationally.
""",

            "intent_analysis": """
Analyze the user's message and determine their intent.

User message: "{{ user_message }}"

Recent conversation context:
{% for message in recent_messages %}
{{ message.role }}: {{ message.content }}
{% endfor %}

Customer context:
- Loyalty tier: {{ loyalty_tier|default('none') }}
- Previous purchases: {{ past_purchases|length }}
- Current cart: {{ cart_items|length }} items

Available intents:
- greeting: User is greeting or saying hello
- browse: User wants to browse or look at products
- search: User is searching for specific products
- recommend: User wants product recommendations
- add_to_cart: User wants to add items to cart
- checkout: User wants to proceed to checkout
- inventory_check: User is asking about product availability
- loyalty: User is asking about loyalty points or benefits
- support: User needs help with an issue
- general_chat: General conversation or questions

Respond with a JSON object containing:
{
    "intent": "detected_intent",
    "confidence": 0.95,
    "entities": [{"type": "product", "value": "laptop"}],
    "reasoning": "Explanation of why this intent was detected"
}
""",

            "recommendation_agent": """
You are a product recommendation specialist. Analyze customer data and provide personalized product recommendations.

Customer Profile:
- Name: {{ customer_name }}
- Loyalty tier: {{ loyalty_tier }}
- Preferences: {{ preferences|tojson }}
- Past purchases: {{ past_purchases|length }} items
- Browsing history: {{ browsing_history|length }} items

Current Request: {{ user_message }}

Available Products:
{% for product in available_products %}
- {{ product.name }}: {{ product.description }} (${{ product.price }})
{% endfor %}

Active Promotions:
{% for promotion in promotions %}
- {{ promotion.name }}: {{ promotion.description }}
{% endfor %}

Provide 3-5 personalized recommendations. For each product, explain why it's relevant to this customer.

Respond with JSON:
{
    "recommendations": [
        {
            "product_id": "prod_123",
            "name": "Product Name",
            "reason": "Why this is recommended",
            "confidence": 0.9
        }
    ],
    "summary": "Brief summary of recommendations"
}
""",

            "inventory_agent": """
You are an inventory and fulfillment specialist. Analyze product availability and provide fulfillment options.

Product ID: {{ product_id }}
Customer Location: {{ customer_location|tojson if customer_location else "Not provided" }}

Current Inventory:
{% for warehouse in inventory_data %}
- {{ warehouse.name }}: {{ warehouse.available_qty }} units
{% endfor %}

Provide availability status and best fulfillment options.

Respond with JSON:
{
    "available_quantity": 150,
    "fulfillment_options": [
        {
            "type": "home_delivery",
            "timeline": "2-3 business days",
            "cost": 5.99
        }
    ],
    "nearest_stores": [],
    "recommendation": "Best fulfillment option"
}
""",

            "cart_agent": """
You are a shopping cart specialist. Manage cart operations and provide cart summaries.

Cart Items:
{% for item in cart_items %}
- {{ item.name }} ({{ item.quantity }}x ${{ item.price }}) = ${{ item.quantity * item.price }}
{% endfor %}

Subtotal: ${{ subtotal }}
Tax (8%): ${{ tax }}
Loyalty Discount: -${{ loyalty_discount }}
Total: ${{ total }}

Customer Loyalty Tier: {{ loyalty_tier }}
Available Points: {{ loyalty_points }}

Provide cart summary and next steps.

Respond with JSON:
{
    "cart_summary": "Cart has X items totaling $Y",
    "total_savings": {{ loyalty_discount }},
    "next_action": "proceed to checkout",
    "suggestions": ["Add protection plan", "Bundle deals"]
}
""",

            "loyalty_agent": """
You are a loyalty program specialist. Analyze customer loyalty status and suggest best discount strategies.

Customer Profile:
- Current Tier: {{ current_tier }}
- Points Balance: {{ points_balance }}
- Total Spent: ${{ total_spent }}
- Available Coupons: {{ available_coupons|length }}

Order Details:
- Order Total: ${{ order_total }}
- Items in Cart: {{ cart_items|length }}

Available Discount Opportunities:
{% for opportunity in discount_opportunities %}
- {{ opportunity.description }}: {{ opportunity.savings }}
{% endfor %}

Suggest the best discount strategy for this customer.

Respond with JSON:
{
    "recommended_action": "redeem_points",
    "discount_amount": 25.00,
    "new_points_balance": {{ new_points_balance }},
    "savings_breakdown": {
        "coupon_discount": 10.00,
        "tier_discount": 15.00
    },
    "next_tier_progress": {{ progress_to_next_tier }}
}
"""
        }
    
    def render(self, template_name: str, **kwargs) -> str:
        """Render a prompt template with variables"""
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found")
        
        template = Template(self.templates[template_name])
        return template.render(**kwargs)


class MistralClientWrapper:
    """Enhanced Mistral client with retry logic and error handling"""
    
    def __init__(self, config: MistralConfig):
        self.config = config
        self.client = MistralClient(api_key=config.api_key)
        self.prompt_manager = PromptTemplateManager()
        self.logger = logging.getLogger(__name__)
    
    async def call_with_retry(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Call Mistral API with exponential backoff retry"""
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                start_time = time.time()
                
                response = self.client.chat(
                    model=self.config.model,
                    messages=messages,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    **kwargs
                )
                
                processing_time = time.time() - start_time
                self.logger.info(f"Mistral API call completed in {processing_time:.2f}s")
                
                return {
                    "content": response.choices[0].message.content,
                    "model": response.model,
                    "usage": response.usage.dict() if response.usage else {},
                    "processing_time": processing_time
                }
                
            except Exception as e:
                last_exception = e
                self.logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < self.config.max_retries:
                    delay = self.config.base_retry_delay * (2 ** attempt)
                    self.logger.info(f"Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"All retry attempts failed: {str(e)}")
                    raise e
        
        raise last_exception
    
    async def stream_chat(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        """Stream chat response from Mistral"""
        try:
            stream = self.client.chat_stream(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                **kwargs
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            self.logger.error(f"Streaming error: {str(e)}")
            yield f"Error: Unable to stream response. {str(e)}"
    
    async def analyze_intent(self, user_message: str, state: 'ConversationState') -> IntentAnalysis:
        """Analyze user intent using Mistral"""
        recent_messages = [
            {"role": msg.role, "content": msg.content} 
            for msg in state.messages[-5:]  # Last 5 messages for context
        ]
        
        prompt = self.prompt_manager.render(
            "intent_analysis",
            user_message=user_message,
            recent_messages=recent_messages,
            loyalty_tier=state.customer_context.loyalty_tier if state.customer_context else None,
            past_purchases=state.customer_context.past_purchases if state.customer_context else [],
            cart_items=state.cart_items
        )
        
        messages = [
            {"role": "system", "content": "You are an expert at understanding customer intent in e-commerce conversations."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = await self.call_with_retry(messages)
            
            # Parse JSON response
            try:
                content = json.loads(response["content"])
                return IntentAnalysis(
                    intent=content.get("intent", "general_chat"),
                    confidence=content.get("confidence", 0.5),
                    entities=content.get("entities", []),
                    reasoning=content.get("reasoning", "")
                )
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                self.logger.warning("Failed to parse intent analysis JSON, using fallback")
                return IntentAnalysis(
                    intent="general_chat",
                    confidence=0.3,
                    reasoning=f"Could not parse intent from: {response['content']}"
                )
                
        except Exception as e:
            self.logger.error(f"Intent analysis failed: {str(e)}")
            return IntentAnalysis(
                intent="general_chat",
                confidence=0.1,
                reasoning=f"Error during analysis: {str(e)}"
            )
    
    async def get_recommendations(self, state: 'ConversationState', available_products: List[Dict], promotions: List[Dict]) -> List[ProductRecommendation]:
        """Get personalized product recommendations"""
        if not state.customer_context:
            return []
        
        prompt = self.prompt_manager.render(
            "recommendation_agent",
            customer_name=state.customer_context.name,
            loyalty_tier=state.customer_context.loyalty_tier,
            preferences=state.customer_context.preferences,
            past_purchases=state.customer_context.past_purchases,
            browsing_history=state.customer_context.browsing_history,
            user_message=state.messages[-1].content if state.messages else "",
            available_products=available_products,
            promotions=promotions
        )
        
        messages = [
            {"role": "system", "content": "You are a product recommendation AI that provides personalized suggestions."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = await self.call_with_retry(messages)
            content = json.loads(response["content"])
            
            recommendations = []
            for rec_data in content.get("recommendations", []):
                recommendations.append(ProductRecommendation(
                    product_id=rec_data["product_id"],
                    name=rec_data.get("name", "Unknown Product"),
                    description=rec_data.get("description", ""),
                    price=rec_data.get("price", 0.0),
                    confidence=rec_data.get("confidence", 0.5),
                    reason=rec_data.get("reason", "")
                ))
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Recommendation generation failed: {str(e)}")
            return []
    
    async def check_inventory(self, product_id: str, state: 'ConversationState', inventory_data: List[Dict]) -> InventoryStatus:
        """Check product inventory and fulfillment options"""
        prompt = self.prompt_manager.render(
            "inventory_agent",
            product_id=product_id,
            customer_location=state.customer_context.location if state.customer_context else None,
            inventory_data=inventory_data
        )
        
        messages = [
            {"role": "system", "content": "You are an inventory management AI that provides accurate availability information."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = await self.call_with_retry(messages)
            content = json.loads(response["content"])
            
            return InventoryStatus(
                product_id=product_id,
                available_quantity=content.get("available_quantity", 0),
                fulfillment_options=content.get("fulfillment_options", []),
                estimated_delivery=content.get("estimated_delivery"),
                nearest_stores=content.get("nearest_stores", [])
            )
            
        except Exception as e:
            self.logger.error(f"Inventory check failed: {str(e)}")
            return InventoryStatus(
                product_id=product_id,
                available_quantity=0,
                fulfillment_options=[],
                nearest_stores=[]
            )
    
    async def process_cart(self, state: 'ConversationState') -> Dict[str, Any]:
        """Process cart and provide summary"""
        subtotal = state.get_cart_total()
        tax = subtotal * 0.08  # 8% tax
        loyalty_discount = 0.0
        
        if state.customer_context and state.customer_context.loyalty_tier in ['gold', 'platinum']:
            loyalty_discount = subtotal * 0.05  # 5% discount for premium tiers
        
        total = subtotal + tax - loyalty_discount
        
        prompt = self.prompt_manager.render(
            "cart_agent",
            cart_items=[{
                "name": item.name,
                "quantity": item.quantity,
                "price": item.price
            } for item in state.cart_items],
            subtotal=subtotal,
            tax=tax,
            loyalty_discount=loyalty_discount,
            total=total,
            loyalty_tier=state.customer_context.loyalty_tier if state.customer_context else "bronze",
            loyalty_points=state.customer_context.loyalty_points if state.customer_context else 0
        )
        
        messages = [
            {"role": "system", "content": "You are a shopping cart AI that helps customers manage their purchases."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = await self.call_with_retry(messages)
            content = json.loads(response["content"])
            
            return {
                "summary": content.get("cart_summary", ""),
                "total_savings": loyalty_discount,
                "subtotal": subtotal,
                "tax": tax,
                "total": total,
                "next_action": content.get("next_action", "continue shopping"),
                "suggestions": content.get("suggestions", [])
            }
            
        except Exception as e:
            self.logger.error(f"Cart processing failed: {str(e)}")
            return {
                "summary": f"Cart has {state.get_cart_items_count()} items totaling ${total:.2f}",
                "total_savings": loyalty_discount,
                "subtotal": subtotal,
                "tax": tax,
                "total": total,
                "next_action": "continue shopping",
                "suggestions": []
            }
    
    async def calculate_loyalty_benefits(self, state: 'ConversationState', order_total: float) -> LoyaltyStatus:
        """Calculate loyalty benefits and discounts"""
        if not state.customer_context:
            return LoyaltyStatus(
                user_id=state.user_id,
                current_tier="bronze",
                points_balance=0,
                available_discounts=[]
            )
        
        customer = state.customer_context
        
        # Calculate discount opportunities
        discount_opportunities = []
        if customer.loyalty_points >= 100:
            discount_opportunities.append({
                "type": "points_redemption",
                "description": "Redeem 100 points for $5 off",
                "savings": 5.00
            })
        
        if customer.loyalty_tier == "gold":
            discount_opportunities.append({
                "type": "tier_discount",
                "description": "5% gold member discount",
                "savings": order_total * 0.05
            })
        
        prompt = self.prompt_manager.render(
            "loyalty_agent",
            current_tier=customer.loyalty_tier,
            points_balance=customer.loyalty_points,
            total_spent=sum(p.get("total", 0) for p in customer.past_purchases),
            available_coupons=discount_opportunities,
            order_total=order_total,
            cart_items=len(state.cart_items),
            discount_opportunities=discount_opportunities
        )
        
        messages = [
            {"role": "system", "content": "You are a loyalty program AI that maximizes customer benefits."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = await self.call_with_retry(messages)
            content = json.loads(response["content"])
            
            return LoyaltyStatus(
                user_id=customer.user_id,
                current_tier=customer.loyalty_tier,
                points_balance=customer.loyalty_points,
                available_discounts=discount_opportunities,
                points_to_next_tier=content.get("points_to_next_tier", 0),
                applicable_coupons=content.get("applicable_coupons", [])
            )
            
        except Exception as e:
            self.logger.error(f"Loyalty calculation failed: {str(e)}")
            return LoyaltyStatus(
                user_id=customer.user_id,
                current_tier=customer.loyalty_tier,
                points_balance=customer.loyalty_points,
                available_discounts=discount_opportunities,
                points_to_next_tier=0,
                applicable_coupons=[]
            )
    
    async def generate_sales_response(self, state: 'ConversationState') -> str:
        """Generate a natural sales response based on current state"""
        recent_context = []
        for msg in state.messages[-3:]:  # Last 3 messages
            recent_context.append({"role": msg.role, "content": msg.content})
        
        prompt = self.prompt_manager.render(
            "sales_agent_system",
            customer_name=state.customer_context.name if state.customer_context else "Customer",
            session_id=state.session_id,
            channel=state.channel,
            current_intent=state.current_intent,
            cart_items=state.cart_items,
            loyalty_tier=state.customer_context.loyalty_tier if state.customer_context else "bronze",
            recent_messages=recent_context
        )
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": state.messages[-1].content if state.messages else "Hello"}
        ]
        
        try:
            response = await self.call_with_retry(messages)
            return response["content"]
        except Exception as e:
            self.logger.error(f"Sales response generation failed: {str(e)}")
            return "I'm here to help you with your shopping needs. What can I assist you with today?"


# Global instance
_mistral_client: Optional[MistralClientWrapper] = None


def get_mistral_client() -> MistralClientWrapper:
    """Get or create global Mistral client instance"""
    global _mistral_client
    
    if _mistral_client is None:
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY environment variable not set")
        
        config = MistralConfig(api_key=api_key)
        _mistral_client = MistralClientWrapper(config)
    
    return _mistral_client


async def initialize_mistral_client(config: Optional[MistralConfig] = None) -> MistralClientWrapper:
    """Initialize Mistral client with optional custom config"""
    global _mistral_client
    
    if config is None:
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY environment variable not set")
        config = MistralConfig(api_key=api_key)
    
    _mistral_client = MistralClientWrapper(config)
    return _mistral_client