"""
Recommendation Agent

This agent specializes in providing personalized product recommendations based on customer data,
browsing history, past purchases, and current preferences.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .state import ConversationState, ProductRecommendation
from .utils import log_agent_execution, format_product_list
from ..llm.mistral_client import get_mistral_client
from ..tools.database_tools import (
    fetch_customer_preferences, fetch_products, search_products,
    get_active_promotions
)

# Configure logging
logger = logging.getLogger(__name__)


class RecommendationAgent:
    """
    Product recommendation specialist agent.
    
    This agent analyzes customer data and provides personalized product recommendations
    using Mistral LLM for natural language reasoning and recommendation logic.
    """
    
    def __init__(self):
        self.mistral_client = None
    
    async def initialize(self):
        """Initialize the recommendation agent"""
        self.mistral_client = get_mistral_client()
    
    @log_agent_execution("RecommendationAgent.process")
    async def process(self, state: ConversationState) -> Dict[str, Any]:
        """Main processing function for the recommendation agent"""
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting recommendation process for user: {state.user_id}")
            
            # Step 1: Fetch customer preferences and context
            customer_data = await self._fetch_customer_data(state)
            
            # Step 2: Determine search parameters
            search_params = await self._determine_search_parameters(state, customer_data)
            
            # Step 3: Fetch relevant products
            products = await self._fetch_relevant_products(search_params)
            
            # Step 4: Get active promotions
            promotions = await get_active_promotions()
            
            # Step 5: Generate recommendations using Mistral
            recommendations = await self._generate_recommendations(
                state, customer_data, products, promotions
            )
            
            # Step 6: Format response
            response = await self._format_recommendation_response(
                state, recommendations, customer_data
            )
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Recommendation process completed in {processing_time:.2f}s")
            
            return {
                "content": response,
                "data": {
                    "recommendations": [rec.dict() for rec in recommendations],
                    "customer_data": customer_data,
                    "search_parameters": search_params,
                    "products_found": len(products),
                    "promotions_count": len(promotions)
                },
                "confidence": self._calculate_confidence(recommendations, customer_data),
                "processing_time": processing_time
            }
            
        except Exception as e:
            logger.error(f"Error in recommendation process: {str(e)}")
            return {
                "content": "I'm having trouble generating recommendations right now. Let me help you browse our products instead.",
                "data": {"error": str(e)},
                "confidence": 0.1,
                "processing_time": (datetime.now() - start_time).total_seconds()
            }
    
    async def _fetch_customer_data(self, state: ConversationState) -> Dict[str, Any]:
        """Fetch comprehensive customer data for recommendations"""
        try:
            if state.customer_context:
                # Use existing customer context
                return {
                    "user_id": state.customer_context.user_id,
                    "name": state.customer_context.name,
                    "loyalty_tier": state.customer_context.loyalty_tier,
                    "preferences": state.customer_context.preferences,
                    "past_purchases": state.customer_context.past_purchases,
                    "browsing_history": state.customer_context.browsing_history,
                    "location": state.customer_context.location
                }
            else:
                # Fetch from database
                return await fetch_customer_preferences(state.user_id)
                
        except Exception as e:
            logger.error(f"Error fetching customer data: {str(e)}")
            return {}
    
    async def _determine_search_parameters(self, state: ConversationState, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Determine what products to search for based on context"""
        search_params = {
            "limit": 20,
            "category": None,
            "price_range": None,
            "tags": [],
            "featured": False
        }
        
        try:
            # Analyze the latest user message for intent and preferences
            latest_message = None
            for msg in reversed(state.messages):
                if msg.role == "user":
                    latest_message = msg.content
                    break
            
            if latest_message:
                # Extract potential product categories from message
                categories = ["electronics", "clothing", "books", "home", "sports", "beauty", "toys"]
                for category in categories:
                    if category.lower() in latest_message.lower():
                        search_params["category"] = category
                        break
                
                # Look for price indicators
                import re
                price_matches = re.findall(r'\$(\d+)', latest_message)
                if price_matches:
                    max_price = int(price_matches[-1])
                    search_params["price_range"] = {"max": max_price}
            
            # Use customer preferences to refine search
            preferences = customer_data.get("preferences", {})
            if preferences.get("favorite_categories"):
                search_params["category"] = search_params["category"] or preferences["favorite_categories"][0]
            
            # Check browsing history for patterns
            browsing_history = customer_data.get("browsing_history", [])
            if browsing_history:
                recent_categories = [item.get("category") for item in browsing_history[-5:]]
                if recent_categories and not search_params["category"]:
                    search_params["category"] = max(set(recent_categories), key=recent_categories.count)
            
            # If no specific category found, show featured products
            if not search_params["category"]:
                search_params["featured"] = True
            
            logger.info(f"Search parameters determined: {search_params}")
            
        except Exception as e:
            logger.error(f"Error determining search parameters: {str(e)}")
        
        return search_params
    
    async def _fetch_relevant_products(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch products based on search parameters"""
        try:
            filters = {}
            
            if search_params.get("category"):
                filters["category"] = search_params["category"]
            
            if search_params.get("price_range", {}).get("max"):
                filters["price"] = {"$lte": search_params["price_range"]["max"]}
            
            if search_params.get("featured"):
                filters["is_featured"] = True
            
            products = await fetch_products(filters=filters, limit=search_params.get("limit", 20))
            
            logger.info(f"Fetched {len(products)} products")
            return products
            
        except Exception as e:
            logger.error(f"Error fetching products: {str(e)}")
            return []
    
    async def _generate_recommendations(
        self, 
        state: ConversationState, 
        customer_data: Dict[str, Any], 
        products: List[Dict[str, Any]], 
        promotions: List[Dict[str, Any]]
    ) -> List[ProductRecommendation]:
        """Generate personalized recommendations using Mistral LLM"""
        try:
            if not products:
                logger.warning("No products available for recommendations")
                return []
            
            # Use Mistral to generate recommendations
            recommendations = await self.mistral_client.get_recommendations(
                state=state,
                available_products=products,
                promotions=promotions
            )
            
            # Fallback recommendations if Mistral fails
            if not recommendations:
                recommendations = await self._generate_fallback_recommendations(products, customer_data)
            
            logger.info(f"Generated {len(recommendations)} recommendations")
            return recommendations[:5]  # Limit to top 5
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return await self._generate_fallback_recommendations(products, customer_data)
    
    async def _generate_fallback_recommendations(
        self, 
        products: List[Dict[str, Any]], 
        customer_data: Dict[str, Any]
    ) -> List[ProductRecommendation]:
        """Generate fallback recommendations when Mistral fails"""
        try:
            recommendations = []
            
            # Simple heuristics for recommendations
            loyalty_tier = customer_data.get("loyalty_tier", "bronze")
            
            for i, product in enumerate(products[:5]):  # Top 5 products
                # Determine recommendation reason based on customer tier and product features
                if loyalty_tier in ["gold", "platinum"]:
                    reason = f"Premium pick for {loyalty_tier} members"
                else:
                    reason = "Popular choice among customers"
                
                # Add promotional reason if applicable
                if product.get("is_featured"):
                    reason = "Featured product - limited time offer"
                elif product.get("discount_percentage", 0) > 0:
                    reason = f"On sale - {product.get('discount_percentage', 0)}% off"
                
                recommendations.append(ProductRecommendation(
                    product_id=product.get("product_id", f"prod_{i}"),
                    name=product.get("name", "Unknown Product"),
                    description=product.get("description", ""),
                    price=product.get("price", 0.0),
                    image_url=product.get("image_url"),
                    availability="in_stock",  # Assume in stock for fallback
                    confidence=0.6,  # Lower confidence for fallback
                    reason=reason,
                    discount_applied=product.get("discount_percentage")
                ))
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating fallback recommendations: {str(e)}")
            return []
    
    async def _format_recommendation_response(
        self, 
        state: ConversationState, 
        recommendations: List[ProductRecommendation], 
        customer_data: Dict[str, Any]
    ) -> str:
        """Format recommendations into a natural language response"""
        try:
            if not recommendations:
                return "I'm still learning about your preferences. Let me show you some of our popular products instead!"
            
            customer_name = customer_data.get("name", "there")
            loyalty_tier = customer_data.get("loyalty_tier", "bronze")
            
            # Personal greeting
            greeting = f"Hi {customer_name}! 👋"
            
            # Context-aware introduction
            if loyalty_tier in ["gold", "platinum"]:
                intro = f"As a {loyalty_tier} member, I have some exclusive recommendations for you."
            else:
                intro = "Based on your interests, I think you'll love these products."
            
            # Format product list
            product_list = []
            for i, rec in enumerate(recommendations, 1):
                price_text = f"${rec.price:.2f}"
                if rec.discount_applied:
                    price_text = f"~~${rec.price:.2f}~~ ${rec.price * (1 - rec.discount_applied/100):.2f}"
                
                product_text = f"{i}. **{rec.name}** - {price_text}"
                if rec.reason:
                    product_text += f"\n   *{rec.reason}*"
                
                product_list.append(product_text)
            
            # Add call to action
            cta = "\n\nWould you like more details about any of these products, or shall I show you products in a specific category?"
            
            response = f"{greeting}\n\n{intro}\n\n" + "\n\n".join(product_list) + cta
            
            return response
            
        except Exception as e:
            logger.error(f"Error formatting recommendation response: {str(e)}")
            return "Here are some products I think you might like:\n\n" + format_product_list([
                {"name": rec.name, "price": rec.price} for rec in recommendations
            ])
    
    def _calculate_confidence(self, recommendations: List[ProductRecommendation], customer_data: Dict[str, Any]) -> float:
        """Calculate confidence score for the recommendations"""
        try:
            if not recommendations:
                return 0.1
            
            # Base confidence on recommendation quality
            avg_confidence = sum(rec.confidence for rec in recommendations) / len(recommendations)
            
            # Boost confidence if we have good customer data
            data_quality_boost = 0.0
            if customer_data.get("past_purchases"):
                data_quality_boost += 0.2
            if customer_data.get("browsing_history"):
                data_quality_boost += 0.2
            if customer_data.get("preferences"):
                data_quality_boost += 0.1
            
            final_confidence = min(avg_confidence + data_quality_boost, 1.0)
            return round(final_confidence, 2)
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {str(e)}")
            return 0.5
    
    async def get_personalized_recommendations(
        self, 
        user_id: str, 
        category: str = None, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Public method to get personalized recommendations"""
        try:
            # Create a mock state for processing
            state = ConversationState(user_id=user_id, channel="api")
            
            # Process recommendations
            result = await self.process(state)
            
            return result.get("data", {}).get("recommendations", [])
            
        except Exception as e:
            logger.error(f"Error in get_personalized_recommendations: {str(e)}")
            return []


# Global instance
_recommendation_agent: Optional[RecommendationAgent] = None


async def get_recommendation_agent() -> RecommendationAgent:
    """Get or create global recommendation agent instance"""
    global _recommendation_agent
    
    if _recommendation_agent is None:
        _recommendation_agent = RecommendationAgent()
        await _recommendation_agent.initialize()
    
    return _recommendation_agent