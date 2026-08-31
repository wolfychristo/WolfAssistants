from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import secrets
import string

from app.core.database import Base


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("app_users.id"), nullable=False, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    used = Column(Boolean, default=False, nullable=False)

    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(32)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("app_users.id"), nullable=False, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)

    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def expiry_in(hours: int = 2) -> datetime:
        return datetime.utcnow() + timedelta(hours=hours)


class ChangeEmailToken(Base):
    __tablename__ = "change_email_tokens"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("app_users.id"), nullable=False, index=True)
    new_email = Column(String, nullable=False)
    token = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    used = Column(Boolean, default=False, nullable=False)

    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(32)



class PasswordResetOTP(Base):
    __tablename__ = "password_reset_otps"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("app_users.id"), nullable=False, index=True)
    otp_code = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)

    @staticmethod
    def generate_otp(length: int = 6) -> str:
        # Use the structured OTP utility: 2 numbers, 2 uppercase, 2 lowercase
        from app.core.otp_utils import generate_structured_otp
        return generate_structured_otp()

    @staticmethod
    def expiry_in(minutes: int = 10) -> datetime:
        return datetime.utcnow() + timedelta(minutes=minutes)

