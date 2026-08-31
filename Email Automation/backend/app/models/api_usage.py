"""
API Usage tracking models.
These models are stored in the accounts database.
"""
from __future__ import annotations

from sqlalchemy import Integer, String, DateTime, Integer as SQLInteger, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.api_key import APIKey

from app.core.database import Base


class APIUsage(Base):
    """Track API usage for analytics and monitoring"""
    __tablename__ = "api_usage"
    __table_args__ = (
        Index('idx_usage_api_key', 'api_key_id'),
        Index('idx_usage_created', 'created_at'),
        Index('idx_usage_endpoint', 'endpoint'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    api_key_id: Mapped[int] = mapped_column(Integer, ForeignKey('api_keys.id', ondelete='CASCADE'), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)  # Index defined in __table_args__
    method: Mapped[str] = mapped_column(String(10), nullable=False)  # GET, POST, etc.
    status_code: Mapped[int] = mapped_column(SQLInteger, nullable=False)
    response_time_ms: Mapped[int] = mapped_column(SQLInteger, nullable=False)  # Response time in milliseconds
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    request_size: Mapped[int | None] = mapped_column(SQLInteger, nullable=True)  # Request payload size in bytes
    response_size: Mapped[int | None] = mapped_column(SQLInteger, nullable=True)  # Response payload size in bytes
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)  # Index defined in __table_args__
    
    # Relationships
    api_key: Mapped["APIKey"] = relationship("APIKey", back_populates="usage_records")

