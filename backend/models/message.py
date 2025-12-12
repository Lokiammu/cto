from pydantic import BaseModel
from typing import Optional, Any, Dict
from datetime import datetime
from enum import Enum


class MessageType(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"
    thinking = "thinking"
    tool_call = "tool_call"
    error = "error"


class ChatMessage(BaseModel):
    session_id: str
    message_type: MessageType
    content: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatSession(BaseModel):
    id: str = Field(alias="_id")
    session_id: str
    user_id: Optional[str] = None
    messages: List[ChatMessage] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    
    class Config:
        populate_by_name = True


from pydantic import Field
from typing import List
