"""
Referral system database models

Handles referral invitations, rewards, and credit tracking.
"""

from sqlalchemy import Integer, String, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timedelta, timezone
from enum import Enum as PyEnum
from typing import Optional

from app.core.database import Base

class ReferralStatus(PyEnum):
    """Referral invitation status enumeration."""
    PENDING = "pending"
    SENT = "sent"
    OPENED = "opened"
    SIGNED_UP = "signed_up"
    EXPIRED = "expired"
    FAILED = "failed"

class RewardType(PyEnum):
    """Referral reward type enumeration."""
    SIGNUP = "signup"
    ACTIVATION = "activation"
    TIER_UPGRADE = "tier_upgrade"
    MONTHLY_BONUS = "monthly_bonus"

class CreditType(PyEnum):
    """User credit type enumeration."""
    REFERRAL = "referral"
    PURCHASE = "purchase"
    BONUS = "bonus"
    USAGE = "usage"

class ReferralInvitation(Base):
    """Referral invitation model."""
    __tablename__ = "referral_invitations"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    referrer_id: Mapped[int] = mapped_column(Integer, ForeignKey("app_users.id"), nullable=False)
    invited_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    referral_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    personal_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ReferralStatus] = mapped_column(Enum(ReferralStatus), default=ReferralStatus.PENDING, nullable=False)
    credits_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    signed_up_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Relationships
    referrer = relationship("User", back_populates="sent_invitations")
    rewards = relationship("ReferralReward", back_populates="invitation")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set expiration to 30 days from creation
        if not self.expires_at:
            self.expires_at = datetime.now(timezone.utc) + timedelta(days=30)

    def is_expired(self) -> bool:
        """Check if invitation has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    def can_be_used(self) -> bool:
        """Check if invitation can still be used."""
        return self.status in [ReferralStatus.PENDING, ReferralStatus.SENT, ReferralStatus.OPENED] and not self.is_expired()

class ReferralReward(Base):
    """Referral reward tracking model."""
    __tablename__ = "referral_rewards"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    referrer_id: Mapped[int] = mapped_column(Integer, ForeignKey("app_users.id"), nullable=False)
    referee_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("app_users.id"), nullable=True)
    invitation_id: Mapped[int] = mapped_column(Integer, ForeignKey("referral_invitations.id"), nullable=False)
    reward_type: Mapped[RewardType] = mapped_column(Enum(RewardType), nullable=False)
    credits_awarded: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    referrer = relationship("User", foreign_keys=[referrer_id], back_populates="referral_rewards")
    referee = relationship("User", foreign_keys=[referee_id], back_populates="received_rewards")
    invitation = relationship("ReferralInvitation", back_populates="rewards")

class UserCredit(Base):
    """User credit tracking model."""
    __tablename__ = "user_credits"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("app_users.id"), nullable=False)
    credit_type: Mapped[CreditType] = mapped_column(Enum(CreditType), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # Can be negative for usage
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reference_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Links to referral, purchase, etc.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="credits")

    def is_expired(self) -> bool:
        """Check if credit has expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def is_valid(self) -> bool:
        """Check if credit is valid and not expired."""
        return not self.is_expired()

class ReferralCode(Base):
    """Referral code management model."""
    __tablename__ = "referral_codes"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("app_users.id"), nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    uses_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_uses: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="referral_code")

    def can_be_used(self) -> bool:
        """Check if referral code can still be used."""
        if not self.is_active:
            return False
        if self.max_uses and self.uses_count >= self.max_uses:
            return False
        return True

    def increment_usage(self):
        """Increment usage count and update last used timestamp."""
        self.uses_count += 1
        self.last_used_at = datetime.now(timezone.utc)
