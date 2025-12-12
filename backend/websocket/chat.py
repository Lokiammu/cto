from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from typing import Optional
import logging
import json
from datetime import datetime
from bson import ObjectId

from backend.websocket.manager import connection_manager
from backend.database import get_database
from backend.services.auth_service import decode_token
from backend.middleware.error_handlers import AuthError
from backend.models.message import MessageType

logger = logging.getLogger(__name__)

router = APIRouter()


class SalesAgentGraph:
    """Mock Sales Agent using LangGraph (placeholder for actual implementation)"""
    
    @staticmethod
    async def process_message(message: str, session_id: str, user_context: dict = None):
        """
        Process user message and generate response
        In production, this would integrate with LangGraph
        """
        # Mock agent response
        responses = [
            f"Thank you for your message! How can I assist you today?",
            f"I'd be happy to help you find the perfect product. What are you looking for?",
            f"Let me check our inventory for you. One moment please...",
            f"Great question! Based on your preferences, I recommend...",
        ]
        
        import random
        response = random.choice(responses)
        
        # Simulate thinking process
        yield {
            "type": "thinking",
            "content": "Processing your request...",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Simulate tool call
        yield {
            "type": "tool_call",
            "content": "Searching product database...",
            "tool": "product_search",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Final response
        yield {
            "type": "assistant",
            "content": response,
            "timestamp": datetime.utcnow().isoformat()
        }


async def authenticate_websocket(token: Optional[str]) -> dict:
    """Authenticate WebSocket connection"""
    if not token:
        raise AuthError("Authentication token required")
    
    try:
        token_data = decode_token(token)
        return {
            "user_id": token_data.user_id,
            "username": token_data.username
        }
    except Exception as e:
        raise AuthError(f"Invalid token: {str(e)}")


async def load_session_history(db, session_id: str):
    """Load conversation history for session"""
    session = await db.channel_sessions.find_one({"session_id": session_id})
    if session:
        return session.get("messages", [])
    return []


async def save_message(db, session_id: str, message_type: str, content: str, user_id: str = None):
    """Save message to database"""
    message = {
        "message_type": message_type,
        "content": content,
        "timestamp": datetime.utcnow()
    }
    
    await db.channel_sessions.update_one(
        {"session_id": session_id},
        {
            "$push": {"messages": message},
            "$set": {
                "updated_at": datetime.utcnow(),
                "user_id": user_id
            },
            "$setOnInsert": {
                "created_at": datetime.utcnow(),
                "is_active": True
            }
        },
        upsert=True
    )


@router.websocket("/ws/chat/{session_id}")
async def chat_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for chat
    URL: /ws/chat/{session_id}?token=<jwt_token>
    """
    db = get_database()
    user_data = None
    
    try:
        # Authenticate
        if token:
            try:
                user_data = await authenticate_websocket(token)
                user_id = user_data["user_id"]
            except AuthError as e:
                await websocket.close(code=1008, reason=str(e))
                return
        else:
            # Allow anonymous connections for demo
            user_id = None
        
        # Connect
        await connection_manager.connect(websocket, session_id, user_id)
        
        # Load session history
        history = await load_session_history(db, session_id)
        
        # Send welcome message with history
        await websocket.send_json({
            "type": "system",
            "content": "Connected to chat",
            "session_id": session_id,
            "history": history,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Main message loop
        while True:
            # Receive message
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                user_message = message_data.get("message", "")
                
                if not user_message:
                    continue
                
                # Save user message
                await save_message(db, session_id, "user", user_message, user_id)
                
                # Echo user message
                await websocket.send_json({
                    "type": "user",
                    "content": user_message,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Process with agent and stream responses
                async for response in SalesAgentGraph.process_message(
                    user_message,
                    session_id,
                    user_data
                ):
                    await websocket.send_json(response)
                    
                    # Save assistant response
                    if response["type"] == "assistant":
                        await save_message(
                            db,
                            session_id,
                            "assistant",
                            response["content"],
                            user_id
                        )
            
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "content": "Invalid message format",
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "content": "Error processing message",
                    "timestamp": datetime.utcnow().isoformat()
                })
    
    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        connection_manager.disconnect(session_id, user_id if user_data else None)
