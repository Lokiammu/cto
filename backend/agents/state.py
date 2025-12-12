"""
Conversation State Model for LangGraph Sales Agent

This module defines the Pydantic models that represent the state flowing
through all agents in the sales conversation system.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator
import uuid


class CartItem(BaseModel):
    """Individual cart item representation"""
    product_id: str = Field(..., description="Unique product identifier")
    quantity: int = Field(..., ge=1, description="Quantity to purchase")
    price: float = Field(..., ge=0, description="Unit price")
    name: str = Field(..., description="Product name")
    color: Optional[str] = Field(None, description="Selected color")
    size: Optional[str] = Field(None, description="Selected size")
    added_at: datetime = Field(default_factory=datetime.now, description="When item was added")
    
    @validator('quantity')
    def validate_quantity(cls, v):
        if v < 1:
            raise ValueError('Quantity must be at least 1')
        return v


class CustomerContext(BaseModel):
    """Customer profile and preferences"""
    user_id: str = Field(..., description="User identifier")
    name: str = Field(..., description="Customer name")
    email: str = Field(..., description="Customer email")
    loyalty_tier: str = Field(default="bronze", description="Loyalty tier: bronze, silver, gold, platinum")
    loyalty_points: int = Field(default=0, ge=0, description="Current loyalty points")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="Customer preferences")
    past_purchases: List[Dict[str, Any]] = Field(default_factory=list, description="Purchase history")
    browsing_history: List[Dict[str, Any]] = Field(default_factory=list, description="Recent browsing activity")
    location: Optional[Dict[str, float]] = Field(None, description="Customer location {lat, lng}")
    communication_preferences: Dict[str, Any] = Field(default_factory=dict, description="How customer prefers to be contacted")


class AgentResponse(BaseModel):
    """Response from a specific agent"""
    agent_name: str = Field(..., description="Name of the agent that responded")
    content: str = Field(..., description="Natural language response")
    data: Dict[str, Any] = Field(default_factory=dict, description="Structured data from the agent")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    processing_time: float = Field(default=0.0, ge=0.0, description="Processing time in seconds")
    timestamp: datetime = Field(default_factory=datetime.now, description="When response was generated")


class ConversationMessage(BaseModel):
    """Individual message in conversation"""
    role: str = Field(..., description="Message role: user, assistant, system")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.now, description="When message was created")
    agent_name: Optional[str] = Field(None, description="Which agent generated this message")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional message metadata")


class ConversationState(BaseModel):
    """
    Main state object that flows through all LangGraph agents
    
    This state represents the complete conversation context and is passed
    between all agents in the sales system.
    """
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique session identifier")
    user_id: str = Field(..., description="User identifier")
    channel: str = Field(..., description="Communication channel: web, mobile, whatsapp, etc.")
    
    # Conversation flow
    messages: List[ConversationMessage] = Field(default_factory=list, description="Complete conversation history")
    current_intent: Optional[str] = Field(None, description="Current user intent: browse, recommend, checkout, etc.")
    last_agent: Optional[str] = Field(None, description="Last agent that responded")
    
    # Shopping context
    cart_items: List[CartItem] = Field(default_factory=list, description="Items in cart")
    customer_context: Optional[CustomerContext] = Field(None, description="Customer profile and preferences")
    
    # Agent orchestration
    agent_responses: List[AgentResponse] = Field(default_factory=list, description="Responses from all agents")
    pending_actions: List[Dict[str, Any]] = Field(default_factory=list, description="Actions waiting to be processed")
    
    # System metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional system metadata")
    created_at: datetime = Field(default_factory=datetime.now, description="Session creation time")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")
    
    # Workflow state
    is_active: bool = Field(default=True, description="Whether this conversation is still active")
    workflow_step: str = Field(default="initial", description="Current step in the workflow")
    error_count: int = Field(default=0, ge=0, description="Number of errors encountered")
    
    @validator('channel')
    def validate_channel(cls, v):
        valid_channels = ['web', 'mobile', 'whatsapp', 'telegram', 'sms', 'email']
        if v not in valid_channels:
            raise ValueError(f'Channel must be one of: {valid_channels}')
        return v
    
    @validator('current_intent')
    def validate_intent(cls, v):
        if v is not None:
            valid_intents = [
                'greeting', 'browse', 'search', 'recommend', 'add_to_cart', 
                'checkout', 'inventory_check', 'loyalty', 'support', 'general_chat'
            ]
            if v not in valid_intents:
                raise ValueError(f'Intent must be one of: {valid_intents}')
        return v
    
    def add_message(self, role: str, content: str, agent_name: str = None, metadata: Dict[str, Any] = None):
        """Add a new message to the conversation history"""
        message = ConversationMessage(
            role=role,
            content=content,
            agent_name=agent_name,
            metadata=metadata or {}
        )
        self.messages.append(message)
        self.updated_at = datetime.now()
    
    def add_agent_response(self, agent_name: str, content: str, data: Dict[str, Any] = None, 
                          confidence: float = 1.0, processing_time: float = 0.0):
        """Add a response from a specific agent"""
        response = AgentResponse(
            agent_name=agent_name,
            content=content,
            data=data or {},
            confidence=confidence,
            processing_time=processing_time
        )
        self.agent_responses.append(response)
        self.last_agent = agent_name
        self.updated_at = datetime.now()
    
    def add_to_cart(self, product_id: str, quantity: int, price: float, name: str, 
                   color: str = None, size: str = None):
        """Add an item to the cart"""
        # Check if item already exists with same attributes
        for item in self.cart_items:
            if (item.product_id == product_id and 
                item.color == color and 
                item.size == size):
                item.quantity += quantity
                self.updated_at = datetime.now()
                return item
        
        # Add new item
        cart_item = CartItem(
            product_id=product_id,
            quantity=quantity,
            price=price,
            name=name,
            color=color,
            size=size
        )
        self.cart_items.append(cart_item)
        self.updated_at = datetime.now()
        return cart_item
    
    def get_cart_total(self) -> float:
        """Calculate total cart value"""
        return sum(item.quantity * item.price for item in self.cart_items)
    
    def get_cart_items_count(self) -> int:
        """Get total number of items in cart"""
        return sum(item.quantity for item in self.cart_items)
    
    def update_customer_context(self, **kwargs):
        """Update customer context with new information"""
        if self.customer_context is None:
            self.customer_context = CustomerContext(**kwargs)
        else:
            for key, value in kwargs.items():
                setattr(self.customer_context, key, value)
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for MongoDB storage"""
        return self.dict()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create state from dictionary (MongoDB retrieval)"""
        return cls(**data)


class IntentAnalysis(BaseModel):
    """Result of intent analysis by Mistral LLM"""
    intent: str = Field(..., description="Detected intent")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in intent detection")
    entities: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted entities")
    suggested_agents: List[str] = Field(default_factory=list, description="Which agents should handle this intent")
    reasoning: str = Field(..., description="LLM reasoning for the decision")


class ProductRecommendation(BaseModel):
    """Product recommendation result"""
    product_id: str = Field(..., description="Product identifier")
    name: str = Field(..., description="Product name")
    description: str = Field(..., description="Product description")
    price: float = Field(..., ge=0, description="Current price")
    image_url: Optional[str] = Field(None, description="Product image URL")
    availability: str = Field(..., description="Availability status")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Recommendation confidence")
    reason: str = Field(..., description="Why this product was recommended")
    discount_applied: Optional[float] = Field(None, description="Discount percentage applied")


class InventoryStatus(BaseModel):
    """Inventory availability result"""
    product_id: str = Field(..., description="Product identifier")
    available_quantity: int = Field(..., ge=0, description="Available quantity")
    fulfillment_options: List[Dict[str, Any]] = Field(default_factory=list, description="Available fulfillment methods")
    estimated_delivery: Optional[str] = Field(None, description="Estimated delivery time")
    nearest_stores: List[Dict[str, Any]] = Field(default_factory=list, description="Nearby stores with stock")


class LoyaltyStatus(BaseModel):
    """Loyalty program status"""
    user_id: str = Field(..., description="User identifier")
    current_tier: str = Field(..., description="Current loyalty tier")
    points_balance: int = Field(..., ge=0, description="Current points balance")
    available_discounts: List[Dict[str, Any]] = Field(default_factory=list, description="Available discount opportunities")
    points_to_next_tier: int = Field(..., ge=0, description="Points needed for next tier")
    applicable_coupons: List[Dict[str, Any]] = Field(default_factory=list, description="Available coupons")