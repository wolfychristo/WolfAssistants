"""Email reputation and deliverability tracking models"""
from sqlalchemy import Integer, String, Boolean, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional
from app.core.database import Base


class EmailReputation(Base):
    """Track email reputation metrics per user/mailbox"""
    __tablename__ = "email_reputation"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_email: Mapped[str] = mapped_column(String, index=True, nullable=False)
    mailbox: Mapped[str] = mapped_column(String, nullable=False)  # SMTP from address
    
    # SPF/DKIM status
    spf_configured: Mapped[bool] = mapped_column(Boolean, default=False)
    dkim_configured: Mapped[bool] = mapped_column(Boolean, default=False)
    spf_last_checked: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    dkim_last_checked: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Sending metrics (last 30 days)
    total_sent: Mapped[int] = mapped_column(Integer, default=0)
    total_delivered: Mapped[int] = mapped_column(Integer, default=0)
    total_bounced: Mapped[int] = mapped_column(Integer, default=0)
    total_complained: Mapped[int] = mapped_column(Integer, default=0)  # Spam complaints
    
    # Rate limiting
    cold_sends_today: Mapped[int] = mapped_column(Integer, default=0)
    cold_sends_reset_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    max_cold_sends_per_day: Mapped[int] = mapped_column(Integer, default=50)  # Conservative default
    
    # Reputation score (0-100)
    reputation_score: Mapped[float] = mapped_column(Float, default=100.0)
    last_calculated: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Status
    is_throttled: Mapped[bool] = mapped_column(Boolean, default=False)
    throttle_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    throttle_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship to bounce records
    bounces: Mapped[list["BounceRecord"]] = relationship("BounceRecord", back_populates="reputation", cascade="all, delete-orphan")


class BounceRecord(Base):
    """Track individual bounce events"""
    __tablename__ = "bounce_records"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reputation_id: Mapped[int] = mapped_column(Integer, ForeignKey("email_reputation.id"), nullable=False)
    owner_email: Mapped[str] = mapped_column(String, index=True, nullable=False)
    mailbox: Mapped[str] = mapped_column(String, nullable=False)
    
    # Bounce details
    recipient_email: Mapped[str] = mapped_column(String, nullable=False)
    bounce_type: Mapped[str] = mapped_column(String, nullable=False)  # 'hard', 'soft', 'complaint'
    bounce_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    bounce_code: Mapped[str | None] = mapped_column(String, nullable=True)  # SMTP error code
    
    # Related email
    email_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Link to emails table if available
    subject: Mapped[str | None] = mapped_column(String, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    reputation: Mapped["EmailReputation"] = relationship("EmailReputation", back_populates="bounces")

