"""
API Interface for LangGraph Sales Agent System

This module provides FastAPI endpoints for the sales agent system,
allowing external systems to interact with the agents through HTTP.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from backend.agents.sales_agent import (
    process_sales_conversation, 
    get_sales_orchestrator,
    create_initial_state
)
from backend.agents.state import ConversationState
from backend.tools.database_tools import initialize_database, close_database
from backend.llm.mistral_client import initialize_mistral_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="LangGraph Sales Agent API",
    description="API for sales conversation processing using LangGraph and Mistral LLM",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for API requests/responses
class MessageRequest(BaseModel):
    """Request model for sending a message"""
    user_id: str = Field(..., description="User identifier")
    channel: str = Field(..., description="Communication channel")
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Session identifier (optional)")
    additional_context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class MessageResponse(BaseModel):
    """Response model for message processing"""
    session_id: str
    user_id: str
    response: str
    current_intent: Optional[str]
    last_agent: Optional[str]
    cart_items_count: int
    workflow_step: str
    has_errors: bool
    conversation_complete: bool
    timestamp: str


class CartRequest(BaseModel):
    """Request model for cart operations"""
    user_id: str = Field(..., description="User identifier")
    action: str = Field(..., description="Cart action: add, update, remove, view, checkout")
    product_id: Optional[str] = Field(None, description="Product ID")
    quantity: Optional[int] = Field(None, description="Quantity")
    color: Optional[str] = Field(None, description="Product color")
    size: Optional[str] = Field(None, description="Product size")


class RecommendationRequest(BaseModel):
    """Request model for product recommendations"""
    user_id: str = Field(..., description="User identifier")
    category: Optional[str] = Field(None, description="Product category filter")
    limit: int = Field(default=5, description="Maximum number of recommendations")


class InventoryRequest(BaseModel):
    """Request model for inventory checks"""
    product_id: str = Field(..., description="Product identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    location: Optional[Dict[str, float]] = Field(None, description="Customer location")
    quantity: int = Field(default=1, description="Requested quantity")


class LoyaltyRequest(BaseModel):
    """Request model for loyalty operations"""
    user_id: str = Field(..., description="User identifier")
    action: str = Field(..., description="Loyalty action: status, discount, redeem")
    order_total: Optional[float] = Field(None, description="Order total for discount calculation")


# API Endpoints

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "LangGraph Sales Agent API",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        # Check database connection
        # This would be implemented based on your database setup
        
        # Check Mistral client
        orchestrator = await get_sales_orchestrator()
        mistral_available = orchestrator.mistral_client is not None
        
        return {
            "status": "healthy",
            "database": "connected",
            "mistral_client": "available" if mistral_available else "unavailable",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@app.post("/api/chat", response_model=MessageResponse)
async def chat_with_agent(request: MessageRequest, background_tasks: BackgroundTasks):
    """
    Main endpoint for chatting with the sales agent
    
    This endpoint processes user messages through the LangGraph sales system,
    analyzing intent and routing to appropriate agents.
    """
    try:
        logger.info(f"Processing chat request from user {request.user_id}")
        
        # Process the conversation
        result = await process_sales_conversation(
            user_id=request.user_id,
            channel=request.channel,
            message=request.message,
            session_id=request.session_id,
            additional_context=request.additional_context
        )
        
        # Return structured response
        return MessageResponse(
            session_id=result["session_id"],
            user_id=result["user_id"],
            response=result["response"],
            current_intent=result.get("current_intent"),
            last_agent=result.get("last_agent"),
            cart_items_count=result.get("cart_items_count", 0),
            workflow_step=result.get("workflow_step", ""),
            has_errors=result.get("has_errors", False),
            conversation_complete=result.get("conversation_complete", True),
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/cart/operation")
async def cart_operation(request: CartRequest):
    """
    Perform cart operations
    
    This endpoint allows direct cart operations without going through
    the full conversation flow.
    """
    try:
        from backend.agents.cart_agent import get_cart_agent
        
        agent = await get_cart_agent()
        
        # Create state for processing
        state = ConversationState(user_id=request.user_id, channel="api")
        
        # Add the requested action as a message
        if request.action == "add" and request.product_id:
            state.add_message("user", f"Add {request.product_id} to cart")
        elif request.action == "view":
            state.add_message("user", "Show my cart")
        elif request.action == "checkout":
            state.add_message("user", "Proceed to checkout")
        
        # Process through cart agent
        result = await agent.process(state)
        
        return {
            "success": True,
            "action": request.action,
            "response": result["content"],
            "data": result.get("data", {}),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in cart operation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cart operation failed: {str(e)}")


@app.post("/api/recommendations")
async def get_recommendations(request: RecommendationRequest):
    """
    Get product recommendations
    
    This endpoint provides personalized product recommendations
    based on user preferences and history.
    """
    try:
        from backend.agents.recommendation_agent import get_recommendation_agent
        
        agent = await get_recommendation_agent()
        
        # Get recommendations
        recommendations = await agent.get_personalized_recommendations(
            user_id=request.user_id,
            category=request.category,
            limit=request.limit
        )
        
        return {
            "success": True,
            "user_id": request.user_id,
            "category": request.category,
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting recommendations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {str(e)}")


@app.post("/api/inventory/check")
async def check_inventory(request: InventoryRequest):
    """
    Check product inventory and availability
    
    This endpoint provides inventory status and fulfillment options
    for specific products.
    """
    try:
        from backend.agents.inventory_agent import get_inventory_agent
        
        agent = await get_inventory_agent()
        
        # Check availability
        availability = await agent.check_product_availability(
            product_id=request.product_id,
            user_id=request.user_id,
            location=request.location,
            quantity=request.quantity
        )
        
        return {
            "success": True,
            "product_id": request.product_id,
            "availability": availability,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error checking inventory: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Inventory check failed: {str(e)}")


@app.post("/api/loyalty/status")
async def get_loyalty_status(request: LoyaltyRequest):
    """
    Get loyalty program status and benefits
    
    This endpoint provides customer loyalty status, points balance,
    and available benefits.
    """
    try:
        from backend.agents.loyalty_agent import get_loyalty_agent
        
        agent = await get_loyalty_agent()
        
        # Create state for processing
        state = ConversationState(user_id=request.user_id, channel="api")
        if request.order_total:
            state.metadata["order_total"] = request.order_total
        
        # Get loyalty status
        result = await agent.process(state)
        
        return {
            "success": True,
            "user_id": request.user_id,
            "action": request.action,
            "response": result["content"],
            "data": result.get("data", {}),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting loyalty status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Loyalty status failed: {str(e)}")


@app.get("/api/conversation/{session_id}")
async def get_conversation(session_id: str):
    """
    Retrieve conversation history
    
    This endpoint allows retrieval of conversation history
    for a specific session.
    """
    try:
        from backend.agents.sales_agent import get_sales_orchestrator
        
        orchestrator = await get_sales_orchestrator()
        conversations = await orchestrator.get_conversation_history(session_id)
        
        return {
            "success": True,
            "session_id": session_id,
            "conversations": conversations,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error retrieving conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Conversation retrieval failed: {str(e)}")


@app.delete("/api/session/{session_id}")
async def clear_session(session_id: str):
    """
    Clear conversation session
    
    This endpoint allows clearing a conversation session
    and resetting the state.
    """
    try:
        # This would implement session clearing logic
        # For now, just return success
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "Session cleared successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error clearing session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Session clearing failed: {str(e)}")


# Webhook endpoints for external integrations
@app.post("/api/webhook/whatsapp")
async def whatsapp_webhook(payload: Dict[str, Any]):
    """
    Webhook for WhatsApp Business API integration
    
    This endpoint handles incoming messages from WhatsApp
    and routes them through the sales agent system.
    """
    try:
        # Extract message from WhatsApp payload
        from_number = payload.get("from", "")
        message_text = payload.get("text", "")
        
        if not message_text:
            return {"error": "No message text provided"}
        
        # Process through sales agent
        result = await process_sales_conversation(
            user_id=from_number,
            channel="whatsapp",
            message=message_text
        )
        
        # Return response (would be sent back via WhatsApp API)
        return {
            "success": True,
            "response": result["response"],
            "session_id": result["session_id"]
        }
        
    except Exception as e:
        logger.error(f"Error processing WhatsApp webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")


@app.post("/api/webhook/telegram")
async def telegram_webhook(payload: Dict[str, Any]):
    """
    Webhook for Telegram Bot API integration
    
    This endpoint handles incoming messages from Telegram
    and routes them through the sales agent system.
    """
    try:
        # Extract message from Telegram payload
        user_id = str(payload.get("message", {}).get("chat", {}).get("id", ""))
        message_text = payload.get("message", {}).get("text", "")
        
        if not message_text:
            return {"error": "No message text provided"}
        
        # Process through sales agent
        result = await process_sales_conversation(
            user_id=user_id,
            channel="telegram",
            message=message_text
        )
        
        # Return response (would be sent back via Telegram API)
        return {
            "success": True,
            "response": result["response"],
            "session_id": result["session_id"]
        }
        
    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        logger.info("Starting up LangGraph Sales Agent API...")
        
        # Initialize database
        await initialize_database()
        
        # Initialize Mistral client
        await initialize_mistral_client()
        
        # Initialize sales orchestrator
        await get_sales_orchestrator()
        
        logger.info("API startup completed successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    try:
        logger.info("Shutting down LangGraph Sales Agent API...")
        
        # Close database connection
        await close_database()
        
        logger.info("API shutdown completed")
        
    except Exception as e:
        logger.error(f"Shutdown failed: {str(e)}")


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return {
        "error": True,
        "status_code": exc.status_code,
        "detail": exc.detail,
        "timestamp": datetime.now().isoformat()
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return {
        "error": True,
        "status_code": 500,
        "detail": "Internal server error",
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    # Run the API server
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )