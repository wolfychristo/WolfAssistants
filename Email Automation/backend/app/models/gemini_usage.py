from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float
from sqlalchemy.sql import func
from app.core.database import Base

class WolfAssistantsUsage(Base):
    """Track all WolfAssistants AI usage for rate limiting and monitoring."""
    __tablename__ = "wolfy_usage"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, nullable=False, index=True)
    endpoint = Column(String, nullable=False)  # 'email_generation', 'chat_response', 'intent_parsing'
    request_type = Column(String, nullable=False)  # 'generate_email', 'chat', 'intent_analysis'
    tokens_used = Column(Integer, default=0)
    response_time = Column(Float, default=0.0)  # in seconds
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Request metadata for caching and deduplication
    request_hash = Column(String, index=True)  # Hash of similar requests for caching
    cached_response = Column(Boolean, default=False)  # Whether response came from cache
    priority = Column(String, default='normal')  # 'high', 'normal', 'low' for prioritization

    # Rate limiting metadata
    user_quota_used = Column(Integer, default=0)  # User's daily quota usage
    global_quota_used = Column(Integer, default=0)  # Global daily quota usage

# Alias for backward compatibility
WolfyUsage = WolfAssistantsUsage