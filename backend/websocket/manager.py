from fastapi import WebSocket
from typing import Dict, Set
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        # Store active connections: {session_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        # Store user connections: {user_id: Set[session_id]}
        self.user_sessions: Dict[str, Set[str]] = {}
        # Store heartbeat tasks
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str, user_id: str = None):
        """Accept and register a new connection"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        
        if user_id:
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = set()
            self.user_sessions[user_id].add(session_id)
        
        logger.info(f"WebSocket connected: session={session_id}, user={user_id}")
        
        # Start heartbeat
        self.heartbeat_tasks[session_id] = asyncio.create_task(
            self._heartbeat(websocket, session_id)
        )
    
    def disconnect(self, session_id: str, user_id: str = None):
        """Remove a connection"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        
        if user_id and user_id in self.user_sessions:
            self.user_sessions[user_id].discard(session_id)
            if not self.user_sessions[user_id]:
                del self.user_sessions[user_id]
        
        # Cancel heartbeat task
        if session_id in self.heartbeat_tasks:
            self.heartbeat_tasks[session_id].cancel()
            del self.heartbeat_tasks[session_id]
        
        logger.info(f"WebSocket disconnected: session={session_id}, user={user_id}")
    
    async def send_message(self, session_id: str, message: dict):
        """Send message to a specific session"""
        if session_id in self.active_connections:
            try:
                websocket = self.active_connections[session_id]
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {session_id}: {e}")
                self.disconnect(session_id)
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send message to all sessions of a user"""
        if user_id in self.user_sessions:
            for session_id in self.user_sessions[user_id]:
                await self.send_message(session_id, message)
    
    async def broadcast(self, message: dict, exclude: Set[str] = None):
        """Broadcast message to all connections"""
        exclude = exclude or set()
        disconnected = []
        
        for session_id, websocket in self.active_connections.items():
            if session_id not in exclude:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {session_id}: {e}")
                    disconnected.append(session_id)
        
        # Clean up disconnected sessions
        for session_id in disconnected:
            self.disconnect(session_id)
    
    async def _heartbeat(self, websocket: WebSocket, session_id: str):
        """Send periodic heartbeat to keep connection alive"""
        try:
            while session_id in self.active_connections:
                await asyncio.sleep(30)  # Send ping every 30 seconds
                try:
                    await websocket.send_json({
                        "type": "ping",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                except Exception as e:
                    logger.warning(f"Heartbeat failed for {session_id}: {e}")
                    break
        except asyncio.CancelledError:
            pass
    
    def get_active_sessions(self) -> int:
        """Get count of active sessions"""
        return len(self.active_connections)
    
    def get_user_sessions(self, user_id: str) -> Set[str]:
        """Get all session IDs for a user"""
        return self.user_sessions.get(user_id, set())


# Global connection manager instance
connection_manager = ConnectionManager()
