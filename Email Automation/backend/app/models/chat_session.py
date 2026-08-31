"""Chat session model for persistent conversations."""
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class ChatSession(Base):
    """Represents a chat session with Wolfy."""
    __tablename__ = "chat_sessions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    owner_email = Column(String, nullable=False, index=True)  # User who owns this session
    title = Column(String, nullable=True)  # Auto-generated or user-defined title
    contact_name = Column(String, nullable=True)  # If chatting about a specific contact
    contact_email = Column(String, nullable=True)  # Contact's email if applicable
    is_active = Column(Boolean, default=True)  # Whether this session is currently active
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_message_at = Column(DateTime(timezone=True), nullable=True)  # Last message timestamp

    # Relationship to messages
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ChatSession(id={self.id}, owner={self.owner_email}, title='{self.title}')>"


class ChatMessage(Base):
    """Represents a message in a chat session."""
    __tablename__ = "chat_messages"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role = Column(String, nullable=False)  # 'user' or 'wolfy'
    content = Column(Text, nullable=False)  # Message content
    intent = Column(String, nullable=True)  # Detected intent (send_email, schedule_meeting, etc.)
    status = Column(String, nullable=True)  # Message status (done, confirm, ok, etc.)
    message_metadata = Column(Text, nullable=True)  # JSON metadata (result data, context, etc.)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to session
    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, session_id={self.session_id}, role='{self.role}')>"
