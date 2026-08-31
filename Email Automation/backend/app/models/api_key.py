"""
API Key management models for external API access.
These models are stored in the accounts database.
"""
from __future__ import annotations

from sqlalchemy import Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.api_usage import APIUsage

from app.core.database import Base


class APIKey(Base):
    """API Key for external API access"""
    __tablename__ = "api_keys"
    __table_args__ = (
        Index('idx_api_keys_hash', 'key_hash'),
        Index('idx_api_keys_user', 'user_id'),
        Index('idx_api_keys_active', 'is_active'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)  # Hashed API key
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('app_users.id', ondelete='CASCADE'), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # Human-readable key name
    permissions: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)  # Array of permission scopes
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    rate_limit_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=10000)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ip_whitelist: Mapped[List[str] | None] = mapped_column(JSON, nullable=True)  # Array of allowed IPs
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", backref="api_keys")
    usage_records: Mapped[list["APIUsage"]] = relationship("APIUsage", back_populates="api_key", cascade="all, delete-orphan")
    
    def is_expired(self) -> bool:
        """Check if API key is expired"""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if API key is valid (active and not expired)"""
        return self.is_active and not self.is_expired()
    
    def has_permission(self, permission: str) -> bool:
        """Check if API key has a specific permission"""
        return permission in self.permissions

