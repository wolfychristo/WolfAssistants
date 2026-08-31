"""Pydantic schemas for chat functionality."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ChatMessageBase(BaseModel):
    """Base chat message schema."""
    role: str = Field(..., description="Message role: 'user' or 'wolfy'")
    content: str = Field(..., description="Message content")
    intent: Optional[str] = Field(None, description="Detected intent")
    status: Optional[str] = Field(None, description="Message status")
    message_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ChatMessageCreate(ChatMessageBase):
    """Schema for creating a chat message."""
    pass


class ChatMessageResponse(ChatMessageBase):
    """Schema for chat message response."""
    id: int
    public_id: str
    session_id: int
    created_at: datetime

    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm(cls, obj):
        """Custom from_orm to handle JSON string metadata"""
        import json
        
        data = {
            'id': obj.id,
            'public_id': obj.public_id,
            'session_id': obj.session_id,
            'role': obj.role,
            'content': obj.content,
            'intent': obj.intent,
            'status': obj.status,
            'created_at': obj.created_at,
        }

        # Parse JSON string metadata if it exists
        if obj.message_metadata:
            try:
                data['message_metadata'] = json.loads(obj.message_metadata)
            except (json.JSONDecodeError, TypeError):
                data['message_metadata'] = None
        else:
            data['message_metadata'] = None

        return cls(**data)


class ChatSessionBase(BaseModel):
    """Base chat session schema."""
    title: Optional[str] = Field(None, description="Session title")
    contact_name: Optional[str] = Field(None, description="Contact name if applicable")
    contact_email: Optional[str] = Field(None, description="Contact email if applicable")


class ChatSessionCreate(ChatSessionBase):
    """Schema for creating a chat session."""
    pass


class ChatSessionUpdate(BaseModel):
    """Schema for updating a chat session."""
    title: Optional[str] = None
    is_active: Optional[bool] = None


class ChatSessionResponse(ChatSessionBase):
    """Schema for chat session response."""
    id: int
    public_id: str
    owner_email: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    message_count: Optional[int] = Field(None, description="Number of messages in session")

    class Config:
        from_attributes = True


class ChatSessionWithMessages(ChatSessionResponse):
    """Schema for chat session with messages."""
    messages: List[ChatMessageResponse] = []


class ChatRequest(BaseModel):
    """Schema for chat request."""
    message: str = Field(..., description="User message")
    session_id: Optional[int] = Field(None, description="Existing session ID, or None for new session")
    contact_name: Optional[str] = Field(None, description="Contact name if starting new session about a contact")
    contact_email: Optional[str] = Field(None, description="Contact email if starting new session about a contact")


class ChatResponse(BaseModel):
    """Schema for chat response."""
    session_id: int
    message: ChatMessageResponse
    session_title: Optional[str] = None
    is_new_session: bool = False


class ChatSessionListResponse(BaseModel):
    """Schema for listing chat sessions."""
    sessions: List[ChatSessionResponse]
    total: int
