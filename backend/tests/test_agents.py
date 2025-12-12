"""
Unit tests for Sales Agent System

This file contains unit tests for the individual agents and components.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from backend.agents.state import ConversationState, CartItem, CustomerContext
from backend.agents.sales_agent import SalesOrchestrator
from backend.agents.recommendation_agent import RecommendationAgent
from backend.agents.inventory_agent import InventoryAgent
from backend.agents.cart_agent import CartAgent
from backend.agents.loyalty_agent import LoyaltyAgent


class TestConversationState:
    """Test the ConversationState model"""
    
    def test_initial_state(self):
        """Test creating initial conversation state"""
        state = ConversationState(
            user_id="user123",
            channel="web"
        )
        
        assert state.user_id == "user123"
        assert state.channel == "web"
        assert state.session_id is not None
        assert len(state.messages) == 0
        assert len(state.cart_items) == 0
        assert state.current_intent is None
        assert state.is_active is True
    
    def test_add_message(self):
        """Test adding messages to conversation"""
        state = ConversationState(user_id="user123", channel="web")
        
        state.add_message("user", "Hello there!")
        
        assert len(state.messages) == 1
        assert state.messages[0].role == "user"
        assert state.messages[0].content == "Hello there!"
        assert state.messages[0].agent_name is None
    
    def test_add_to_cart(self):
        """Test adding items to cart"""
        state = ConversationState(user_id="user123", channel="web")
        
        # Add first item
        item1 = state.add_to_cart("prod001", 2, 29.99, "Test Product")
        
        assert len(state.cart_items) == 1
        assert item1.product_id == "prod001"
        assert item1.quantity == 2
        assert item1.price == 29.99
        
        # Add same item with different color
        item2 = state.add_to_cart("prod001", 1, 29.99, "Test Product", color="red")
        
        assert len(state.cart_items) == 2
        assert item2.color == "red"
    
    def test_cart_totals(self):
        """Test cart total calculations"""
        state = ConversationState(user_id="user123", channel="web")
        
        state.add_to_cart("prod001", 2, 10.00, "Product 1")
        state.add_to_cart("prod002", 1, 25.00, "Product 2")
        
        assert state.get_cart_total() == 45.00
        assert state.get_cart_items_count() == 3


class TestSalesOrchestrator:
    """Test the Sales Orchestrator"""
    
    @pytest.fixture
    def mock_mistral_client(self):
        """Mock Mistral client"""
        with patch('backend.agents.sales_agent.get_mistral_client') as mock:
            mock_client = Mock()
            mock_client.analyze_intent = AsyncMock()
            mock_client.generate_sales_response = AsyncMock(return_value="Hello! How can I help?")
            mock.return_value = mock_client
            yield mock_client
    
    @pytest.mark.asyncio
    async def test_process_message(self, mock_mistral_client):
        """Test processing a message through the orchestrator"""
        orchestrator = SalesOrchestrator()
        
        # Mock the graph
        mock_graph = Mock()
        mock_graph.ainvoke = AsyncMock()
        mock_graph.ainvoke.return_value = ConversationState(
            user_id="user123",
            channel="web"
        )
        orchestrator.graph = mock_graph
        
        state = ConversationState(user_id="user123", channel="web")
        state.add_message("user", "I want to buy a laptop")
        
        result = await orchestrator.process_message(state)
        
        assert result.user_id == "user123"
        mock_graph.ainvoke.assert_called_once()


class TestRecommendationAgent:
    """Test the Recommendation Agent"""
    
    @pytest.fixture
    def mock_mistral_client(self):
        """Mock Mistral client"""
        with patch('backend.agents.recommendation_agent.get_mistral_client') as mock:
            mock_client = Mock()
            mock_client.get_recommendations = AsyncMock(return_value=[])
            mock.return_value = mock_client
            yield mock_client
    
    @pytest.fixture
    def mock_database_tools(self):
        """Mock database tools"""
        with patch('backend.agents.recommendation_agent.fetch_customer_preferences') as mock_pref, \
             patch('backend.agents.recommendation_agent.fetch_products') as mock_products, \
             patch('backend.agents.recommendation_agent.get_active_promotions') as mock_promos:
            
            mock_pref.return_value = {
                "preferences": {"category": "electronics"},
                "past_purchases": [],
                "browsing_history": [],
                "loyalty_tier": "bronze"
            }
            
            mock_products.return_value = [
                {"product_id": "prod001", "name": "Laptop", "price": 999.99, "category": "electronics"}
            ]
            
            mock_promos.return_value = []
            
            yield {
                "preferences": mock_pref,
                "products": mock_products,
                "promotions": mock_promos
            }
    
    @pytest.mark.asyncio
    async def test_process_recommendations(self, mock_mistral_client, mock_database_tools):
        """Test processing recommendation request"""
        agent = RecommendationAgent()
        await agent.initialize()
        
        state = ConversationState(user_id="user123", channel="web")
        state.add_message("user", "I need a new laptop")
        
        result = await agent.process(state)
        
        assert "content" in result
        assert "data" in result
        assert "confidence" in result
        assert result["confidence"] > 0


class TestCartAgent:
    """Test the Cart Agent"""
    
    @pytest.fixture
    def mock_database_tools(self):
        """Mock database tools"""
        with patch('backend.agents.cart_agent.fetch_product_by_id') as mock_product, \
             patch('backend.agents.cart_agent.add_to_cart') as mock_add:
            
            mock_product.return_value = {
                "product_id": "prod001",
                "name": "Test Product",
                "price": 29.99,
                "status": "active"
            }
            mock_add.return_value = True
            
            yield {
                "product": mock_product,
                "add_to_cart": mock_add
            }
    
    @pytest.mark.asyncio
    async def test_add_item_to_cart(self, mock_database_tools):
        """Test adding item to cart"""
        agent = CartAgent()
        await agent.initialize()
        
        state = ConversationState(user_id="user123", channel="web")
        state.add_message("user", "Add laptop to cart")
        
        result = await agent.process(state)
        
        assert "content" in result
        assert "added_item" in result["data"]
        assert result["data"]["added_item"]["name"] == "Test Product"


class TestInventoryAgent:
    """Test the Inventory Agent"""
    
    @pytest.fixture
    def mock_mistral_client(self):
        """Mock Mistral client"""
        with patch('backend.agents.inventory_agent.get_mistral_client') as mock:
            mock_client = Mock()
            mock_client.check_inventory = AsyncMock()
            mock_client.check_inventory.return_value = Mock(
                available_quantity=10,
                fulfillment_options=[{"method": "Standard Shipping", "timeline": "2-3 days", "cost": 5.99}],
                estimated_delivery="2-3 business days",
                nearest_stores=[]
            )
            mock.return_value = mock_client
            yield mock_client
    
    @pytest.fixture
    def mock_database_tools(self):
        """Mock database tools"""
        with patch('backend.agents.inventory_agent.check_stock') as mock_stock, \
             patch('backend.agents.inventory_agent.fetch_product_by_id') as mock_product:
            
            mock_stock.return_value = {
                "available_quantity": 10,
                "warehouse_stock": 8,
                "store_stock": 2,
                "fulfillment_options": []
            }
            
            mock_product.return_value = {
                "product_id": "prod001",
                "name": "Test Product",
                "status": "active"
            }
            
            yield {
                "stock": mock_stock,
                "product": mock_product
            }
    
    @pytest.mark.asyncio
    async def test_check_inventory(self, mock_mistral_client, mock_database_tools):
        """Test checking inventory status"""
        agent = InventoryAgent()
        await agent.initialize()
        
        state = ConversationState(user_id="user123", channel="web")
        state.add_message("user", "Is the laptop in stock?")
        
        result = await agent.process(state)
        
        assert "content" in result
        assert "inventory_status" in result["data"]
        assert result["data"]["inventory_status"]["available_quantity"] == 10


class TestLoyaltyAgent:
    """Test the Loyalty Agent"""
    
    @pytest.fixture
    def mock_mistral_client(self):
        """Mock Mistral client"""
        with patch('backend.agents.loyalty_agent.get_mistral_client') as mock:
            mock_client = Mock()
            mock_client.calculate_loyalty_benefits = AsyncMock()
            mock_client.calculate_loyalty_benefits.return_value = Mock(
                current_tier="gold",
                points_balance=500,
                available_discounts=[{"type": "tier_discount", "savings": 10.00}],
                points_to_next_tier=500,
                applicable_coupons=[]
            )
            mock.return_value = mock_client
            yield mock_client
    
    @pytest.fixture
    def mock_database_tools(self):
        """Mock database tools"""
        with patch('backend.agents.loyalty_agent.get_loyalty_profile') as mock_profile, \
             patch('backend.agents.loyalty_agent.get_available_coupons') as mock_coupons:
            
            mock_profile.return_value = {
                "user_id": "user123",
                "current_tier": "gold",
                "points_balance": 500,
                "total_spent": 2000.00
            }
            
            mock_coupons.return_value = [
                {"code": "GOLD20", "discount": 20.00, "description": "20% off for gold members"}
            ]
            
            yield {
                "profile": mock_profile,
                "coupons": mock_coupons
            }
    
    @pytest.mark.asyncio
    async def test_check_loyalty_status(self, mock_mistral_client, mock_database_tools):
        """Test checking loyalty status"""
        agent = LoyaltyAgent()
        await agent.initialize()
        
        state = ConversationState(user_id="user123", channel="web")
        state.add_message("user", "Check my loyalty status")
        
        result = await agent.process(state)
        
        assert "content" in result
        assert "loyalty_profile" in result["data"]
        assert result["data"]["loyalty_profile"]["current_tier"] == "gold"


# Integration Tests
class TestIntegrationFlows:
    """Test integration flows between agents"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_conversation(self):
        """Test a complete conversation flow"""
        # This would test the full flow from user input to final response
        # including intent analysis, agent routing, and response generation
        pass
    
    @pytest.mark.asyncio
    async def test_cart_to_checkout_flow(self):
        """Test cart management to checkout flow"""
        # This would test adding items, viewing cart, and proceeding to checkout
        pass
    
    @pytest.mark.asyncio
    async def test_recommendation_to_purchase_flow(self):
        """Test from recommendation to purchase flow"""
        # This would test getting recommendations and adding items to cart
        pass


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])