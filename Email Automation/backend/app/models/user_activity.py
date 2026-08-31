"""
User Activity and Abuse Detection Models
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
import uuid

from app.core.database import Base

class ActivityType(PyEnum):
    """Types of user activities to monitor"""
    LOGIN = "login"
    LOGOUT = "logout"
    EMAIL_SENT = "email_sent"
    EMAIL_RECEIVED = "email_received"
    CONTACT_CREATED = "contact_created"
    CONTACT_UPDATED = "contact_updated"
    CONTACT_DELETED = "contact_deleted"
    MEETING_SCHEDULED = "meeting_scheduled"
    PASSWORD_CHANGED = "password_changed"
    PROFILE_UPDATED = "profile_updated"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    API_ABUSE = "api_abuse"
    SPAM_ATTEMPT = "spam_attempt"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

class BanReason(PyEnum):
    """Reasons for user bans"""
    SPAM = "spam"
    ABUSE = "abuse"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    TERMS_VIOLATION = "terms_violation"
    FRAUD = "fraud"
    HARASSMENT = "harassment"
    INAPPROPRIATE_CONTENT = "inappropriate_content"
    SYSTEM_ABUSE = "system_abuse"
    MULTIPLE_ACCOUNTS = "multiple_accounts"
    MANUAL_BAN = "manual_ban"

class BanStatus(PyEnum):
    """Status of user bans"""
    ACTIVE = "active"
    EXPIRED = "expired"
    APPEALED = "appealed"
    OVERTURNED = "overturned"
    PERMANENT = "permanent"

class UserActivity(Base):
    """Track user activities for monitoring and abuse detection"""
    __tablename__ = "user_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("app_users.id"), nullable=False)
    activity_type = Column(Enum(ActivityType), nullable=False)
    description = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(Text, nullable=True)
    activity_metadata = Column(Text, nullable=True)  # JSON string for additional data
    risk_score = Column(Integer, default=0)  # 0-100 risk assessment
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="activities")

class UserBan(Base):
    """Track user bans and restrictions"""
    __tablename__ = "user_bans"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("app_users.id"), nullable=False)
    banned_by = Column(Integer, ForeignKey("app_users.id"), nullable=False)  # Admin who banned
    reason = Column(Enum(BanReason), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(BanStatus), default=BanStatus.ACTIVE)
    ban_duration_days = Column(Integer, nullable=True)  # None for permanent
    banned_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    appeal_submitted_at = Column(DateTime, nullable=True)
    appeal_reviewed_at = Column(DateTime, nullable=True)
    appeal_reviewed_by = Column(Integer, ForeignKey("app_users.id"), nullable=True)
    appeal_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="bans")
    banned_by_user = relationship("User", foreign_keys=[banned_by])
    appeal_reviewer = relationship("User", foreign_keys=[appeal_reviewed_by])

class AbusePattern(Base):
    """Track patterns of abuse for automated detection"""
    __tablename__ = "abuse_patterns"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("app_users.id"), nullable=False)
    pattern_type = Column(String(100), nullable=False)  # e.g., "rapid_email_sending", "spam_keywords"
    severity = Column(Integer, default=1)  # 1-5 severity level
    occurrences = Column(Integer, default=1)
    first_detected = Column(DateTime, default=datetime.utcnow)
    last_detected = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    auto_ban_triggered = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="abuse_patterns")

class AdminNotification(Base):
    """Track admin notifications for user management actions"""
    __tablename__ = "admin_notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    notification_type = Column(String(100), nullable=False)  # e.g., "user_banned", "abuse_detected"
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True)  # Related user
    admin_id = Column(Integer, ForeignKey("app_users.id"), nullable=True)  # Admin who should see this
    is_read = Column(Boolean, default=False)
    priority = Column(Integer, default=1)  # 1-5 priority level
    notification_metadata = Column(Text, nullable=True)  # JSON string for additional data
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    admin = relationship("User", foreign_keys=[admin_id])
