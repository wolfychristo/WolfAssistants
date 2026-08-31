from sqlalchemy import Integer, String, Boolean, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional
from app.core.database import Base
from app.core.encryption import smtp_encryption


class User(Base):
    __tablename__ = "app_users"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Admin tracking fields
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deletion_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Detailed deletion feedback fields
    deletion_feedback_category: Mapped[str | None] = mapped_column(String, nullable=True)  # pricing, features, support, etc.
    deletion_feedback_custom_category: Mapped[str | None] = mapped_column(String, nullable=True)  # custom reason when category is 'other'
    deletion_feedback_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5 scale
    deletion_feedback_details: Mapped[str | None] = mapped_column(String, nullable=True)  # detailed text feedback
    deletion_feedback_improvements: Mapped[str | None] = mapped_column(String, nullable=True)  # what could be improved
    deletion_feedback_competitor: Mapped[str | None] = mapped_column(String, nullable=True)  # if switching to competitor
    deletion_feedback_contact_consent: Mapped[bool] = mapped_column(Boolean, default=False)  # if they want follow-up
    deletion_feedback_contact_method: Mapped[str | None] = mapped_column(String, nullable=True)  # email, phone, etc.
    # Extended profile fields
    username: Mapped[str | None] = mapped_column(String, unique=True, index=True, nullable=True)
    company_name: Mapped[str | None] = mapped_column(String, nullable=True)
    team_size: Mapped[str | None] = mapped_column(String, nullable=True)
    revenue_size: Mapped[str | None] = mapped_column(String, nullable=True)
    social_link: Mapped[str | None] = mapped_column(String, nullable=True)
    website_url: Mapped[str | None] = mapped_column(String, nullable=True)
    calendly_link: Mapped[str | None] = mapped_column(String, nullable=True)
    heard_about_us: Mapped[str | None] = mapped_column(String, nullable=True)
    profile_image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    position_title: Mapped[str | None] = mapped_column(String, nullable=True)

    # Per-user business email settings (SMTP/IMAP)
    smtp_host: Mapped[str | None] = mapped_column(String, nullable=True)
    smtp_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    smtp_username: Mapped[str | None] = mapped_column(String, nullable=True)
    smtp_password: Mapped[str | None] = mapped_column(String, nullable=True)
    smtp_from: Mapped[str | None] = mapped_column(String, nullable=True)
    smtp_use_tls: Mapped[bool] = mapped_column(Boolean, default=True)

    imap_host: Mapped[str | None] = mapped_column(String, nullable=True)
    imap_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    imap_username: Mapped[str | None] = mapped_column(String, nullable=True)
    imap_password: Mapped[str | None] = mapped_column(String, nullable=True)
    imap_use_ssl: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # DKIM configuration (for manual key entry)
    dkim_selector: Mapped[str | None] = mapped_column(String, nullable=True)  # e.g., "default", "mail", "google"
    dkim_public_key: Mapped[str | None] = mapped_column(String, nullable=True)  # The DKIM public key
    
    # Auto follow-up settings
    auto_followup_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    auto_followup_max_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    auto_followup_daily_hour: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Auto follow-up telemetry
    last_auto_followup_run: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_auto_followup_sent_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Credential health tracking
    smtp_last_tested: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    smtp_test_status: Mapped[str | None] = mapped_column(String, nullable=True)
    
    # Tenant schema tracking
    schema_created: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # User timezone preference
    timezone: Mapped[str | None] = mapped_column(String, default='Asia/Kolkata', nullable=True)
    tier_activated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # When current tier was activated
    tier_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # When current tier expires (for paid tiers)
    payment_status: Mapped[str | None] = mapped_column(String, nullable=True)  # 'active', 'cancelled', 'past_due', 'trialing'
    last_payment_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # Last successful payment
    next_payment_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # Next expected payment
    
    # Trial period tracking
    trial_start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # When trial started
    trial_end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # When trial ends (14 days from start)
    
    # Pricing tier
    pricing_tier: Mapped[str | None] = mapped_column(String, default='free', nullable=True)  # 'free', 'starter', 'professional', 'enterprise'
    subscription_id: Mapped[str | None] = mapped_column(String, nullable=True)  # Stripe subscription ID
    
    # Marketplace freelancer fields (deprecated - kept for database compatibility)
    # These fields are no longer used but remain in the model to match existing database schema
    is_freelancer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    freelancer_profile_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    stripe_connect_account_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    marketplace_commission_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    def set_smtp_password(self, password: str):
        """Set encrypted SMTP password"""
        encrypted = smtp_encryption.encrypt_password(password)
        self.smtp_password = encrypted
    
    def get_smtp_password(self) -> str:
        """Get decrypted SMTP password"""
        return smtp_encryption.decrypt_password(self.smtp_password or "")
    
    def set_imap_password(self, password: str):
        """Set encrypted IMAP password"""
        self.imap_password = smtp_encryption.encrypt_password(password)
    
    def get_imap_password(self) -> str:
        """Get decrypted IMAP password"""
        return smtp_encryption.decrypt_password(self.imap_password or "")
    
    def is_tier_active(self) -> bool:
        """Check if current tier is active and not expired"""
        pricing_tier = getattr(self, 'pricing_tier', 'starter') or 'starter'
        # Map legacy tier names
        if pricing_tier == "free":
            pricing_tier = "starter"
        elif pricing_tier == "professional":
            pricing_tier = "pro"
        
        if pricing_tier == "starter":  # Free tier
            return True
        
        if not self.tier_expires_at:
            return False
            
        return datetime.utcnow() < self.tier_expires_at
    
    def is_payment_active(self) -> bool:
        """Check if payment is active (for paid tiers)"""
        pricing_tier = getattr(self, 'pricing_tier', 'starter') or 'starter'
        # Map legacy tier names
        if pricing_tier == "free":
            pricing_tier = "starter"
        elif pricing_tier == "professional":
            pricing_tier = "pro"
        
        if pricing_tier == "starter":  # Free tier
            return True
            
        return self.payment_status in ["active", "trialing"]
    
    def is_trial_active(self) -> bool:
        """Check if user is currently in their 14-day free trial period"""
        try:
            trial_start = getattr(self, 'trial_start_date', None)
            trial_end = getattr(self, 'trial_end_date', None)
            if not trial_start or not trial_end:
                return False
            now = datetime.utcnow()
            return trial_start <= now <= trial_end
        except Exception:
            return False
    
    def get_trial_days_remaining(self) -> int:
        """Get number of days remaining in trial (returns 0 if trial expired or not active)"""
        try:
            if not self.is_trial_active():
                return 0
            trial_end = getattr(self, 'trial_end_date', None)
            if not trial_end:
                return 0
            now = datetime.utcnow()
            remaining = (trial_end - now).days
            return max(0, remaining)
        except Exception:
            return 0
    
    def has_trial_expired(self) -> bool:
        """Check if trial has expired"""
        try:
            trial_end = getattr(self, 'trial_end_date', None)
            if not trial_end:
                return False
            return datetime.utcnow() > trial_end
        except Exception:
            return False
    
    def can_access_feature(self, feature: str) -> bool:
        """Check if user can access a specific feature based on their tier"""
        if not self.is_tier_active() or not self.is_payment_active():
            return False
            
        # Define feature access by tier
        tier_features = {
            "starter": ["basic_chat", "email_composition", "basic_analytics", "email_scheduling", "basic_templates"],
            "pro": ["basic_chat", "email_composition", "basic_analytics", "email_scheduling", "basic_templates", 
                   "advanced_analytics", "custom_templates", "team_collaboration"],
            "enterprise": ["basic_chat", "email_composition", "basic_analytics", "email_scheduling", "basic_templates",
                         "advanced_analytics", "custom_templates", "team_collaboration", "api_access", "priority_support"]
        }
        
        pricing_tier = getattr(self, 'pricing_tier', 'starter') or 'starter'
        # Map legacy tier names
        if pricing_tier == "free":
            pricing_tier = "starter"
        elif pricing_tier == "professional":
            pricing_tier = "pro"
        return feature in tier_features.get(pricing_tier, tier_features["starter"])
    
    def get_tier_limits(self) -> dict:
        """Get usage limits for current tier"""
        limits = {
            "starter": {
                "emails_per_month": 100,
                "ai_requests_per_day": 20,
                "team_members": 1,
                "storage_gb": 1
            },
            "pro": {
                "emails_per_month": 10000,
                "ai_requests_per_day": 500,
                "team_members": 10,
                "storage_gb": 100
            },
            "enterprise": {
                "emails_per_month": 100000,
                "ai_requests_per_day": 2000,
                "team_members": -1,  # Unlimited
                "storage_gb": 1000
            }
        }
        
        pricing_tier = getattr(self, 'pricing_tier', 'starter') or 'starter'
        # Map legacy tier names
        if pricing_tier == "free":
            pricing_tier = "starter"
        elif pricing_tier == "professional":
            pricing_tier = "pro"
        return limits.get(pricing_tier, limits["starter"])
    
    def get_marketplace_commission_rate(self) -> float:
        """Get commission rate based on current tier"""
        rates = {
            'starter': 0.10,
            'pro': 0.05,
            'enterprise': 0.01
        }
        tier = getattr(self, 'pricing_tier', 'starter') or 'starter'
        # Map old tier names to new ones
        if tier == 'free':
            tier = 'starter'
        elif tier == 'professional':
            tier = 'pro'
        return rates.get(tier, 0.10)

    # Referral system relationships
    sent_invitations = relationship("ReferralInvitation", back_populates="referrer")
    referral_rewards = relationship("ReferralReward", foreign_keys="ReferralReward.referrer_id", back_populates="referrer")
    received_rewards = relationship("ReferralReward", foreign_keys="ReferralReward.referee_id", back_populates="referee")
    credits = relationship("UserCredit", back_populates="user")
    referral_code = relationship("ReferralCode", back_populates="user", uselist=False)
    
    # User monitoring and abuse detection relationships
    activities = relationship("UserActivity", back_populates="user", lazy="select")
    bans = relationship("UserBan", foreign_keys="UserBan.user_id", back_populates="user", lazy="select")
    abuse_patterns = relationship("AbusePattern", back_populates="user", lazy="select")
    
    def is_banned(self) -> bool:
        """Check if user is currently banned"""
        from datetime import datetime
        from app.models.user_activity import BanStatus, UserBan
        from app.core.database import AccountsSessionLocal
        
        # Query bans directly using accounts database since UserBan is in accounts DB
        db = AccountsSessionLocal()
        try:
            active_bans = db.query(UserBan).filter(
                UserBan.user_id == self.id,
                UserBan.status.in_([BanStatus.ACTIVE, BanStatus.PERMANENT])
            ).all()
            
            if not active_bans:
                return False
                
            # Check for active bans
            for ban in active_bans:
                if ban.status == BanStatus.ACTIVE:
                    # Check if ban has expired
                    if ban.expires_at and ban.expires_at < datetime.utcnow():
                        continue
                    return True
                elif ban.status == BanStatus.PERMANENT:
                    return True
                    
            return False
        except Exception:
            # If there's any error checking ban status, allow login (fail open)
            return False
        finally:
            db.close()
    
    def get_active_ban(self):
        """Get the currently active ban if any"""
        from datetime import datetime
        from app.models.user_activity import BanStatus, UserBan
        from app.core.database import AccountsSessionLocal
        
        # Query bans directly using accounts database since UserBan is in accounts DB
        db = AccountsSessionLocal()
        try:
            active_bans = db.query(UserBan).filter(
                UserBan.user_id == self.id,
                UserBan.status.in_([BanStatus.ACTIVE, BanStatus.PERMANENT])
            ).all()
            
            if not active_bans:
                return None
                
            for ban in active_bans:
                if ban.status == BanStatus.ACTIVE:
                    if ban.expires_at and ban.expires_at < datetime.utcnow():
                        continue
                    return ban
                elif ban.status == BanStatus.PERMANENT:
                    return ban
                    
            return None
        except Exception:
            # If there's any error getting ban, return None (fail open)
            return None
        finally:
            db.close()

    def get_total_credits(self) -> int:
        """Get total valid credits for user."""
        # This method should be called with a tenant database session
        # The caller should pass the correct database session
        from app.models.referral import UserCredit
        from datetime import datetime
        
        # Get the current session from SQLAlchemy's session registry
        from sqlalchemy.orm import object_session
        db = object_session(self)
        
        if not db:
            return 0
            
        try:
            total = db.query(UserCredit).filter(
                UserCredit.user_id == self.id,
                (UserCredit.expires_at.is_(None) | (UserCredit.expires_at > datetime.utcnow()))
            ).with_entities(UserCredit.amount).all()
            return sum(amount[0] for amount in total if amount[0] > 0)
        except Exception:
            return 0

    def add_credits(self, amount: int, credit_type: str, description: Optional[str] = None, expires_days: Optional[int] = None):
        """Add credits to user account."""
        from app.core.database import SessionLocal
        from app.models.referral import UserCredit
        from datetime import timedelta
        
        db = SessionLocal()
        try:
            expires_at = None
            if expires_days:
                expires_at = datetime.utcnow() + timedelta(days=expires_days)
            
            credit = UserCredit(
                user_id=self.id,
                credit_type=credit_type,
                amount=amount,
                description=description,
                expires_at=expires_at
            )
            db.add(credit)
            db.commit()
        finally:
            db.close()

    def use_credits(self, amount: int, description: Optional[str] = None) -> bool:
        """Use credits from user account. Returns True if successful."""
        from app.core.database import SessionLocal
        from app.models.referral import UserCredit
        
        if self.get_total_credits() < amount:
            return False
        
        db = SessionLocal()
        try:
            # Add negative credit entry for usage
            credit = UserCredit(
                user_id=self.id,
                credit_type="usage",
                amount=-amount,
                description=description
            )
            db.add(credit)
            db.commit()
            return True
        finally:
            db.close()


